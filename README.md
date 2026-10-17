# websocket-eleccion-lider

[![CI](https://github.com/Whiteherobot/websocket-eleccion-lider/actions/workflows/ci.yml/badge.svg)](https://github.com/Whiteherobot/websocket-eleccion-lider/actions/workflows/ci.yml)

Cinco contenedores en anillo que eligen un líder con el algoritmo de Chang y
Roberts, hablando por WebSocket. Si el líder se cae, los demás lo detectan y
eligen otro; si un nodo no responde, el anillo lo salta.

```
   nodo-1 (23) ──> nodo-2 (7) ──> nodo-3 (41) ──> nodo-4 (15) ──> nodo-5 (36) ──┐
       ^                                                                        │
       └────────────────────────────────────────────────────────────────────────┘
```

## Cómo funciona

- **Elección** (`anillo/eleccion.py`): un nodo manda `ELECCION(su id)` al
  siguiente. Cada nodo reenvía el candidato si es mayor que su id, lo reemplaza
  por el suyo si es menor (y todavía no participa) o lo descarta si ya participa.
  Cuando a un nodo le vuelve su propio id, es el líder y manda `ELEGIDO` alrededor
  del anillo. Gana el id más alto; con n nodos se usan entre 2n y
  n(n+1)/2 + n mensajes.
- **Reparación del anillo** (`anillo/nodo.py`): si el siguiente nodo no acepta la
  conexión, el mensaje va al que sigue.
- **Caída del líder**: cada nodo consulta al líder por HTTP cada 2 s; si no
  responde, empieza una elección nueva.
- **Regreso de un nodo**: un nodo que vuelve y recibe un anuncio de un líder con
  id menor que el suyo no lo acepta y empieza su propia elección.

## Uso

```bash
docker compose up --build
curl localhost:8101/estado
# {"id": 23, "lider": 41, "participante": false, "siguiente": "http://nodo-2:8000", ...}

docker compose stop nodo-3          # se cae el líder (41)
curl localhost:8101/estado          # en unos segundos: "lider": 36

docker compose start nodo-3          # vuelve y recupera el liderazgo
curl -X POST localhost:8101/eleccion   # también se puede pedir una elección a mano
```

Cada nodo publica su puerto en el host (8101 a 8105) para poder mirar su
estado; con `PUERTO_BASE=83` quedan en 8301 a 8305. En los logs se ve la
elección:

```
nodo-3-1  | [nodo 41] soy el líder (la elección dio 7 saltos)
nodo-1-1  | [nodo 23] nuevo líder: 41
nodo-1-1  | [nodo 23] el líder http://nodo-3:8000 no responde
nodo-1-1  | [nodo 23] empiezo una elección (cayó el líder)
nodo-2-1  | [nodo 7] http://nodo-3:8000 no responde, se salta
nodo-5-1  | [nodo 36] soy el líder (la elección dio 5 saltos)
nodo-5-1  | [nodo 36] todos saben que el líder es 36
nodo-3-1  | [nodo 41] empiezo una elección (arranque)
nodo-3-1  | [nodo 41] soy el líder (la elección dio 5 saltos)
```

## Pruebas

```bash
pip install -r requirements.txt pytest
pytest                # el algoritmo en anillos simulados
scripts/probar.sh     # con el compose levantado: elige 41, cae 41 -> 36, vuelve 41 -> 41
```

Las pruebas del algoritmo cubren varios órdenes del anillo, varias elecciones a
la vez (con los mensajes entregados en orden aleatorio) y la cantidad de
mensajes en el mejor y el peor caso.

## De dónde sale

Era la evaluación de Docker y comunicación de Sistemas Distribuidos (noviembre
de 2025): un anillo de tres nodos que transformaban un mensaje (el informe
original está en `docs/`). Ese mismo enunciado ya está resuelto en
[websocket-anillo-nodos](https://github.com/Whiteherobot/websocket-anillo-nodos),
así que en 2026 este repo se rehízo con la misma idea, contenedores en anillo
por WebSocket, aplicada a otro problema clásico: elegir un líder y sobrevivir a
su caída. El repo se llamaba `Evaluaci-n-Docker-y-Comunicaci-n_Michael_Lata`.

Licencia MIT.
