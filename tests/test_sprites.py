"""Os sprites pintados: todo chefe tem os quadros, e o desenho ancora os pés certo."""

from ryoiki import figuras, sprites
from ryoiki.chefe import carregar_chefe


class Renderer:
    def __init__(self):
        self.texturas, self.imagens = {}, []

    def load_texture(self, tid, caminho):
        self.texturas[tid] = caminho

    def draw_ui_image(self, tid, x, y, **kw):
        self.imagens.append((tid, x, y, kw))

    def draw_ui_polygon(self, *a, **kw):
        pass


def test_todo_visual_de_chefe_tem_sprite_com_os_quadros_e_o_clarao():
    r = Renderer()
    assert sprites.carregar(r) == len(figuras.DESENHOS_CHEFE)
    for nome in figuras.DESENHOS_CHEFE:
        info = sprites.CATALOGO[nome]
        assert len(info["ids"]) == len(info["flashes"]) == info["quadros"]
    for cid in ("vulcao", "mahito", "dagon", "sukuna"):
        assert carregar_chefe(cid).visual in sprites.CATALOGO
    sprites.CATALOGO.clear()


def test_o_sprite_espelha_para_a_esquerda_e_devolve_o_topo():
    r = Renderer()
    sprites.carregar(r)
    topo = figuras.desenhar_chefe("rei", r, 300, 400, 26, 0.0, (-1.0, 0.0), ferido=True)
    assert topo < 400
    base, clarao = r.imagens
    assert base[3]["flip_x"] and clarao[0] in sprites.CATALOGO["rei"]["flashes"]
    sprites.CATALOGO.clear()  # os outros testes desenham por primitivas
