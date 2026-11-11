"""A rota (v1, passo 4): lutas em sequência, com recompensas entre elas. Lógica pura.

- As lutas e as recompensas vêm de `data/rota.json`. O `grau` de cada luta multiplica a vida
  e o dano do chefe (`escalar`).
- A vida passa de uma luta para a outra, com uma cura parcial no meio.
- Entre lutas, o jogador escolhe 1 de 3 recompensas. **Bênçãos** só dão; **votos** são trocas
  (ganha de um lado, paga do outro), como os votos vinculantes. Cada uma só vem uma vez.
- As recompensas mexem nos feels (`mods`), então valem para tudo que lê aquele feel.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, replace
from pathlib import Path

from ryoiki.chefe import DadosChefe, carregar_chefe
from ryoiki.combate import FeelCombate
from ryoiki.defesa import FeelDefesa
from ryoiki.dominio import FeelDominio
from ryoiki.movimento import DADOS, Feel

FEELS = {"combate", "defesa", "dominio", "movimento"}


@dataclass(frozen=True)
class Recompensa:
    id: str
    nome: str
    tipo: str  # bencao | voto
    descricao: str
    mods: tuple[dict, ...]


@dataclass(frozen=True)
class DadosRota:
    lutas: tuple[tuple[str, float], ...]  # (chefe, grau)
    recompensas: tuple[Recompensa, ...]
    cura_entre_lutas: float


def carregar_rota(caminho: Path | None = None) -> DadosRota:
    d = json.loads((caminho or DADOS / "rota.json").read_text(encoding="utf-8"))
    recs = []
    for r in d["recompensas"]:
        for m in r["mods"]:
            if m["feel"] not in FEELS or m["op"] not in ("mult", "soma"):
                raise ValueError(f"{r['id']}: mod inválido {m}")
        recs.append(Recompensa(r["id"], r["nome"], r["tipo"], r["descricao"], tuple(r["mods"])))
    lutas = tuple((lu["chefe"], float(lu["grau"])) for lu in d["lutas"])
    return DadosRota(lutas, tuple(recs), float(d.get("cura_entre_lutas", 0)))


def escalar(dados: DadosChefe, grau: float) -> DadosChefe:
    """O mesmo chefe, mais forte: vida e todo dano multiplicados pelo grau."""
    if grau == 1:
        return dados
    padroes = tuple(
        replace(p, p={**p.p, "dano": p.p["dano"] * grau} if "dano" in p.p else p.p)
        for p in dados.padroes
    )
    dominio = replace(dados.dominio, dano_tique=dados.dominio.dano_tique * grau)
    fases = tuple(
        (
            limiar,
            {
                **novos,
                "padroes": tuple(
                    replace(p, p={**p.p, "dano": p.p["dano"] * grau} if "dano" in p.p else p.p)
                    for p in novos["padroes"]
                ),
            }
            if "padroes" in novos
            else novos,
        )
        for limiar, novos in dados.fases
    )
    return replace(dados, vida=dados.vida * grau, padroes=padroes, dominio=dominio, fases=fases)


def _aplicar(feel, mods: list[dict]):
    valores = {}
    for m in mods:
        atual = valores.get(m["campo"], getattr(feel, m["campo"]))
        if isinstance(atual, tuple):
            novo = tuple(x * m["valor"] if m["op"] == "mult" else x + m["valor"] for x in atual)
        elif m["op"] == "mult":
            novo = atual * m["valor"]
        else:
            novo = atual + m["valor"]
        valores[m["campo"]] = novo
    return replace(feel, **valores) if valores else feel


@dataclass
class Rota:
    dados: DadosRota
    rng: random.Random = field(default_factory=random.Random)
    indice: int = 0  # a luta atual
    escolhidas: list[Recompensa] = field(default_factory=list)
    vida: float | None = None  # None: começa a próxima luta com a vida cheia
    acabou: bool = False
    venceu: bool = False

    @property
    def total(self) -> int:
        return len(self.dados.lutas)

    def chefe_atual(self) -> DadosChefe:
        cid, grau = self.dados.lutas[self.indice]
        return escalar(carregar_chefe(cid), grau)

    def feels(self) -> dict:
        """Os feels base com todas as recompensas escolhidas aplicadas."""
        base = {
            "movimento": Feel.carregar(),
            "combate": FeelCombate.carregar(),
            "defesa": FeelDefesa.carregar(),
            "dominio": FeelDominio.carregar(),
        }
        for nome in base:
            mods = [m for r in self.escolhidas for m in r.mods if m["feel"] == nome]
            base[nome] = _aplicar(base[nome], mods)
        d = base["defesa"]
        base["defesa"] = replace(
            d, vida_max=max(10.0, d.vida_max), guarda_reducao=min(0.95, max(0.0, d.guarda_reducao))
        )
        return base

    def oferecer(self, n: int = 3) -> list[Recompensa]:
        tomadas = {r.id for r in self.escolhidas}
        livres = [r for r in self.dados.recompensas if r.id not in tomadas]
        return self.rng.sample(livres, min(n, len(livres)))

    def terminar_luta(self, venceu: bool, vida: float) -> None:
        if not venceu:
            self.acabou, self.venceu = True, False
            return
        self.indice += 1
        if self.indice >= self.total:
            self.acabou, self.venceu = True, True
            return
        vida_max = self.feels()["defesa"].vida_max
        self.vida = min(vida_max, vida + self.dados.cura_entre_lutas)

    def escolher(self, r: Recompensa) -> None:
        self.escolhidas.append(r)
        vida_max = self.feels()["defesa"].vida_max
        if self.vida is not None:
            self.vida = min(self.vida, vida_max)
