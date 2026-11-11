"""A maldição de treino agora revida (v0, passo 3): se arrasta até você e, de tempos em
tempos, carrega uma pancada em área avisada no chão. Atordoar cancela a carga.

Serve para a Técnica Reversa e o reforço terem o que curar e o que segurar. O chefe de
verdade (vários padrões e um domínio) é o passo 4.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, fields
from pathlib import Path

from ryoiki.combate import Alvo
from ryoiki.movimento import DADOS, Corpo


@dataclass(frozen=True)
class FeelMaldicao:
    velocidade: float = 45.0  # px/s se arrastando
    gatilho: float = 190.0  # px: perto assim, ela começa a carregar
    carga: float = 0.8  # s de aviso antes da pancada
    raio: float = 100.0  # px da pancada
    dano: float = 18.0
    espera: float = 2.2  # s entre uma pancada e a próxima

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> FeelMaldicao:
        dados = json.loads((caminho or DADOS / "feel.json").read_text(encoding="utf-8"))
        bruto = dados.get("maldicao_treino", {})
        nomes = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in bruto.items() if k in nomes})


@dataclass
class IAMaldicao:
    feel: FeelMaldicao
    t_espera: float = 1.5
    t_carga: float = 0.0  # > 0: carregando a pancada

    @property
    def carregando(self) -> bool:
        return self.t_carga > 0

    @property
    def carga(self) -> float:
        """0..1: quanto da carga já passou (para o aviso no chão)."""
        return 1 - self.t_carga / self.feel.carga if self.carregando else 0.0

    def atualizar(self, dt: float, alvo: Alvo, corpo: Corpo) -> float:
        """Um quadro. Devolve o dano da pancada se ela pegou o jogador agora, senão 0."""
        f = self.feel
        if not alvo.vivo:
            self.t_carga = 0.0
            return 0.0
        if alvo.t_atordoado > 0:
            self.t_carga = 0.0  # atordoar cancela a carga
            return 0.0
        dx, dy = corpo.x - alvo.x, corpo.y - alvo.y
        d = math.hypot(dx, dy)
        if self.carregando:
            self.t_carga = max(0.0, self.t_carga - dt)
            if self.t_carga == 0:
                self.t_espera = f.espera
                return f.dano if d <= f.raio + corpo.raio else 0.0
            return 0.0
        self.t_espera = max(0.0, self.t_espera - dt)
        if d > alvo.raio + corpo.raio + 4:
            alvo.x += dx / d * f.velocidade * dt
            alvo.y += dy / d * f.velocidade * dt
        if self.t_espera == 0 and d <= f.gatilho:
            self.t_carga = f.carga
        return 0.0
