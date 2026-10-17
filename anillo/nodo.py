"""Un nodo del anillo en red.

Variables de entorno:
  ID        id del nodo para la elección (entero, único)
  ANILLO    direcciones de todos los nodos en orden, separadas por comas
            (por ejemplo http://nodo-1:8000,http://nodo-2:8000,...)
  POSICION  índice de este nodo dentro de ANILLO (desde 0)

Los mensajes de la elección viajan por WebSocket (/ws) al siguiente nodo. Si el
siguiente no responde, se salta al que sigue, así el anillo se repara solo.
Cada nodo vigila al líder por HTTP y, si deja de responder, empieza una
elección nueva.
"""

import asyncio
import logging
import os
import time

import aiohttp
from aiohttp import web

from .eleccion import Nodo

ID = int(os.environ.get("ID", "1"))
ANILLO = [u.strip() for u in os.environ.get("ANILLO", "http://localhost:8000").split(",") if u.strip()]
POSICION = int(os.environ.get("POSICION", "0"))
VIGILANCIA = float(os.environ.get("VIGILANCIA", "2"))
PUERTO = int(os.environ.get("PUERTO", "8000"))
RECORDAR_CAIDA = 15  # segundos

logging.basicConfig(level=logging.INFO, format=f"[nodo {ID}] %(message)s")
log = logging.getLogger("nodo")


class Servicio:
    def __init__(self):
        self.nodo = Nodo(ID)
        self.yo = ANILLO[POSICION]
        self.url_lider = None
        self.siguiente = None
        self.sesion = None
        self.caidos = {}  # dirección -> momento en que dejó de responder

    async def enviar(self, mensaje):
        """Manda el mensaje al primer nodo vivo después de este, en orden de anillo."""
        n = len(ANILLO)
        orden = [ANILLO[(POSICION + k) % n] for k in range(1, n + 1)]
        # Los que fallaron hace poco se intentan al final, para no esperar su
        # timeout en cada mensaje mientras siguen caídos.
        recientes = {d for d, t in self.caidos.items() if time.monotonic() - t < RECORDAR_CAIDA}
        orden = [d for d in orden if d not in recientes] + [d for d in orden if d in recientes]
        for destino in orden:
            try:
                async with self.sesion.ws_connect(f"{destino}/ws", timeout=aiohttp.ClientWSTimeout(ws_close=2)) as ws:
                    await ws.send_json(mensaje)
                self.caidos.pop(destino, None)
                if destino != self.siguiente:
                    log.info("siguiente en el anillo: %s", destino)
                    self.siguiente = destino
                return
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
                if destino not in self.caidos:
                    log.info("%s no responde, se salta", destino)
                self.caidos[destino] = time.monotonic()
        log.warning("no hay ningún nodo vivo en el anillo")

    async def procesar(self, mensaje):
        if mensaje["tipo"] == "ELEGIDO" and "url" in mensaje:
            self.url_lider = mensaje["url"]
        salida = self.nodo.recibir(mensaje)
        if mensaje["tipo"] == "ELECCION" and salida and salida[0]["tipo"] == "ELEGIDO":
            log.info("soy el líder (la elección dio %d saltos)", mensaje["saltos"] + 1)
            self.url_lider = self.yo
        elif mensaje["tipo"] == "ELEGIDO" and salida and salida[0]["tipo"] == "ELECCION":
            log.info("no acepto al líder %d (mi id es mayor); empiezo una elección", mensaje["lider"])
        elif mensaje["tipo"] == "ELEGIDO" and not salida:
            log.info("todos saben que el líder es %d", self.nodo.lider)
        elif mensaje["tipo"] == "ELEGIDO":
            log.info("nuevo líder: %d", self.nodo.lider)
        for m in salida:
            if m["tipo"] == "ELEGIDO":
                m["url"] = self.url_lider
            await self.enviar(m)

    async def iniciar_eleccion(self, motivo):
        mensajes = self.nodo.iniciar()
        if mensajes:
            log.info("empiezo una elección (%s)", motivo)
            for m in mensajes:
                await self.enviar(m)

    async def vigilar(self):
        """Si el líder deja de responder, empieza otra elección."""
        # Al arrancar, cada nodo espera un poco distinto y solo pide elección si
        # todavía no le llegó un líder; así no se repiten elecciones al levantar todo junto.
        await asyncio.sleep(1 + POSICION * 0.7)
        if self.nodo.lider is None:
            await self.iniciar_eleccion("arranque")
        while True:
            await asyncio.sleep(VIGILANCIA)
            if self.url_lider in (None, self.yo) or self.nodo.participante:
                continue
            try:
                async with self.sesion.get(f"{self.url_lider}/estado", timeout=aiohttp.ClientTimeout(total=1.5)) as r:
                    r.raise_for_status()
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
                log.info("el líder %s no responde", self.url_lider)
                self.url_lider = None
                self.nodo.lider = None
                await self.iniciar_eleccion("cayó el líder")


servicio = Servicio()


async def ws_entrada(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            mensaje = msg.json()
            # Se procesa aparte para que el que envía no espere a toda la vuelta.
            asyncio.create_task(servicio.procesar(mensaje))
    return ws


async def estado(request):
    n = servicio.nodo
    return web.json_response(
        {"id": n.id, "lider": n.lider, "participante": n.participante, "siguiente": servicio.siguiente,
         "mensajes_recibidos": n.mensajes_recibidos}
    )


async def pedir_eleccion(request):
    asyncio.create_task(servicio.iniciar_eleccion("pedida por HTTP"))
    return web.json_response({"id": ID, "eleccion": "iniciada"}, status=202)


async def al_arrancar(app):
    servicio.sesion = aiohttp.ClientSession()
    app["vigilancia"] = asyncio.create_task(servicio.vigilar())


async def al_cerrar(app):
    app["vigilancia"].cancel()
    await servicio.sesion.close()


def crear_app():
    app = web.Application()
    app.add_routes([web.get("/ws", ws_entrada), web.get("/estado", estado), web.post("/eleccion", pedir_eleccion)])
    app.on_startup.append(al_arrancar)
    app.on_cleanup.append(al_cerrar)
    return app


if __name__ == "__main__":
    web.run_app(crear_app(), port=PUERTO, print=None)
