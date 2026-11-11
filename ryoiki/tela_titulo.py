"""A tela de título (v1, passos 1, 3 e 4): escolher a técnica e o chefe, e então lutar
avulso, começar a rota (lutas em sequência) ou abrir a oficina da técnica própria.

Tudo vem dos dados: uma técnica nova em `tecnicas.json` ou um chefe novo em `maldicoes.json`
aparece aqui sozinho.
"""

from __future__ import annotations

import json
import math

from ouroboros.bootstrap.scene import IScene

from ryoiki import figuras as f
from ryoiki import visual as v
from ryoiki.chefe import carregar_chefe
from ryoiki.movimento import DADOS
from ryoiki.tecnica import carregar_tecnicas
from ryoiki.tela_arena import ALTURA, LARGURA, ArenaScene


class TituloScene(IScene):
    def __init__(self, entrada, ao_lutar, ao_sair=None, ao_oficina=None, ao_rota=None) -> None:
        """`ao_lutar(cena_arena)`: quem monta o jogo empilha a arena."""
        self.entrada = entrada
        self.ao_lutar = ao_lutar
        self.ao_sair = ao_sair
        self.ao_oficina = ao_oficina
        self.ao_rota = ao_rota  # ao_rota(id da técnica)
        self.da_oficina = False  # voltando da oficina: escolhe a técnica própria
        self.tecnicas = carregar_tecnicas()
        mal = json.loads((DADOS / "maldicoes.json").read_text(encoding="utf-8"))
        self.chefes = [carregar_chefe(cid) for cid in mal["maldicoes"]]
        inicial = json.loads((DADOS / "tecnicas.json").read_text(encoding="utf-8"))["jogador"]
        self.ids = list(self.tecnicas)
        self.i_tecnica = self.ids.index(inicial)
        self.i_chefe = self.chefes.index(next(c for c in self.chefes if c.id == mal["chefe"]))
        self.linha = 0  # 0: técnica, 1: chefe, 2: as ações (lutar, rota, oficina)
        self.acao = 0
        self.relogio = 0.0

    @property
    def tecnica(self):
        return self.tecnicas[self.ids[self.i_tecnica]]

    @property
    def chefe(self):
        return self.chefes[self.i_chefe]

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        e = self.entrada
        if e.is_action_pressed("sair") and self.ao_sair is not None:
            self.ao_sair()
            return
        if e.is_action_pressed("cima"):
            self.linha = (self.linha - 1) % 3
        if e.is_action_pressed("baixo"):
            self.linha = (self.linha + 1) % 3
        passo = int(e.is_action_pressed("direita")) - int(e.is_action_pressed("esquerda"))
        if passo and self.linha == 0:
            self.i_tecnica = (self.i_tecnica + passo) % len(self.ids)
        elif passo and self.linha == 1:
            self.i_chefe = (self.i_chefe + passo) % len(self.chefes)
        elif passo and self.linha == 2:
            self.acao = (self.acao + passo) % len(self.acoes)
        if e.is_action_pressed("confirmar") or (self.linha == 2 and e.is_action_pressed("golpe")):
            self.executar(self.acoes[self.acao][0] if self.linha == 2 else "lutar")

    @property
    def acoes(self) -> list[tuple[str, str]]:
        """As ações da última linha (só as que o jogo montou)."""
        out = [("lutar", "戦う  lutar")]
        if self.ao_rota is not None:
            out.append(("rota", "巡り  rota"))
        if self.ao_oficina is not None:
            out.append(("oficina", "術式を作る  oficina"))
        return out

    def executar(self, acao: str) -> None:
        if acao == "oficina":
            self.da_oficina = True
            self.ao_oficina()
        elif acao == "rota":
            self.ao_rota(self.tecnica.id)
        else:
            self.ao_lutar(self.criar_arena())

    def on_enter(self, world, renderer) -> None:
        """Voltando da oficina: relê as técnicas e já escolhe a própria, se ela existir."""
        from ryoiki.oficina import ID_PROPRIA

        atual = self.tecnica.id if self.i_tecnica < len(self.ids) else None
        self.tecnicas = carregar_tecnicas()
        self.ids = list(self.tecnicas)
        if self.da_oficina and ID_PROPRIA in self.tecnicas:
            self.i_tecnica = self.ids.index(ID_PROPRIA)
        elif atual in self.ids:
            self.i_tecnica = self.ids.index(atual)
        else:
            self.i_tecnica = 0
        self.da_oficina = False

    def criar_arena(self) -> ArenaScene:
        return ArenaScene(
            self.entrada,
            ao_sair=self.ao_sair,
            tecnica=self.tecnica.id,
            chefe=self.chefe.id,
        )

    # ------------------------------------------------------------------ desenho

    def render(self, world, r) -> None:
        v.fundo_titulo(r, LARGURA, ALTURA, self.relogio)
        r.draw_text(
            LARGURA / 2,
            92,
            "領域",
            110,
            v.a(v.SANGUE, 230),
            anchor="center",
            font_id=v.FONTE_PINCEL,
        )
        r.draw_text(LARGURA / 2, 168, "R Y O I K I", 22, v.a(v.TINTA, 200), anchor="center")
        t, ch = self.tecnica, self.chefe
        # o duelo no meio: o feiticeiro de um lado, o chefe do outro
        f.feiticeiro(r, 250, 345, 18, (1.0, 0.0), self.relogio, aura=0.7)
        f.desenhar_chefe(ch.visual, r, LARGURA - 250, 345, 26, self.relogio, (-1.0, 0.0))
        r.draw_text(
            LARGURA / 2,
            300,
            "対",
            46,
            v.a(v.TINTA, 120),
            anchor="center",
            font_id=v.FONTE_PINCEL,
        )
        golpes = " · ".join(g.nome for g in t.golpes)
        dom = f"domínio: {t.dominio.nome}" if t.dominio else "sem domínio"
        self._linha(r, 0, 380, f"{t.kanji}  {t.nome}", f"{golpes}  ·  {dom}", t.cor)
        self._linha(r, 1, 432, f"{ch.kanji}  {ch.nome}", ch.titulo, ch.cor)
        acoes = self.acoes
        for k, (_, rotulo) in enumerate(acoes):
            sel = self.linha == 2 and k == self.acao
            pulso = 0.7 + 0.3 * math.sin(self.relogio * 5) if sel else 0.45
            x = LARGURA / 2 + (k - (len(acoes) - 1) / 2) * 230
            if sel:
                r.draw_ui_rect(x - 105, 470, 210, 34, v.a(v.SANGUE, 50))
            r.draw_text(
                x,
                486,
                rotulo,
                21,
                v.a(v.SANGUE if sel else v.TINTA, 255 * pulso),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
        if self.linha == 2 and acoes[self.acao][0] == "rota":
            r.draw_text(
                LARGURA / 2,
                508,
                "os chefes em sequência, a vida não volta toda; entre as lutas, bênçãos e votos",
                12,
                v.a(v.TINTA, 150),
                anchor="center",
            )
        r.draw_text(
            LARGURA / 2,
            ALTURA - 16,
            "W/S escolhe a linha · A/D troca · Espaço confirma · Esc sai",
            12,
            v.a(v.TINTA, 110),
            anchor="center",
        )

    def _linha(self, r, i, y, titulo, sub, cor) -> None:
        sel = self.linha == i
        if sel:
            r.draw_ui_rect(LARGURA / 2 - 330, y - 20, 660, 46, v.a(cor, 40))
            r.draw_text(LARGURA / 2 - 310, y, "<", 18, v.a(cor, 230), anchor="center")
            r.draw_text(LARGURA / 2 + 310, y, ">", 18, v.a(cor, 230), anchor="center")
        r.draw_text(
            LARGURA / 2,
            y - 4,
            titulo,
            20,
            v.a(cor if sel else v.TINTA, 255 if sel else 170),
            anchor="center",
            font_id=v.FONTE_PINCEL,
        )
        r.draw_text(LARGURA / 2, y + 16, sub, 12, v.a(v.TINTA, 150 if sel else 90), anchor="center")
