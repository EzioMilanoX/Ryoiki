"""A maldição chefe: os padrões avisados, o domínio, a interrupção e a técnica queimada."""

import json

import pytest

from ryoiki.chefe import Chefe, carregar_chefe
from ryoiki.movimento import Corpo

DADOS = carregar_chefe()
DT = 1 / 120
ARENA = (1600.0, 1000.0)


def novo(seed=7):
    ch = Chefe.novo(DADOS, 800, 500, seed)
    ch.t_espera = 99  # sem padrões, a não ser que o teste peça
    return ch


def rodar(ch, corpo, segundos):
    danos, t = [], 0.0
    while t < segundos:
        danos += ch.atualizar(DT, corpo, ARENA)
        ch.alvo.passo(DT, ARENA)
        t += DT
    return danos


def forcar(ch, pid):
    ch.padrao = next(p for p in DADOS.padroes if p.id == pid)
    ch.estado, ch.t = "carga", ch.padrao.carga


def test_o_chefe_do_json_tem_tres_padroes_e_um_dominio():
    assert {p.tipo for p in DADOS.padroes} == {"investida", "erupcoes", "brasas"}
    assert DADOS.dominio.gatilhos == tuple(sorted(DADOS.dominio.gatilhos, reverse=True))


def test_padrao_desconhecido_e_recusado(tmp_path):
    from ryoiki.movimento import DADOS as PASTA

    dados = json.loads((PASTA / "maldicoes.json").read_text(encoding="utf-8"))
    dados["maldicoes"]["vulcao"]["padroes"][0]["tipo"] = "teleporte"
    caminho = tmp_path / "m.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match="teleporte"):
        carregar_chefe(caminho=caminho)


def test_a_investida_avisa_mira_e_acerta_uma_vez():
    ch, corpo = novo(), Corpo(1100, 500)
    forcar(ch, "investida")
    antes = rodar(ch, corpo, ch.padrao.carga - 0.05)
    assert antes == [] and ch.estado == "carga"  # o aviso: nada dói ainda
    danos = rodar(ch, corpo, 1.0)
    assert [d.fonte for d in danos] == ["investida"] and not danos[0].garantido
    assert ch.alvo.x > 1000


def test_esquivar_da_investida_trava_a_mira_no_fim_da_carga():
    ch, corpo = novo(), Corpo(1100, 500)
    forcar(ch, "investida")
    rodar(ch, corpo, ch.padrao.carga - 0.2)  # a mira já travou
    corpo.y = 800  # saiu da faixa
    assert rodar(ch, corpo, 1.0) == []


def test_erupcoes_caem_em_cima_do_jogador_depois_do_atraso():
    ch, corpo = novo(), Corpo(600, 500)
    forcar(ch, "erupcoes")
    rodar(ch, corpo, ch.padrao.carga + 0.01)
    q = ch.padrao.p
    assert len(ch.erupcoes) == q["quantidade"]
    assert (ch.erupcoes[0].x, ch.erupcoes[0].y) == (600, 500)
    danos = rodar(ch, corpo, q["atraso"] + 0.6)
    assert any(d.fonte == "erupcao" for d in danos)


def test_brasas_saem_em_leque():
    ch, corpo = novo(), Corpo(400, 500)
    forcar(ch, "insetos")
    rodar(ch, corpo, ch.padrao.carga + 0.01)
    assert len(ch.brasas) == ch.padrao.p["quantidade"]
    assert any(d.fonte == "brasa" for d in rodar(ch, corpo, 1.5))


def test_o_padrao_nao_se_repete_duas_vezes_seguidas():
    ch, corpo = Chefe.novo(DADOS, 800, 500), Corpo(1400, 900)
    vistos = []
    for _ in range(12):
        ch.estado, ch.t_espera = "andando", 0.0
        ch.atualizar(DT, corpo, ARENA)
        vistos.append(ch.padrao.id)
        ch.brasas.clear()
        ch.erupcoes.clear()
    assert all(a != b for a, b in zip(vistos, vistos[1:], strict=False))


def _ate_entoar(ch, corpo):
    ch.alvo.vida = ch.alvo.vida_max * DADOS.dominio.gatilhos[0] - 1
    ch.atualizar(DT, corpo, ARENA)
    assert ch.estado == "entoando"


def test_o_dominio_entoa_no_gatilho_e_o_acerto_e_garantido():
    ch, corpo = novo(), Corpo(400, 500)
    _ate_entoar(ch, corpo)
    rodar(ch, corpo, DADOS.dominio.entoar + 0.02)
    assert ch.dominio_ativo
    danos = [d for d in rodar(ch, corpo, DADOS.dominio.duracao) if d.fonte == "dominio"]
    assert danos and all(d.garantido for d in danos)
    assert len(danos) == pytest.approx(DADOS.dominio.duracao / DADOS.dominio.tique, abs=1)
    assert ch.estado == "queimado" and not ch.dominio_ativo


def test_dano_na_entoacao_interrompe():
    ch, corpo = novo(), Corpo(400, 500)
    _ate_entoar(ch, corpo)
    ch.alvo.vida -= DADOS.dominio.interromper
    ch.atualizar(DT, corpo, ARENA)
    assert ch.estado == "andando" and not ch.dominio_ativo and ch.alvo.t_atordoado > 0
    assert ("interrompido", ch.alvo.x, ch.alvo.y) in ch.eventos


def test_atordoar_na_entoacao_interrompe():
    ch, corpo = novo(), Corpo(400, 500)
    _ate_entoar(ch, corpo)
    ch.alvo.t_atordoado = 0.5
    ch.atualizar(DT, corpo, ARENA)
    assert ch.estado == "andando"


def test_cada_gatilho_dispara_uma_vez_so():
    ch, corpo = novo(), Corpo(400, 500)
    _ate_entoar(ch, corpo)
    ch.alvo.t_atordoado = 0.5
    ch.atualizar(DT, corpo, ARENA)
    ch.alvo.t_atordoado = 0
    rodar(ch, corpo, 0.2)
    assert ch.estado != "entoando" and len(ch.gatilhos) == len(DADOS.dominio.gatilhos) - 1


def test_o_chefe_e_pesado():
    ch = novo()
    ch.alvo.receber(0, 1, 0, 500)
    assert ch.alvo.vx == pytest.approx(500 / DADOS.massa)
