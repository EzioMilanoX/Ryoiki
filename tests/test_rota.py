"""A rota: lutas em sequência, chefes escalados, recompensas nos feels e o fluxo de cenas."""

import random

import pytest

from ryoiki.chefe import carregar_chefe
from ryoiki.combate import FeelCombate
from ryoiki.defesa import FeelDefesa
from ryoiki.rota import Rota, carregar_rota, escalar
from ryoiki.tela_arena import ArenaScene
from ryoiki.tela_rota import ControleRota, RecompensaScene, ResultadoScene, quebrar
from ryoiki.tela_titulo import TituloScene
from tests.test_telas import Entrada, apertar

DADOS = carregar_rota()


def rec(rid):
    return next(r for r in DADOS.recompensas if r.id == rid)


def test_a_rota_do_json_carrega_e_todo_chefe_existe():
    assert len(DADOS.lutas) >= 2
    for cid, grau in DADOS.lutas:
        assert carregar_chefe(cid) and grau >= 1


def test_escalar_multiplica_vida_e_dano():
    base = carregar_chefe("vulcao")
    forte = escalar(base, 1.5)
    assert forte.vida == base.vida * 1.5
    assert forte.padroes[0].p["dano"] == base.padroes[0].p["dano"] * 1.5
    assert forte.dominio.dano_tique == base.dominio.dano_tique * 1.5


def test_bencao_e_voto_mexem_nos_feels():
    r = Rota(DADOS)
    r.escolher(rec("punho_pesado"))
    r.escolher(rec("voto_do_confinamento"))
    f = r.feels()
    base = FeelCombate.carregar()
    assert f["combate"].danos == pytest.approx(tuple(d * 1.25 for d in base.danos))
    assert f["defesa"].vida_max == FeelDefesa.carregar().vida_max - 20
    assert f["dominio"].custo < 70


def test_nenhuma_recompensa_repete():
    r = Rota(DADOS, random.Random(1))
    vistas = set()
    for _ in range(len(DADOS.recompensas)):
        oferta = r.oferecer(1)
        assert oferta[0].id not in vistas
        vistas.add(oferta[0].id)
        r.escolher(oferta[0])
    assert r.oferecer() == []


def test_a_vida_passa_de_uma_luta_para_a_outra_com_cura_parcial():
    r = Rota(DADOS)
    r.terminar_luta(True, 30)
    assert r.indice == 1 and r.vida == 30 + DADOS.cura_entre_lutas
    r.terminar_luta(False, 0)
    assert r.acabou and not r.venceu


def test_vencer_a_ultima_fecha_a_rota():
    r = Rota(DADOS)
    for _ in DADOS.lutas:
        r.terminar_luta(True, 100)
    assert r.acabou and r.venceu


def test_o_fluxo_de_cenas_da_rota():
    pilha = []
    e = Entrada()
    ctl = ControleRota(e, "boneco_de_palha", pilha.append, pilha.pop, random.Random(2))
    ctl.comecar()
    arena = pilha[-1]
    assert isinstance(arena, ArenaScene) and arena.ao_fim is not None
    assert "Recomeçar a luta" not in arena.opcoes  # na rota não dá para recomeçar
    arena.ao_fim(True, 50)
    assert isinstance(pilha[-1], RecompensaScene)
    apertar(pilha[-1], e, "direita", "confirmar")
    arena2 = pilha[-1]
    assert isinstance(arena2, ArenaScene) and arena2.vitalidade.vida == 50 + DADOS.cura_entre_lutas
    assert arena2.dados_chefe.id == DADOS.lutas[1][0] and len(ctl.rota.escolhidas) == 1
    arena2.ao_fim(False, 0)
    assert isinstance(pilha[-1], ResultadoScene) and len(pilha) == 1
    apertar(pilha[-1], e, "confirmar")
    assert pilha == []


def test_o_titulo_comeca_a_rota_com_a_tecnica_escolhida():
    e, rotas = Entrada(), []
    t = TituloScene(e, lambda a: None, ao_rota=rotas.append, ao_oficina=lambda: None)
    apertar(t, e, "direita")  # troca a técnica
    apertar(t, e, "baixo", "baixo", "direita", "confirmar")  # ações: lutar -> rota
    assert rotas == [t.tecnica.id]


def test_quebrar_texto_nao_corta_palavra():
    assert quebrar("um dois tres quatro", 8) == ["um dois", "tres", "quatro"]


def test_os_quatro_chefes_estao_na_rota():
    assert {cid for cid, _ in DADOS.lutas} == {"vulcao", "mahito", "dagon", "sukuna"}
