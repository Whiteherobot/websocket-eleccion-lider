import itertools
import random

import pytest

from anillo.eleccion import Nodo, eleccion


def simular(ids, iniciadores, orden_aleatorio=None):
    """Corre el algoritmo en un anillo en memoria. Devuelve los nodos y el total de mensajes."""
    nodos = [Nodo(i) for i in ids]
    pendientes = []  # (posición destino, mensaje)
    for pos in iniciadores:
        pendientes += [((pos + 1) % len(nodos), m) for m in nodos[pos].iniciar()]
    enviados = len(pendientes)
    while pendientes:
        i = orden_aleatorio.randrange(len(pendientes)) if orden_aleatorio else 0
        destino, mensaje = pendientes.pop(i)
        salida = nodos[destino].recibir(mensaje)
        pendientes += [((destino + 1) % len(nodos), m) for m in salida]
        enviados += len(salida)
    return nodos, enviados


@pytest.mark.parametrize("ids", [[23, 7, 41, 15, 36], [1, 2, 3, 4, 5], [5, 4, 3, 2, 1], [9]])
def test_gana_el_id_mas_alto_y_todos_lo_saben(ids):
    nodos, _ = simular(ids, iniciadores=[0])
    assert {n.lider for n in nodos} == {max(ids)}
    assert not any(n.participante for n in nodos)


def test_varias_elecciones_a_la_vez_terminan_con_un_solo_lider():
    ids = [23, 7, 41, 15, 36, 2, 30]
    for semilla in range(20):
        nodos, _ = simular(ids, iniciadores=[0, 2, 4, 6], orden_aleatorio=random.Random(semilla))
        assert {n.lider for n in nodos} == {41}


def test_cantidad_de_mensajes():
    # Mejor caso (ids crecientes en el sentido del anillo, inicia el mayor): 2n.
    n = 8
    _, mensajes = simular(list(range(1, n + 1)), iniciadores=[n - 1])
    assert mensajes == 2 * n
    # Peor caso (ids decrecientes, todos inician): n(n+1)/2 elecciones + n anuncios.
    _, mensajes = simular(list(range(n, 0, -1)), iniciadores=list(range(n)))
    assert mensajes == n * (n + 1) // 2 + n


def test_un_nodo_descarta_candidatos_menores_si_ya_participa():
    nodo = Nodo(10)
    assert nodo.iniciar() == [eleccion(10)]
    assert nodo.recibir(eleccion(3)) == []
    assert nodo.iniciar() == []  # no arranca otra elección encima de la suya


def test_el_mensaje_cuenta_los_saltos():
    nodos, _ = simular([3, 1, 2], iniciadores=[1])
    # La elección de 1 llega a 2, que la reemplaza; da la vuelta y vuelve al 3...
    assert all(n.lider == 3 for n in nodos)
    assert nodos[0].recibir({"tipo": "ELEGIDO", "lider": 3, "saltos": 2}) == []


def test_mensajes_desconocidos():
    with pytest.raises(ValueError):
        Nodo(1).recibir({"tipo": "HOLA"})


@pytest.mark.parametrize("perm", list(itertools.permutations([1, 2, 3, 4])))
def test_cualquier_orden_del_anillo(perm):
    nodos, _ = simular(list(perm), iniciadores=[0])
    assert {n.lider for n in nodos} == {4}
