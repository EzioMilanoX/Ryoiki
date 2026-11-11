"""A vida do feiticeiro e o que a energia faz por ela (v0, passo 3).

- **Técnica Reversa**: segurar o botão converte energia em cura, devagar e caro (a
  eficiência fica abaixo de 1, como no anime). Enquanto cura, o feiticeiro quase não anda.
- **Reforço (defesa)**: segurar o botão de reforço cobre o corpo de energia. O golpe que
  entra perde a maior parte do dano, e a parte absorvida custa energia. Sem energia, sem
  defesa.

Lógica pura. A energia mora no `Golpeador` (o tanque é um só).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

from ryoiki.movimento import DADOS


@dataclass(frozen=True)
class FeelDefesa:
    vida_max: float = 100.0
    reversa_custo: float = 30.0  # energia por segundo
    reversa_cura: float = 15.0  # vida por segundo (eficiência 0,5)
    reversa_lentidao: float = 0.25
    guarda_reducao: float = 0.75  # fração do dano que o reforço segura
    guarda_custo: float = 0.8  # energia por ponto de dano absorvido
    guarda_lentidao: float = 0.55
    renascer: float = 2.0  # s até a arena recomeçar depois da derrota

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> FeelDefesa:
        dados = json.loads((caminho or DADOS / "feel.json").read_text(encoding="utf-8"))
        bruto = dados.get("defesa", {})
        nomes = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in bruto.items() if k in nomes})


@dataclass
class Vitalidade:
    feel: FeelDefesa
    vida: float = -1.0
    curando: bool = False
    t_ferido: float = 0.0  # o clarão vermelho de quando apanha
    t_bloqueio: float = 0.0  # o escudo acende quando segura um golpe

    def __post_init__(self) -> None:
        if self.vida < 0:
            self.vida = self.feel.vida_max

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    def passo(self, dt: float) -> None:
        self.t_ferido = max(0.0, self.t_ferido - dt)
        self.t_bloqueio = max(0.0, self.t_bloqueio - dt)

    def reverter(self, dt: float, golpeador, segurando: bool) -> bool:
        """Um quadro de Técnica Reversa. True se curou alguma coisa."""
        f = self.feel
        self.curando = segurando and self.vivo and self.vida < f.vida_max and golpeador.energia > 0
        if not self.curando:
            return False
        gasto = min(golpeador.energia, f.reversa_custo * dt)
        golpeador.energia -= gasto
        self.vida = min(f.vida_max, self.vida + gasto * f.reversa_cura / f.reversa_custo)
        return True

    def sofrer(self, dano: float, golpeador, *, invencivel: bool, guardando: bool) -> float:
        """Recebe um golpe. Devolve o dano que de fato entrou."""
        if invencivel or not self.vivo:
            return 0.0
        f = self.feel
        if guardando and golpeador.energia > 0:
            absorvido = min(dano * f.guarda_reducao, golpeador.energia / f.guarda_custo)
            golpeador.energia -= absorvido * f.guarda_custo
            dano -= absorvido
            self.t_bloqueio = 0.25
        self.vida = max(0.0, self.vida - dano)
        if dano > 0:
            self.t_ferido = 0.2
        return dano
