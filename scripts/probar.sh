#!/usr/bin/env bash
# Con el compose levantado: todos eligen a 41; se apaga el líder y todos pasan a 36.
#   PUERTO_BASE=81 scripts/probar.sh
set -uo pipefail
base="${PUERTO_BASE:-81}"

lideres() { # imprime el líder que ve cada nodo vivo
  for n in "$@"; do curl -s "localhost:${base}0$n/estado" | python3 -c 'import json,sys; print(json.load(sys.stdin)["lider"])' 2>/dev/null; done | sort -u | tr '\n' ' '
}

esperar() { # esperar "<líder>" nodos...
  local esperado=$1; shift
  for _ in $(seq 40); do
    [[ "$(lideres "$@")" == "$esperado " ]] && { echo "ok     los nodos $* ven al líder $esperado"; return 0; }
    sleep 1
  done
  echo "FALLA  los nodos $* ven: $(lideres "$@")"; return 1
}

esperar 41 1 2 3 4 5 || exit 1
docker compose stop nodo-3 >/dev/null 2>&1
echo "       se apagó nodo-3 (id 41)"
esperar 36 1 2 4 5 || exit 1
docker compose start nodo-3 >/dev/null 2>&1
curl -s -X POST "localhost:${base}03/eleccion" >/dev/null
echo "       volvió nodo-3 y pidió una elección"
esperar 41 1 2 3 4 5 || exit 1
