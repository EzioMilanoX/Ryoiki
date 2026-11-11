"""O seu Domínio, o choque de domínios e o Domínio Simples."""

import pytest

from ryoiki.chefe import Chefe, carregar_chefe
from ryoiki.combate import FeelCombate, Golpeador
from ryoiki.dominio import Expansao, FeelDominio
from ryoiki.movimento import Corpo
from ryoiki.tecnica import carregar_tecnicas

TECNICAS = carregar_tecnicas()
FC = FeelCombate.carregar()
FDOM = FeelDominio.carregar()
CHEFE = carregar_chefe()
DT = 1 / 120
ARENA = (1600.0, 1000.0)


def montar(tecnica="boneco_de_palha"):
    g = Golpeador(FC)
    g.energia = FC.energia_max
    ch = Chefe.novo(CHEFE, 800, 500)
    ch.t_espera = 99
    return g, ch, Expansao(FDOM), TECNICAS[tecnica]


def rodar(xp, g, ch, segundos, **kw):
    acertos, t = [], 0.0
    while t < segundos:
        acertos += xp.atualizar(DT, g, ch, **kw)
        t += DT
    return acertos


def test_toda_tecnica_tem_dominio_com_efeitos_validos():
    assert all(t.dominio and t.dominio.efeitos for t in TECNICAS.values())


def test_so_expande_com_a_barra_cheia_e_gasta_o_custo():
    g, ch, xp, t = montar()
    g.energia = FC.energia_max - 1
    assert not xp.expandir(g, t)
    g.energia = FC.energia_max
    assert xp.expandir(g, t) and xp.ativo
    assert g.energia == FC.energia_max - FDOM.custo
    assert not xp.expandir(g, t)  # já aberto


def test_o_acerto_garantido_pega_o_chefe_em_qualquer_lugar_e_depois_queima():
    g, ch, xp, t = montar()
    ch.alvo.x, ch.alvo.y = 1500, 900
    xp.expandir(g, t)
    acertos = rodar(xp, g, ch, t.dominio.duracao + 0.05)
    assert len(acertos) == pytest.approx(t.dominio.duracao / t.dominio.tique, abs=1)
    assert ch.alvo.vida < ch.alvo.vida_max and ch.alvo.marcado
    assert not xp.ativo and xp.queimado and "fim" in xp.eventos
    g.energia = FC.energia_max
    assert not xp.expandir(g, t)  # técnica queimada


def test_vazio_infinito_paralisa_e_corta_a_entoacao_do_chefe():
    g, ch, xp, t = montar("ilimitado")
    ch.alvo.vida = ch.alvo.vida_max * CHEFE.dominio.gatilhos[0] - 1
    ch.atualizar(DT, Corpo(400, 500), ARENA)
    assert ch.estado == "entoando"
    xp.expandir(g, t)
    rodar(xp, g, ch, 0.3)
    ch.atualizar(DT, Corpo(400, 500), ARENA)
    assert ch.estado == "andando" and not ch.dominio_ativo


def _choque(tecnica="boneco_de_palha"):
    g, ch, xp, t = montar(tecnica)
    xp.expandir(g, t)
    ch.t_dominio, ch.t_tique = CHEFE.dominio.duracao, CHEFE.dominio.tique
    xp.atualizar(DT, g, ch)
    assert xp.em_choque and ch.em_choque
    return g, ch, xp, t


def test_dois_dominios_abertos_viram_choque_e_o_acerto_garantido_se_anula():
    g, ch, xp, t = _choque()
    t_dele, t_meu = ch.t_dominio, xp.t_dominio
    danos = []
    for _ in range(60):
        xp.atualizar(DT, g, ch)
        danos += ch.atualizar(DT, Corpo(400, 500), ARENA)
    assert not any(d.garantido for d in danos)
    assert ch.t_dominio == t_dele and xp.t_dominio == t_meu  # o tempo para no choque


def test_sem_reagir_o_dominio_mais_refinado_vence():
    g, ch, xp, t = _choque()
    assert t.dominio.refinamento < CHEFE.dominio.refinamento
    g.energia = 0
    rodar(xp, g, ch, 0.6 / (CHEFE.dominio.refinamento - t.dominio.refinamento))
    assert not xp.ativo and xp.queimado and "perdeu" in xp.eventos
    assert ch.dominio_ativo and not ch.em_choque  # o dele segue


def test_queimar_energia_ou_bater_vence_o_choque():
    g, ch, xp, t = _choque()
    g.energia = FC.energia_max
    rodar(xp, g, ch, 1.0, bombeando=True, dano_causado=1.0)
    for _ in range(600):
        if not xp.em_choque:
            break
        xp.atualizar(DT, g, ch, dano_causado=2.0)
    assert "venceu" in xp.eventos and xp.ativo
    assert not ch.dominio_ativo and ch.estado == "queimado"


def test_dominio_simples_gasta_energia_e_nao_abre_com_o_seu_dominio():
    g, ch, xp, t = montar()
    g.energia = 50
    rodar(xp, g, ch, 1.0, segurando_simples=True)
    assert xp.simples and g.energia == pytest.approx(50 - FDOM.simples_custo, rel=0.02)
    g.energia = FC.energia_max
    xp.expandir(g, t)
    xp.atualizar(DT, g, ch, segurando_simples=True)
    assert not xp.simples
