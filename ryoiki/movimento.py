"""O corpo do jogador na arena: andar, esquivar (com invencibilidade) e a câmera.

Lógica pura, sem pygame: a cena lê a entrada e chama `Corpo.passo`. Os números do feel
vêm de `data/feel.json` (`Feel.carregar`), para ajustar sem mexer em código.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields
from pathlib import Path

DADOS = Path(__file__).parent / "data"
ESCALA_Y = 0.62  # a visão 3/4 (2.5D): o chão aparece achatado na vertical


@dataclass(frozen=True)
class Feel:
    velocidade: float = 300.0  # px/s andando
    aceleracao: float = 2600.0  # px/s² até a velocidade
    atrito: float = 3200.0  # px/s² para parar sem entrada
    esquiva_velocidade: float = 950.0
    esquiva_duracao: float = 0.16
    esquiva_invencivel: float = 0.2  # um pouco mais que a esquiva: perdoa o timing
    esquiva_recarga: float = 0.45
    camera_suavidade: float = 9.0  # quanto maior, mais grudada no jogador
    camera_mira: float = 0.18  # a câmera puxa um pouco para onde você mira
    arena: tuple[float, float] = (1600.0, 1000.0)

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> Feel:
        dados = json.loads((caminho or DADOS / "feel.json").read_text(encoding="utf-8"))
        nomes = {f.name for f in fields(cls)}
        valores = {k: v for k, v in dados.items() if k in nomes}
        if "arena" in valores:
            valores["arena"] = tuple(float(x) for x in valores["arena"])
        return cls(**valores)


def normalizar(x: float, y: float) -> tuple[float, float]:
    """O vetor com tamanho no máximo 1 (a diagonal não anda mais rápido)."""
    n = math.hypot(x, y)
    return (x / n, y / n) if n > 1 else (x, y)


@dataclass
class Corpo:
    x: float
    y: float
    raio: float = 16.0
    vx: float = 0.0
    vy: float = 0.0
    mira: tuple[float, float] = (1.0, 0.0)  # para onde olha (unitário)
    t_esquiva: float = 0.0  # > 0: no meio da esquiva
    t_invencivel: float = 0.0
    t_recarga: float = 0.0
    dir_esquiva: tuple[float, float] = (1.0, 0.0)
    rastro: list[tuple[float, float]] = field(default_factory=list)  # o desenho da esquiva

    @property
    def esquivando(self) -> bool:
        return self.t_esquiva > 0

    @property
    def invencivel(self) -> bool:
        return self.t_invencivel > 0

    def esquivar(self, feel: Feel, dx: float, dy: float) -> bool:
        """Na direção (dx, dy); parado, na direção da mira. False se ainda recarrega."""
        if self.t_recarga > 0 or self.esquivando:
            return False
        d = normalizar(dx, dy)
        if d == (0.0, 0.0):
            d = self.mira
        n = math.hypot(*d) or 1.0
        self.dir_esquiva = (d[0] / n, d[1] / n)
        self.t_esquiva = feel.esquiva_duracao
        self.t_invencivel = feel.esquiva_invencivel
        self.t_recarga = feel.esquiva_duracao + feel.esquiva_recarga
        self.rastro.clear()
        return True

    def passo(self, feel: Feel, dt: float, dx: float, dy: float) -> None:
        """Um quadro: (dx, dy) é a entrada de movimento (-1..1 em cada eixo)."""
        self.t_invencivel = max(0.0, self.t_invencivel - dt)
        self.t_recarga = max(0.0, self.t_recarga - dt)
        if self.esquivando:
            self.t_esquiva = max(0.0, self.t_esquiva - dt)
            self.vx = self.dir_esquiva[0] * feel.esquiva_velocidade
            self.vy = self.dir_esquiva[1] * feel.esquiva_velocidade
            self.rastro.append((self.x, self.y))
            if not self.esquivando:  # sai da esquiva já andando, sem deslizar
                self.vx *= feel.velocidade / feel.esquiva_velocidade
                self.vy *= feel.velocidade / feel.esquiva_velocidade
        else:
            ax, ay = normalizar(dx, dy)
            alvo_x, alvo_y = ax * feel.velocidade, ay * feel.velocidade
            taxa = feel.aceleracao if (ax or ay) else feel.atrito
            self.vx = _aproximar(self.vx, alvo_x, taxa * dt)
            self.vy = _aproximar(self.vy, alvo_y, taxa * dt)
            if len(self.rastro) > 0:
                self.rastro.pop(0)
        self.x += self.vx * dt
        self.y += self.vy * dt
        w, h = feel.arena
        self.x = min(max(self.x, self.raio), w - self.raio)
        self.y = min(max(self.y, self.raio), h - self.raio)

    def mirar(self, alvo_x: float, alvo_y: float) -> None:
        d = math.hypot(alvo_x - self.x, alvo_y - self.y)
        if d > 1:
            self.mira = ((alvo_x - self.x) / d, (alvo_y - self.y) / d)


def _aproximar(v: float, alvo: float, passo: float) -> float:
    if v < alvo:
        return min(v + passo, alvo)
    return max(v - passo, alvo)


@dataclass
class Camera:
    """O centro da tela no mundo. Segue o jogador com suavidade, puxa para a mira e
    não mostra fora da arena."""

    x: float
    y: float
    tela: tuple[float, float] = (960.0, 540.0)

    def seguir(self, feel: Feel, corpo: Corpo, mira_x: float, mira_y: float, dt: float) -> None:
        alvo_x = corpo.x + (mira_x - corpo.x) * feel.camera_mira
        alvo_y = corpo.y + (mira_y - corpo.y) * feel.camera_mira
        k = 1 - math.exp(-feel.camera_suavidade * dt)
        self.x += (alvo_x - self.x) * k
        self.y += (alvo_y - self.y) * k
        w, h = feel.arena
        meio_w, meio_h = self.tela[0] / 2, self.tela[1] / 2 / ESCALA_Y
        self.x = min(max(self.x, meio_w), max(meio_w, w - meio_w))
        self.y = min(max(self.y, meio_h), max(meio_h, h - meio_h))

    def tela_de(self, x: float, y: float, z: float = 0.0) -> tuple[float, float]:
        """Do mundo (chão em x, y; altura z) para a tela, na visão 3/4."""
        return (
            x - self.x + self.tela[0] / 2,
            (y - self.y) * ESCALA_Y - z + self.tela[1] / 2,
        )

    def mundo_de(self, sx: float, sy: float) -> tuple[float, float]:
        """Da tela para o chão (o cursor aponta para um ponto do chão)."""
        return sx + self.x - self.tela[0] / 2, (sy - self.tela[1] / 2) / ESCALA_Y + self.y
