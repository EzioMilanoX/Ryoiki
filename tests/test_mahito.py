"""O segundo chefe: lacaios invocados, regeneração e o desenho escolhido pelos dados."""

import json

import pytest

from ryoiki import visual
from ryoiki.chefe import Chefe, carregar_chefe
from ryoiki.combate import GOLPE, FeelCombate, Golpeador
from ryoiki.movimento import DADOS, Corpo

MAHITO = carregar_chefe("mahito")
DT = 1 / 120
ARENA = (1600.0, 1000.0)


def invocar(ch, corpo):
    ch.padrao = next(p for p in MAHITO.padroes if p.tipo == "invocar")
    ch.estado, ch.t = "carga", ch.padrao.carga
    for _ in range(int(ch.padrao.carga / DT) + 2):
        ch.atualizar(DT, corpo, ARENA)


def test_todo_chefe_do_json_carrega_e_tem_desenho():
    ids = json.loads((DADOS / "maldicoes.json").read_text(encoding="utf-8"))["maldicoes"]
    for cid in ids:
        assert carregar_chefe(cid).visual in visual.DESENHOS_CHEFE


def test_invocar_respeita_o_maximo_de_lacaios():
    ch, corpo = Chefe.novo(MAHITO, 800, 500), Corpo(200, 200)
    q = next(p for p in MAHITO.padroes if p.tipo == "invocar").p
    for _ in range(4):
        invocar(ch, corpo)
    assert len(ch.lacaios) == q["maximo"]


def test_o_lacaio_corre_e_explode_no_contato():
    ch, corpo = Chefe.novo(MAHITO, 800, 500), Corpo(700, 500)
    invocar(ch, corpo)
    danos = []
    for _ in range(240):
        danos += ch.atualizar(DT, corpo, ARENA)
    assert any(d.fonte == "lacaio" for d in danos)
    assert any(ev[0] == "lacaio_explode" for ev in ch.eventos)


def test_o_golpe_mata_o_lacaio_no_caminho():
    ch, corpo = Chefe.novo(MAHITO, 1400, 900), Corpo(500, 500)
    invocar(ch, corpo)
    la = ch.lacaios[0]
    la.x, la.y, la.vida = 545, 500, 5
    g = Golpeador(FeelCombate.carregar())
    g.pedir(GOLPE)
    for _ in range(40):
        g.atualizar(DT, corpo, [ch.alvo, *ch.lacaios])
    assert not la.vivo


def test_mahito_regenera_menos_com_a_tecnica_queimada():
    ch, corpo = Chefe.novo(MAHITO, 800, 500), Corpo(200, 200)
    ch.t_espera = 99
    ch.alvo.vida = 500
    for _ in range(120):
        ch.atualizar(DT, corpo, ARENA)
    assert ch.alvo.vida == pytest.approx(500 + MAHITO.regeneracao, abs=0.1)
    ch.estado, ch.t = "queimado", 5
    vida = ch.alvo.vida
    for _ in range(120):
        ch.atualizar(DT, corpo, ARENA)
    assert ch.alvo.vida == vida
