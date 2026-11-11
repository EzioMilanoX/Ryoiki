"""A técnica por blocos, a Técnica Reversa, o reforço como defesa e a maldição que revida."""

import json

import pytest

from ryoiki.combate import Alvo, FeelCombate, Golpeador
from ryoiki.defesa import FeelDefesa, Vitalidade
from ryoiki.inimigo import FeelMaldicao, IAMaldicao
from ryoiki.movimento import Corpo
from ryoiki.tecnica import Conjurador, aplicar, carregar_tecnicas

TECNICAS = carregar_tecnicas()
FC = FeelCombate.carregar()
FD = FeelDefesa.carregar()
DT = 1 / 120
ARENA = (2000.0, 2000.0)


def rodar(cj, corpo, alvos, segundos):
    acertos, t = [], 0.0
    while t < segundos:
        acertos += cj.atualizar(DT, corpo, alvos, ARENA)
        for al in alvos:
            al.passo(DT, ARENA)
        t += DT
    return acertos


def cheio():
    g = Golpeador(FC)
    g.energia = FC.energia_max
    return g


def test_as_tecnicas_do_json_carregam_e_o_jogador_existe(tmp_path):
    assert {"boneco_de_palha", "ilimitado"} <= set(TECNICAS)
    from ryoiki.movimento import DADOS

    jogador = json.loads((DADOS / "tecnicas.json").read_text(encoding="utf-8"))["jogador"]
    assert jogador in TECNICAS
    assert all(len(t.golpes) == 2 for t in TECNICAS.values())


def test_bloco_desconhecido_e_recusado(tmp_path):
    ruim = {
        "tecnicas": {
            "x": {
                "nome": "X",
                "kanji": "X",
                "golpes": [
                    {
                        "id": "a",
                        "nome": "A",
                        "custo": 1,
                        "recarga": 1,
                        "blocos": [{"tipo": "projetil", "efeitos": [{"tipo": "explodir_tudo"}]}],
                    }
                ],
            }
        }
    }
    caminho = tmp_path / "t.json"
    caminho.write_text(json.dumps(ruim), encoding="utf-8")
    with pytest.raises(ValueError, match="explodir_tudo"):
        carregar_tecnicas(caminho)


def test_pregos_saem_em_leque_marcam_e_a_ressonancia_consome_a_marca():
    corpo, alvo, g = Corpo(500, 500), Alvo(700, 500, vida_max=999, vida=999), cheio()
    cj = Conjurador(TECNICAS["boneco_de_palha"])
    assert cj.usar(0, corpo, (700, 500), g)
    assert len(cj.projeteis) == 3
    rodar(cj, corpo, [alvo], 0.5)
    assert alvo.marcado and alvo.vida < 999
    vida = alvo.vida
    alvo.x, alvo.y = 1800, 1800  # longe: a Ressonância não liga para a distância
    assert cj.usar(1, corpo, (0, 0), g)
    rodar(cj, corpo, [alvo], 0.05)
    assert vida - alvo.vida == 32 and not alvo.marcado and alvo.t_atordoado > 0


def test_ressonancia_sem_marca_nao_faz_nada():
    corpo, alvo, g = Corpo(500, 500), Alvo(700, 500), cheio()
    cj = Conjurador(TECNICAS["boneco_de_palha"])
    cj.usar(1, corpo, (0, 0), g)
    assert rodar(cj, corpo, [alvo], 0.05) == [] and alvo.vida == alvo.vida_max


def test_azul_explode_no_cursor_depois_do_atraso_e_puxa():
    corpo, alvo, g = Corpo(500, 500), Alvo(800, 560), cheio()
    cj = Conjurador(TECNICAS["ilimitado"])
    cj.usar(0, corpo, (800, 500), g)
    assert rodar(cj, corpo, [alvo], 0.2) == []  # ainda carregando
    rodar(cj, corpo, [alvo], 0.25)
    assert alvo.vida < alvo.vida_max and alvo.y < 560  # puxado para o centro (y = 500)


def test_vermelho_atravessa_e_empurra():
    corpo, g = Corpo(500, 500), cheio()
    a1, a2 = Alvo(620, 500, vida_max=999, vida=999), Alvo(760, 500, vida_max=999, vida=999)
    cj = Conjurador(TECNICAS["ilimitado"])
    cj.usar(1, corpo, (900, 500), g)
    rodar(cj, corpo, [a1, a2], 0.05 + 300 / 950)
    assert a1.vida < 999 and a2.vida < 999 and a1.x > 620


def test_tecnica_gasta_energia_e_respeita_a_recarga():
    corpo, g = Corpo(500, 500), cheio()
    cj = Conjurador(TECNICAS["ilimitado"])
    custo = TECNICAS["ilimitado"].golpes[1].custo
    assert cj.usar(1, corpo, (900, 500), g) and g.energia == FC.energia_max - custo
    assert not cj.usar(1, corpo, (900, 500), g)  # recarregando
    g.energia = custo - 1
    cj.recargas[1] = 0
    assert not cj.usar(1, corpo, (900, 500), g)  # sem energia


def test_se_marcado_usa_o_senao_quando_nao_ha_marca():
    alvo = Alvo(0, 0)
    efeitos = [
        {
            "tipo": "se_marcado",
            "entao": [{"tipo": "dano", "valor": 50}],
            "senao": [{"tipo": "dano", "valor": 3}],
        }
    ]
    assert aplicar(efeitos, alvo, 0, 0, 1, 0) == 3


def test_tecnica_reversa_troca_energia_por_vida_com_perda():
    g, vit = cheio(), Vitalidade(FD, vida=40)
    for _ in range(120):  # 1 s segurando
        vit.reverter(DT, g, True)
    gasto = FC.energia_max - g.energia
    assert gasto == pytest.approx(FD.reversa_custo, rel=0.02)
    assert vit.vida - 40 == pytest.approx(gasto * FD.reversa_cura / FD.reversa_custo)
    assert vit.vida - 40 < gasto  # eficiência abaixo de 1


def test_reversa_sem_energia_ou_com_vida_cheia_nao_cura():
    g = Golpeador(FC)
    g.energia = 0.0001
    g.energia = 0.0
    vit = Vitalidade(FD, vida=50)
    assert not vit.reverter(DT, g, True)
    assert not Vitalidade(FD).reverter(DT, cheio(), True)


def test_reforco_segura_a_maior_parte_do_golpe_e_cobra_energia():
    g, vit = cheio(), Vitalidade(FD)
    entrou = vit.sofrer(20, g, invencivel=False, guardando=True)
    assert entrou == pytest.approx(20 * (1 - FD.guarda_reducao))
    assert g.energia == pytest.approx(FC.energia_max - 20 * FD.guarda_reducao * FD.guarda_custo)
    assert Vitalidade(FD).sofrer(20, g, invencivel=False, guardando=False) == 20
    assert Vitalidade(FD).sofrer(20, g, invencivel=True, guardando=False) == 0


def test_a_maldicao_avisa_antes_de_bater_e_atordoar_cancela():
    fm = FeelMaldicao.carregar()
    ia, alvo, corpo = IAMaldicao(fm, t_espera=0), Alvo(500, 500), Corpo(560, 500)
    assert ia.atualizar(DT, alvo, corpo) == 0 and ia.carregando
    alvo.t_atordoado = 0.5
    ia.atualizar(DT, alvo, corpo)
    assert not ia.carregando
    alvo.t_atordoado = 0
    ia.t_espera = 0
    danos = [ia.atualizar(DT, alvo, corpo) for _ in range(int(fm.carga / DT) + 3)]
    assert max(danos) == fm.dano
