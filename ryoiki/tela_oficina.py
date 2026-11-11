"""A tela da oficina (v1, passo 3): montar a técnica própria peça por peça.

W/S escolhe a linha, A/D troca a peça, Espaço na última linha salva, Esc volta sem salvar.
As regras (peças, custo, gravação) ficam em `oficina.py`.
"""

from __future__ import annotations

import math

from ouroboros.bootstrap.scene import IScene

from ryoiki import oficina as of
from ryoiki import visual as v
from ryoiki.tela_arena import ALTURA, LARGURA

OPCOES_EFEITO = [of.VAZIO, *of.EFEITOS]
OPCOES_FORMA = list(of.FORMAS)


class OficinaScene(IScene):
    def __init__(self, entrada, ao_voltar, caminho=None) -> None:
        self.entrada = entrada
        self.ao_voltar = ao_voltar
        self.caminho = caminho
        self.montagem = of.carregar(caminho) or of.Montagem()
        self.linha = 0
        self.relogio = 0.0
        self.aviso = ("", 0.0)
        # cada linha: ("cor",) | ("forma", golpe) | ("efeito", golpe, posição) | ("salvar",)
        self.linhas: list[tuple] = [("cor",), ("nome",)]
        for gi in range(len(self.montagem.golpes)):
            self.linhas.append(("forma", gi))
            self.linhas += [("efeito", gi, k) for k in range(of.MAX_EFEITOS)]
        self.linhas.append(("salvar",))

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self.aviso = (self.aviso[0], max(0.0, self.aviso[1] - delta_time))
        e = self.entrada
        if e.is_action_pressed("sair"):
            self.ao_voltar()
            return
        n = len(self.linhas)
        if e.is_action_pressed("cima"):
            self.linha = (self.linha - 1) % n
        if e.is_action_pressed("baixo"):
            self.linha = (self.linha + 1) % n
        passo = int(e.is_action_pressed("direita")) - int(e.is_action_pressed("esquerda"))
        if passo:
            self.trocar(passo)
        if e.is_action_pressed("confirmar") and self.linhas[self.linha][0] == "salvar":
            self.salvar()

    def trocar(self, passo: int) -> None:
        linha, m = self.linhas[self.linha], self.montagem
        if linha[0] == "cor":
            m.cor = (m.cor + passo) % len(of.CORES)
        elif linha[0] == "nome":
            m.nome = (m.nome + passo) % len(of.NOMES)
        elif linha[0] == "forma":
            g = m.golpes[linha[1]]
            g.forma = OPCOES_FORMA[(OPCOES_FORMA.index(g.forma) + passo) % len(OPCOES_FORMA)]
        elif linha[0] == "efeito":
            g, k = m.golpes[linha[1]], linha[2]
            i = OPCOES_EFEITO.index(g.efeitos[k])
            g.efeitos[k] = OPCOES_EFEITO[(i + passo) % len(OPCOES_EFEITO)]

    def salvar(self) -> bool:
        if not self.montagem.valida:
            self.aviso = ("todo golpe precisa de pelo menos um efeito", 2.0)
            return False
        of.salvar(self.montagem, self.caminho)
        self.ao_voltar()
        return True

    # ------------------------------------------------------------------ desenho

    def render(self, world, r) -> None:
        m = self.montagem
        cor = (*of.CORES[m.cor], 255)
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, v.NOITE)
        r.draw_text(
            LARGURA / 2,
            40,
            "術式を作る",
            40,
            v.a(cor, 230),
            anchor="center",
            font_id=v.FONTE_PINCEL,
        )
        r.draw_text(
            LARGURA / 2,
            74,
            "oficina: monte a sua técnica com os blocos",
            13,
            v.a(v.TINTA, 150),
            anchor="center",
        )
        y = 112
        for i, linha in enumerate(self.linhas):
            sel = i == self.linha
            if linha[0] == "forma":
                y += 10
                g = m.golpes[linha[1]]
                r.draw_text(
                    60,
                    y,
                    f"Golpe {linha[1] + 1} ({'E' if linha[1] == 0 else 'Q'})",
                    15,
                    v.a(cor, 220),
                    font_id=v.FONTE_PINCEL,
                )
                r.draw_text(
                    560,
                    y,
                    f"{g.custo:.0f} de energia · recarga {g.recarga:.1f} s",
                    13,
                    v.a(v.TINTA, 170),
                )
                y += 24
            rotulo, valor = self._texto(linha)
            if sel:
                r.draw_ui_rect(70, y - 3, 820, 24, v.a(cor, 45))
                pulso = 0.6 + 0.4 * math.sin(self.relogio * 6)
                r.draw_text(78, y, ">", 14, v.a(cor, 255 * pulso))
            r.draw_text(96, y, rotulo, 14, v.a(v.TINTA, 230 if sel else 140))
            if linha[0] == "cor":
                r.draw_ui_rect(330, y + 1, 60, 14, cor)
            r.draw_text(330, y, valor, 14, v.a(cor if sel else v.TINTA, 255 if sel else 170))
            y += 26 if linha[0] != "salvar" else 0
        r.draw_text(
            LARGURA / 2,
            ALTURA - 40,
            "o domínio próprio garante os efeitos do golpe 1 (metade do dano, sem puxar)",
            12,
            v.a(v.TINTA, 120),
            anchor="center",
        )
        r.draw_text(
            LARGURA / 2,
            ALTURA - 18,
            "W/S linha · A/D troca · Espaço salva · Esc volta",
            12,
            v.a(v.TINTA, 110),
            anchor="center",
        )
        texto, t = self.aviso
        if t > 0:
            r.draw_text(
                LARGURA / 2, 92, texto, 14, v.a(v.SANGUE, 255 * min(1.0, t)), anchor="center"
            )

    def _texto(self, linha) -> tuple[str, str]:
        m = self.montagem
        if linha[0] == "cor":
            return "Cor", ""
        if linha[0] == "nome":
            fim, kanji = of.NOMES[m.nome % len(of.NOMES)]
            return "Nome", f"Técnica {fim}"
        if linha[0] == "forma":
            return "  forma", of.FORMAS[m.golpes[linha[1]].forma][0]
        if linha[0] == "efeito":
            e = m.golpes[linha[1]].efeitos[linha[2]]
            return f"  efeito {linha[2] + 1}", of.EFEITOS[e][0] if e else "(vazio)"
        return "", "Salvar e voltar" + ("" if m.valida else "  (falta efeito)")
