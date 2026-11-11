"""A oficina: montar, custo pela soma dos blocos, salvar, carregar e lutar com a técnica."""

import pytest

from ryoiki import oficina as of
from ryoiki.tecnica import Conjurador, carregar_tecnicas
from ryoiki.tela_arena import ArenaScene
from ryoiki.tela_oficina import OficinaScene
from ryoiki.tela_titulo import TituloScene
from tests.test_telas import Entrada, apertar


def test_toda_forma_e_efeito_pronto_passa_na_validacao(tmp_path):
    for forma in of.FORMAS:
        for efeito in of.EFEITOS:
            m = of.Montagem(golpes=[of.GolpeMontado(forma, [efeito, "", ""])] * 2)
            of.salvar(m, tmp_path / "t.json")
            assert "propria" in carregar_tecnicas(propria=tmp_path / "t.json")


def test_o_custo_e_a_soma_dos_blocos_e_a_recarga_sobe_com_ele():
    leve = of.GolpeMontado("disparo", ["dano_leve", "", ""])
    pesado = of.GolpeMontado("lanca", ["dano_forte", "atordoar", "empurrar"])
    assert leve.custo == of.FORMAS["disparo"][1] + of.EFEITOS["dano_leve"][1]
    assert pesado.custo > leve.custo and pesado.recarga > leve.recarga


def test_golpe_sem_efeito_nao_salva(tmp_path):
    m = of.Montagem()
    m.golpes[1].efeitos = ["", "", ""]
    with pytest.raises(ValueError):
        of.salvar(m, tmp_path / "t.json")


def test_salvar_e_reabrir_devolve_a_mesma_montagem(tmp_path):
    m = of.Montagem(cor=3)
    m.golpes[0].efeitos[2] = "atordoar"
    of.salvar(m, tmp_path / "t.json")
    assert of.carregar(tmp_path / "t.json") == m


def test_arquivo_estragado_nao_derruba_nada(tmp_path):
    (tmp_path / "t.json").write_text("{nada", encoding="utf-8")
    assert of.carregar(tmp_path / "t.json") is None
    assert "propria" not in carregar_tecnicas(propria=tmp_path / "t.json")


def test_o_dominio_proprio_garante_o_golpe_1_sem_puxar_e_com_meio_dano():
    m = of.Montagem(golpes=[of.GolpeMontado("explosao", ["dano_forte", "puxar", ""])] * 2)
    efeitos = m.para_json()["dominio"]["efeitos"]
    assert efeitos == [{"tipo": "dano", "valor": 9.0}]


def test_a_tecnica_propria_funciona_na_luta(tmp_path):
    from ryoiki.combate import Alvo, FeelCombate, Golpeador
    from ryoiki.movimento import Corpo

    of.salvar(of.Montagem(), tmp_path / "t.json")
    t = carregar_tecnicas(propria=tmp_path / "t.json")["propria"]
    corpo, alvo, g = Corpo(500, 500), Alvo(700, 500), Golpeador(FeelCombate.carregar())
    g.energia = 100
    cj = Conjurador(t)
    assert cj.usar(0, corpo, (700, 500), g)
    for _ in range(60):
        cj.atualizar(1 / 120, corpo, [alvo], (2000, 2000))
    assert alvo.marcado and alvo.vida < alvo.vida_max


def test_a_tela_troca_pecas_salva_e_o_titulo_escolhe_a_propria(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    e, voltou = Entrada(), []
    ofi = OficinaScene(e, lambda: voltou.append(1))
    apertar(ofi, e, "baixo", "baixo", "direita")  # forma do golpe 1: a próxima
    assert ofi.montagem.golpes[0].forma == list(of.FORMAS)[1]
    apertar(ofi, e, "cima", "cima", "cima", "confirmar")  # dá a volta até a última linha (salvar)
    assert voltou == [1] and of.caminho_proprio().exists()
    titulo = TituloScene(e, lambda arena: None, ao_oficina=lambda: None)
    titulo.da_oficina = True
    titulo.on_enter(None, None)
    assert titulo.tecnica.id == of.ID_PROPRIA
    assert isinstance(titulo.criar_arena(), ArenaScene)


def test_o_nome_escolhido_vai_para_a_tecnica_e_o_dominio(tmp_path):
    m = of.Montagem(nome=1)
    of.salvar(m, tmp_path / "t.json")
    t = carregar_tecnicas(propria=tmp_path / "t.json")["propria"]
    fim, kanji = of.NOMES[1]
    assert t.nome == f"Técnica {fim}" and t.kanji.startswith(kanji)
    assert t.dominio.nome == f"Domínio {fim}"
    assert of.carregar(tmp_path / "t.json").nome == 1
