"""As telas da rota (v1, passo 4): escolher a recompensa entre as lutas e o resultado no fim.
`ControleRota` encadeia tudo: arena -> recompensa -> arena ... -> resultado.
"""

from __future__ import annotations

import math
import random

from ouroboros.bootstrap.scene import IScene

from ryoiki import visual as v
from ryoiki.rota import Recompensa, Rota, carregar_rota
from ryoiki.tela_arena import ALTURA, LARGURA, ArenaScene

COR_BENCAO = (110, 200, 160, 255)
COR_VOTO = (200, 60, 70, 255)


def quebrar(texto: str, largura: int) -> list[str]:
    """Quebra o texto em linhas de até `largura` caracteres, sem cortar palavra."""
    linhas, atual = [], ""
    for p in texto.split():
        if atual and len(atual) + 1 + len(p) > largura:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    return linhas + ([atual] if atual else [])


class ControleRota:
    """Monta cada luta com os feels da rota e troca as cenas. `empilhar`/`desempilhar` são
    as do GameLoop (ou falsas, nos testes)."""

    def __init__(self, entrada, tecnica: str, empilhar, desempilhar, rng=None, dados=None):
        self.entrada = entrada
        self.tecnica = tecnica
        self.empilhar, self.desempilhar = empilhar, desempilhar
        self.rota = Rota(dados or carregar_rota(), rng or random.Random())

    def comecar(self) -> None:
        self._luta()

    def _luta(self) -> None:
        f = self.rota.feels()
        self.empilhar(
            ArenaScene(
                self.entrada,
                feel=f["movimento"],
                feel_combate=f["combate"],
                tecnica=self.tecnica,
                ao_titulo=self.desempilhar,
                feel_defesa=f["defesa"],
                feel_dominio=f["dominio"],
                dados_chefe=self.rota.chefe_atual(),
                vida_inicial=self.rota.vida,
                ao_fim=self._fim_da_luta,
                rotulo=self.rotulo(),
            )
        )

    def rotulo(self) -> str:
        r = self.rota
        texto = f"rota: luta {r.indice + 1} de {r.total}"
        if r.escolhidas:
            texto += " · " + ", ".join(rec.nome for rec in r.escolhidas)
        return texto

    def _fim_da_luta(self, venceu: bool, vida: float) -> None:
        self.desempilhar()
        self.rota.terminar_luta(venceu, vida)
        if self.rota.acabou:
            self.empilhar(ResultadoScene(self.entrada, self.rota, self.desempilhar))
        else:
            ofertas = self.rota.oferecer()
            self.empilhar(RecompensaScene(self.entrada, self.rota, ofertas, self._escolheu))

    def _escolheu(self, r: Recompensa | None) -> None:
        self.desempilhar()
        if r is not None:
            self.rota.escolher(r)
        self._luta()


class RecompensaScene(IScene):
    def __init__(self, entrada, rota: Rota, ofertas: list[Recompensa], ao_escolher) -> None:
        self.entrada, self.rota, self.ofertas = entrada, rota, ofertas
        self.ao_escolher = ao_escolher
        self.i = 0
        self.relogio = 0.0

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        e = self.entrada
        n = len(self.ofertas)
        if not n:  # nada a oferecer: segue a rota
            self.ao_escolher(None)
            return
        passo = int(e.is_action_pressed("direita")) - int(e.is_action_pressed("esquerda"))
        self.i = (self.i + passo) % n
        if e.is_action_pressed("confirmar") or e.is_action_pressed("golpe"):
            self.ao_escolher(self.ofertas[self.i])

    def render(self, world, r) -> None:
        rota = self.rota
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, v.NOITE)
        r.draw_text(
            LARGURA / 2,
            50,
            f"祓除  luta {rota.indice} de {rota.total} vencida",
            26,
            v.a(v.TINTA, 230),
            anchor="center",
            font_id=v.FONTE_PINCEL,
        )
        vida_max = rota.feels()["defesa"].vida_max
        r.draw_text(
            LARGURA / 2,
            86,
            f"vida {rota.vida:.0f}/{vida_max:.0f} · próxima: {rota.chefe_atual().nome}"
            f" (grau {rota.dados.lutas[rota.indice][1]:.2f}) · escolha uma",
            13,
            v.a(v.TINTA, 150),
            anchor="center",
        )
        w, gap = 260, 30
        x0 = LARGURA / 2 - (len(self.ofertas) * w + (len(self.ofertas) - 1) * gap) / 2
        for k, rec in enumerate(self.ofertas):
            x, y, sel = x0 + k * (w + gap), 130, k == self.i
            cor = COR_VOTO if rec.tipo == "voto" else COR_BENCAO
            sobe = -8 + 3 * math.sin(self.relogio * 4) if sel else 0
            r.draw_ui_rect(x, y + sobe, w, 300, v.a(v.PRETO, 200))
            r.draw_ui_rect(x, y + sobe, w, 6, v.a(cor, 255 if sel else 120))
            borda = [(x, y + sobe), (x + w, y + sobe), (x + w, y + sobe + 300), (x, y + sobe + 300)]
            r.draw_ui_polygon(borda, v.a(cor, 230 if sel else 70), 2 if sel else 1)
            selo = "縛り  voto" if rec.tipo == "voto" else "祝福  bênção"
            r.draw_text(
                x + w / 2,
                y + sobe + 40,
                selo,
                18,
                v.a(cor, 230),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
            r.draw_text(
                x + w / 2,
                y + sobe + 90,
                rec.nome,
                20,
                v.a(v.TINTA, 240 if sel else 170),
                anchor="center",
            )
            for j, linha in enumerate(quebrar(rec.descricao, 30)):
                r.draw_text(
                    x + w / 2,
                    y + sobe + 140 + j * 20,
                    linha,
                    13,
                    v.a(v.TINTA, 210 if sel else 120),
                    anchor="center",
                )
        if rota.escolhidas:
            nomes = " · ".join(rec.nome for rec in rota.escolhidas)
            r.draw_text(
                LARGURA / 2,
                ALTURA - 50,
                f"já tem: {nomes}",
                12,
                v.a(v.TINTA, 120),
                anchor="center",
            )
        r.draw_text(
            LARGURA / 2,
            ALTURA - 20,
            "A/D escolhe · Enter pega",
            12,
            v.a(v.TINTA, 110),
            anchor="center",
        )


class ResultadoScene(IScene):
    def __init__(self, entrada, rota: Rota, ao_voltar) -> None:
        self.entrada, self.rota, self.ao_voltar = entrada, rota, ao_voltar

    def update(self, world, delta_time: float) -> None:
        e = self.entrada
        if e.is_action_pressed("confirmar") or e.is_action_pressed("sair"):
            self.ao_voltar()

    def render(self, world, r) -> None:
        rota = self.rota
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, v.NOITE)
        if rota.venceu:
            titulo, sub, cor = "完遂", f"rota completa: {rota.total} chefes exorcizados", v.TINTA
        else:
            titulo = "敗北"
            sub = f"a rota acabou na luta {rota.indice + 1} de {rota.total}"
            cor = v.SANGUE
        r.draw_text(
            LARGURA / 2, 170, titulo, 96, v.a(cor, 230), anchor="center", font_id=v.FONTE_PINCEL
        )
        r.draw_text(LARGURA / 2, 250, sub, 18, v.a(v.TINTA, 200), anchor="center")
        for j, rec in enumerate(rota.escolhidas):
            r.draw_text(
                LARGURA / 2,
                300 + j * 22,
                f"{rec.nome}: {rec.descricao}",
                13,
                v.a(COR_VOTO if rec.tipo == "voto" else COR_BENCAO, 200),
                anchor="center",
            )
        r.draw_text(
            LARGURA / 2,
            ALTURA - 20,
            "Enter volta ao título",
            12,
            v.a(v.TINTA, 110),
            anchor="center",
        )
