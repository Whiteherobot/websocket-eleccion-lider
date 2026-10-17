"""Elección de líder en un anillo con el algoritmo de Chang y Roberts (1979).

Cada nodo tiene un id único y solo conoce al siguiente del anillo. Gana el id
más alto:

- ELECCION(c): si c es mayor que el propio id se reenvía; si es menor y el
  nodo todavía no participa, lo reemplaza por su id; si es menor y ya
  participa, lo descarta (otra elección con un id más alto ya está en curso);
  si es el propio id, el mensaje dio la vuelta entero y el nodo es el líder.
- ELEGIDO(l): cada nodo anota al líder y lo reenvía hasta que vuelve a él.

Las funciones devuelven los mensajes que hay que mandar al siguiente nodo, así
el algoritmo se prueba sin red.
"""

from dataclasses import dataclass, field


def eleccion(candidato, saltos=0):
    return {"tipo": "ELECCION", "candidato": candidato, "saltos": saltos}


def elegido(lider, saltos=0):
    return {"tipo": "ELEGIDO", "lider": lider, "saltos": saltos}


@dataclass
class Nodo:
    id: int
    participante: bool = False
    lider: int | None = None
    mensajes_recibidos: int = field(default=0)

    def iniciar(self):
        """Empieza una elección (por ejemplo, al detectar que el líder cayó)."""
        if self.participante:
            return []
        self.participante = True
        self.lider = None
        return [eleccion(self.id)]

    def recibir(self, mensaje):
        self.mensajes_recibidos += 1
        saltos = mensaje.get("saltos", 0) + 1
        if mensaje["tipo"] == "ELECCION":
            candidato = mensaje["candidato"]
            if candidato > self.id:
                self.participante = True
                self.lider = None
                return [eleccion(candidato, saltos)]
            if candidato < self.id:
                if self.participante:
                    return []
                self.participante = True
                self.lider = None
                return [eleccion(self.id, saltos)]
            # Volvió el propio id: nadie más alto en el anillo.
            self.participante = False
            self.lider = self.id
            return [elegido(self.id, saltos)]
        if mensaje["tipo"] == "ELEGIDO":
            self.participante = False
            self.lider = mensaje["lider"]
            return [] if mensaje["lider"] == self.id else [elegido(mensaje["lider"], saltos)]
        raise ValueError(f"tipo de mensaje desconocido: {mensaje['tipo']!r}")
