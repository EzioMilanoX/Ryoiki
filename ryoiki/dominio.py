"""O Domínio do jogador, o choque de domínios e o Domínio Simples (v0, passo 5). Lógica pura.

- **Expandir (F):** só com a barra de energia cheia; gasta `custo`. A cada tique, os efeitos do
  domínio da técnica (`tecnicas.json`) pegam o chefe onde ele estiver: é o acerto garantido.
  Quando acaba, a técnica do jogador fica **queimada** (sem E/Q) por uns segundos.
- **Choque:** se os dois domínios estão abertos ao mesmo tempo, o acerto garantido dos dois
  se anula e o tempo deles para. Uma barra vai de 0 (você perde) a 1 (você vence); o mais
  refinado empurra sozinho. O jogador escolhe como empurrar de volta: **segurar F** queima
  energia (que faria falta para curar e defender) ou **bater no chefe** (arriscado, ele
  continua atacando). Quem perde tem o domínio quebrado e a técnica queimada.
- **Domínio Simples (segure C):** um círculo em volta do jogador anula o acerto garantido do
  domínio inimigo. Custa energia por segundo e não deixa andar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path

from ryoiki.movimento import DADOS
from ryoiki.tecnica import Acerto, DadosDominio, Tecnica, aplicar


@dataclass(frozen=True)
class FeelDominio:
    custo: float = 70.0  # precisa da barra cheia, gasta isto
    queimado: float = 6.0  # s sem técnica depois do domínio
    choque_bomba: float = 30.0  # energia/s queimada segurando F no choque
    choque_por_energia: float = 0.008  # o quanto cada ponto de energia empurra a barra
    choque_por_dano: float = 0.004  # o quanto cada ponto de dano no chefe empurra
    simples_custo: float = 10.0  # energia/s do Domínio Simples

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> FeelDominio:
        dados = json.loads((caminho or DADOS / "feel.json").read_text(encoding="utf-8"))
        bruto = dados.get("dominio", {})
        nomes = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in bruto.items() if k in nomes})


@dataclass
class Expansao:
    feel: FeelDominio
    dados: DadosDominio | None = None  # o domínio aberto agora
    t_dominio: float = 0.0
    t_tique: float = 0.0
    t_queimado: float = 0.0
    choque: float | None = None  # 0..1 no choque de domínios; None fora dele
    simples: bool = False
    eventos: list[str] = field(default_factory=list)  # para o desenho; a cena esvazia

    @property
    def ativo(self) -> bool:
        return self.t_dominio > 0

    @property
    def queimado(self) -> bool:
        return self.t_queimado > 0

    @property
    def em_choque(self) -> bool:
        return self.choque is not None

    def pode_expandir(self, golpeador, tecnica: Tecnica) -> bool:
        return (
            tecnica.dominio is not None
            and not self.ativo
            and not self.queimado
            and golpeador.energia >= golpeador.feel.energia_max
        )

    def expandir(self, golpeador, tecnica: Tecnica) -> bool:
        if not self.pode_expandir(golpeador, tecnica):
            return False
        golpeador.energia -= self.feel.custo
        self.dados = tecnica.dominio
        self.t_dominio = self.dados.duracao
        self.t_tique = self.dados.tique * 0.5  # o primeiro acerto vem logo
        self.simples = False
        self.eventos.append("expandir")
        return True

    def atualizar(
        self,
        dt: float,
        golpeador,
        chefe,
        *,
        bombeando: bool = False,
        segurando_simples: bool = False,
        dano_causado: float = 0.0,
    ) -> list[Acerto]:
        """Um quadro. `dano_causado`: o dano que o jogador deu no chefe neste quadro."""
        f = self.feel
        self.t_queimado = max(0.0, self.t_queimado - dt)
        self.simples = segurando_simples and not self.ativo and golpeador.energia > 0
        if self.simples:
            golpeador.energia -= min(golpeador.energia, f.simples_custo * dt)
        if not self.ativo:
            return []
        if chefe.dominio_ativo and chefe.alvo.vivo:
            self._choque(dt, golpeador, chefe, bombeando, dano_causado)
            return []
        if self.em_choque:  # o domínio dele acabou por outro motivo
            self.choque, chefe.em_choque = None, False
        acertos = []
        self.t_dominio = max(0.0, self.t_dominio - dt)
        self.t_tique -= dt
        al = chefe.alvo
        if self.t_tique <= 0:
            self.t_tique += self.dados.tique
            if al.vivo:
                dano = aplicar(self.dados.efeitos, al, al.x, al.y, 0.0, 0.0)
                acertos.append(Acerto(al.x, al.y, dano, "dominio"))
        if not self.ativo:
            self.eventos.append("fim")
            self._desfazer()
        return acertos

    def _choque(self, dt, golpeador, chefe, bombeando: bool, dano_causado: float) -> None:
        f = self.feel
        if not self.em_choque:
            self.choque, chefe.em_choque = 0.5, True
            self.eventos.append("choque")
        empurrao = (self.dados.refinamento - chefe.dados.dominio.refinamento) * dt
        empurrao += dano_causado * f.choque_por_dano
        if bombeando and golpeador.energia > 0:
            gasto = min(golpeador.energia, f.choque_bomba * dt)
            golpeador.energia -= gasto
            empurrao += gasto * f.choque_por_energia
        self.choque += empurrao
        if self.choque >= 1:
            chefe.quebrar_dominio()
            self.choque = None
            self.eventos.append("venceu")
        elif self.choque <= 0:
            chefe.em_choque = False
            self.eventos.append("perdeu")
            self._desfazer()

    def _desfazer(self) -> None:
        self.t_dominio, self.dados, self.choque = 0.0, None, None
        self.t_queimado = self.feel.queimado
