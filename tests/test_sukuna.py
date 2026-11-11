"""O terceiro chefe: os cortes (avisados, um em cima de você) e o fim da rota."""

from ryoiki.chefe import Chefe, Corte, carregar_chefe
from ryoiki.movimento import Corpo
from ryoiki.rota import carregar_rota

SUKUNA = carregar_chefe("sukuna")
DT = 1 / 120
ARENA = (1600.0, 1000.0)


def cortar(ch, corpo):
    ch.padrao = next(p for p in SUKUNA.padroes if p.tipo == "cortes")
    ch.estado, ch.t = "carga", ch.padrao.carga
    for _ in range(int(ch.padrao.carga / DT) + 2):
        ch.atualizar(DT, corpo, ARENA)


def test_a_distancia_ate_o_corte():
    c = Corte(0, 0, 100, 0, 10, 0, 0, 5)
    assert c.distancia(50, 7) == 7 and c.distancia(130, 0) == 30


def test_os_cortes_avisam_e_o_primeiro_passa_em_cima_de_voce():
    ch, corpo = Chefe.novo(SUKUNA, 800, 500), Corpo(400, 400)
    ch.t_espera = 99
    cortar(ch, corpo)
    q = ch.padrao.p
    assert len(ch.cortes) == q["quantidade"]
    assert ch.cortes[0].distancia(400, 400) < 1
    danos = []
    for _ in range(int((q["atraso"] + q["quantidade"] * q["intervalo"]) / DT) + 5):
        danos += ch.atualizar(DT, corpo, ARENA)
    assert any(d.fonte == "corte" for d in danos) and ch.cortes == []


def test_sair_da_linha_escapa_do_corte():
    ch, corpo = Chefe.novo(SUKUNA, 800, 500), Corpo(400, 400)
    ch.t_espera = 99
    cortar(ch, corpo)
    ch.cortes = ch.cortes[:1]
    corpo.x, corpo.y = 1500, 950  # longe de tudo
    danos = []
    for _ in range(120):
        danos += ch.atualizar(DT, corpo, ARENA)
    assert not any(d.fonte == "corte" for d in danos)


def test_o_dominio_dele_e_o_mais_refinado_e_sukuna_fecha_a_rota():
    for cid in ("vulcao", "mahito"):
        assert SUKUNA.dominio.refinamento > carregar_chefe(cid).dominio.refinamento
    assert carregar_rota().lutas[-1][0] == "sukuna"
