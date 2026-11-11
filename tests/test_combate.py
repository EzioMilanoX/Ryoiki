"""O golpe em combo, o reforço, a energia, o Kokusen e o hitstop."""

from ryoiki.combate import GOLPE, REFORCO, Alvo, FeelCombate, Golpeador
from ryoiki.movimento import Corpo

FC = FeelCombate.carregar()
DT = 1 / 120


def cena(distancia=50.0):
    corpo = Corpo(500, 500)  # mira para a direita
    alvo = Alvo(500 + distancia, 500, vida_max=9999, vida=9999)
    return corpo, alvo, Golpeador(FC)


def rodar(g, corpo, alvo, segundos, apertar_em=()):
    """Roda a simulação; `apertar_em`: instantes (s) em que o golpe é apertado."""
    impactos, t, apertos = [], 0.0, sorted(apertar_em)
    while t < segundos:
        while apertos and apertos[0] <= t:
            g.pedir(GOLPE)
            apertos.pop(0)
        impactos += g.atualizar(DT, corpo, [alvo])
        t += DT
    return impactos


def test_o_feel_do_combate_vem_do_json():
    assert FC.kokusen_mult == 2.5 and len(FC.danos) == 3


def test_o_combo_tem_tres_golpes_e_o_ultimo_e_o_mais_forte():
    corpo, alvo, g = cena()
    duracao = FC.antes + FC.ativo + FC.depois
    imps = rodar(g, corpo, alvo, 3 * duracao + 0.1, apertar_em=[0, 0.02, duracao + 0.02])
    assert [i.dano for i in imps] == list(FC.danos)
    assert [i.final for i in imps] == [False, False, True]
    assert imps[-1].hitstop == FC.hitstop_final > imps[0].hitstop == FC.hitstop


def test_o_golpe_nao_pega_quem_esta_atras():
    corpo, alvo, g = cena(distancia=-60)
    g.pedir(GOLPE)
    assert rodar(g, corpo, alvo, 0.4) == []


def test_kokusen_so_quando_o_aperto_cai_na_janela_depois_do_impacto():
    corpo, alvo, g = cena()
    impacto = FC.antes + DT  # o primeiro quadro do ativo
    imps = rodar(g, corpo, alvo, 0.6, apertar_em=[0, impacto + FC.kokusen_janela / 2])
    assert len(imps) == 2 and not imps[0].kokusen and imps[1].kokusen
    assert imps[1].dano == FC.danos[1] * FC.kokusen_mult
    assert imps[1].hitstop == FC.hitstop_kokusen
    assert g.na_zona and g.kokusens == 1


def test_esmagar_o_botao_antes_do_impacto_nao_da_kokusen():
    corpo, alvo, g = cena()
    imps = rodar(g, corpo, alvo, 0.6, apertar_em=[0, 0.01, 0.02, 0.03])
    assert len(imps) == 2 and not any(i.kokusen for i in imps)


def test_atrasado_demais_e_golpe_normal():
    corpo, alvo, g = cena()
    tarde = FC.antes + FC.kokusen_janela + 0.04
    imps = rodar(g, corpo, alvo, 0.6, apertar_em=[0, tarde])
    assert len(imps) == 2 and not imps[1].kokusen


def test_na_zona_a_janela_e_mais_larga():
    corpo, alvo, g = cena()
    g.t_zona = 3.0
    impacto = FC.antes + DT
    meio = (FC.kokusen_janela + FC.kokusen_janela_zona) / 2  # fora da janela normal
    imps = rodar(g, corpo, alvo, 0.6, apertar_em=[0, impacto + meio])
    assert imps[1].kokusen


def test_reforco_gasta_energia_e_bate_dobrado():
    corpo, alvo, g = cena()
    g.energia = FC.reforco_custo
    assert g.pedir(REFORCO)
    assert g.energia == 0
    imps = rodar(g, corpo, alvo, 0.4)
    assert imps[0].dano == FC.danos[2] * FC.reforco_mult and imps[0].final


def test_sem_energia_nao_ha_reforco():
    corpo, alvo, g = cena()
    g.energia = FC.reforco_custo - 1
    assert not g.pedir(REFORCO) and not g.atacando


def test_acertar_e_o_kokusen_devolvem_energia():
    corpo, alvo, g = cena()
    g.energia = 10
    impacto = FC.antes + DT
    rodar(g, corpo, alvo, 0.6, apertar_em=[0, impacto + 0.02])
    ganho = 2 * FC.energia_por_golpe + FC.energia_kokusen
    assert g.energia >= 10 + ganho


def test_o_combo_esfria_e_volta_ao_primeiro_golpe():
    corpo, alvo, g = cena()
    rodar(g, corpo, alvo, 0.5, apertar_em=[0])
    rodar(g, corpo, alvo, FC.combo_janela + 0.05)
    assert g.passo == 0 and g.combo == 0


def test_o_golpe_empurra_a_maldicao():
    corpo, alvo, g = cena()
    x0 = alvo.x
    rodar(g, corpo, alvo, 0.3, apertar_em=[0])
    for _ in range(30):
        alvo.passo(DT, (2000, 2000))
    assert alvo.x > x0 and alvo.vida < alvo.vida_max
