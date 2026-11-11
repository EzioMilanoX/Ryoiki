"""O título (escolher técnica e chefe) e a pausa da arena, com uma entrada falsa."""

from ryoiki.tela_arena import ArenaScene
from ryoiki.tela_titulo import TituloScene


class Entrada:
    def __init__(self):
        self.apertos, self.seguros = set(), set()

    def is_action_pressed(self, acao):
        return acao in self.apertos

    def is_action_held(self, acao):
        return acao in self.seguros

    def get_cursor_position(self):
        return (480, 270)


def apertar(cena, entrada, *acoes):
    for acao in acoes:
        entrada.apertos = {acao}
        cena.update(None, 1 / 60)
    entrada.apertos = set()


def test_o_titulo_troca_a_tecnica_e_entra_na_luta_com_ela():
    e, lutas = Entrada(), []
    titulo = TituloScene(e, lutas.append)
    antes = titulo.tecnica.id
    apertar(titulo, e, "direita")
    assert titulo.tecnica.id != antes
    apertar(titulo, e, "confirmar")
    assert len(lutas) == 1 and isinstance(lutas[0], ArenaScene)
    assert lutas[0].conjurador.tecnica.id == titulo.tecnica.id
    assert lutas[0].chefe.dados.id == titulo.chefe.id


def test_a_lista_de_tecnicas_volta_ao_inicio():
    e = Entrada()
    titulo = TituloScene(e, lambda arena: None)
    antes = titulo.tecnica.id
    apertar(titulo, e, *["direita"] * len(titulo.ids))
    assert titulo.tecnica.id == antes


def test_esc_pausa_e_o_mundo_para():
    e = Entrada()
    arena = ArenaScene(e)
    apertar(arena, e, "pausa")
    assert arena.pausado
    x = arena.alvo.x
    arena.chefe.t_espera = 0
    for _ in range(120):
        arena.update(None, 1 / 60)
    assert arena.alvo.x == x and arena.chefe.estado == "andando"
    apertar(arena, e, "pausa")
    assert not arena.pausado


def test_a_pausa_recomeca_a_luta_e_volta_ao_titulo():
    e, voltas = Entrada(), []
    arena = ArenaScene(e, ao_titulo=lambda: voltas.append(1))
    arena.alvo.vida = 10
    apertar(arena, e, "pausa", "baixo", "confirmar")  # Recomeçar a luta
    assert not arena.pausado and arena.alvo.vida == arena.alvo.vida_max
    apertar(arena, e, "pausa", "baixo", "baixo", "confirmar")  # Voltar ao título
    assert voltas == [1]
    assert "Sair do jogo" not in arena.opcoes  # sem ao_sair, não oferece


def test_segurar_o_reforco_sob_o_dominio_dele_vira_dominio_simples():
    e = Entrada()
    arena = ArenaScene(e)
    arena.chefe.t_espera = 99
    arena.chefe.t_dominio, arena.chefe.t_tique = 5.0, 0.4
    e.seguros = {"reforco"}
    vida = arena.vitalidade.vida
    for _ in range(90):
        arena.update(None, 1 / 60)
    assert arena.expansao.simples and arena.vitalidade.vida == vida
