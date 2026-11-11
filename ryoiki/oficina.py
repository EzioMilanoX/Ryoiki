"""A oficina (v1, passo 3): o jogador monta a própria técnica com os blocos. Lógica pura.

Cada golpe é uma **forma** pronta mais até 3 **efeitos** prontos. O custo de energia e a
recarga saem da soma dos blocos (quem empilha efeito forte paga mais), então não dá para
montar algo de graça. O domínio da técnica própria garante os efeitos do primeiro golpe
(com metade do dano e sem empurrar/puxar).

O resultado é salvo fora do jogo (`caminho_proprio`), no mesmo formato de `tecnicas.json`,
junto com a montagem crua para reabrir na oficina. `tecnica.carregar_tecnicas` junta a
técnica própria às outras.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ID_PROPRIA = "propria"

# id: (nome, custo, bloco de forma sem os efeitos)
FORMAS: dict[str, tuple[str, float, dict]] = {
    "disparo": (
        "Disparo",
        6,
        {"tipo": "projetil", "velocidade": 820, "raio": 8, "alcance": 600},
    ),
    "leque": (
        "Leque de 3",
        12,
        {
            "tipo": "projetil",
            "quantidade": 3,
            "espalhar": 22,
            "velocidade": 780,
            "raio": 6,
            "alcance": 500,
        },
    ),
    "lanca": (
        "Lança que atravessa",
        12,
        {"tipo": "projetil", "velocidade": 960, "raio": 14, "alcance": 720, "atravessa": True},
    ),
    "explosao": (
        "Explosão no cursor",
        10,
        {"tipo": "area", "onde": "cursor", "distancia": 360, "atraso": 0.4, "raio": 110},
    ),
    "onda": (
        "Onda em volta de si",
        8,
        {"tipo": "area", "onde": "si", "atraso": 0.15, "raio": 130},
    ),
    "ressonancia": ("Todos os marcados", 10, {"tipo": "marcados"}),
}

# id: (nome, custo, efeito)
EFEITOS: dict[str, tuple[str, float, dict]] = {
    "dano_leve": ("Dano leve (6)", 3, {"tipo": "dano", "valor": 6}),
    "dano_forte": ("Dano forte (18)", 12, {"tipo": "dano", "valor": 18}),
    "puxar": ("Puxar", 5, {"tipo": "puxar", "forca": 480}),
    "empurrar": ("Empurrar", 5, {"tipo": "empurrar", "forca": 620}),
    "marcar": ("Marcar (6 s)", 4, {"tipo": "marcar", "duracao": 6}),
    "atordoar": ("Atordoar (0,5 s)", 9, {"tipo": "atordoar", "duracao": 0.5}),
    "detonar": (
        "Se marcado: 24 de dano (gasta a marca)",
        10,
        {"tipo": "se_marcado", "consome": True, "entao": [{"tipo": "dano", "valor": 24}]},
    ),
}

VAZIO = ""
MAX_EFEITOS = 3
# os nomes possíveis (a engine ainda não tem digitação): (o fim do nome, o kanji)
NOMES: list[tuple[str, str]] = [
    ("Própria", "自己"),
    ("dos Fios Rubros", "赤糸"),
    ("da Lâmina Silenciosa", "静刃"),
    ("do Eco Partido", "割響"),
    ("das Cinzas Vivas", "灰生"),
    ("do Corvo Negro", "黒鴉"),
    ("da Maré Funda", "深潮"),
    ("do Trovão Contido", "封雷"),
    ("da Flor de Ferro", "鉄花"),
    ("do Espelho Torto", "歪鏡"),
    ("da Sombra Longa", "長影"),
]

CORES: list[tuple[int, int, int]] = [
    (90, 200, 160),
    (230, 120, 80),
    (110, 150, 255),
    (235, 60, 60),
    (200, 120, 230),
    (235, 210, 90),
]


def caminho_proprio() -> Path:
    """Fora da pasta do jogo: sobrevive a atualizações e não suja o repositório."""
    base = os.environ.get("APPDATA")
    pasta = Path(base) / "Ryoiki" if base else Path.home() / ".ryoiki"
    return pasta / "tecnica_propria.json"


@dataclass
class GolpeMontado:
    forma: str = "disparo"
    efeitos: list[str] = field(default_factory=lambda: ["dano_leve", VAZIO, VAZIO])

    @property
    def ativos(self) -> list[str]:
        return [e for e in self.efeitos if e]

    @property
    def custo(self) -> float:
        return FORMAS[self.forma][1] + sum(EFEITOS[e][1] for e in self.ativos)

    @property
    def recarga(self) -> float:
        return round(0.4 + self.custo / 25, 2)

    @property
    def valido(self) -> bool:
        return bool(self.ativos)

    def bloco(self) -> dict:
        forma = dict(FORMAS[self.forma][2])
        forma["efeitos"] = [EFEITOS[e][2] for e in self.ativos]
        return forma


@dataclass
class Montagem:
    cor: int = 0
    nome: int = 0  # índice em NOMES
    golpes: list[GolpeMontado] = field(
        default_factory=lambda: [
            GolpeMontado("disparo", ["dano_leve", "marcar", VAZIO]),
            GolpeMontado("ressonancia", ["detonar", VAZIO, VAZIO]),
        ]
    )

    @property
    def valida(self) -> bool:
        return all(g.valido for g in self.golpes)

    def para_json(self) -> dict:
        """A técnica no formato de `tecnicas.json`."""
        golpes = [
            {
                "id": f"golpe_{i + 1}",
                "nome": FORMAS[g.forma][0],
                "custo": g.custo,
                "recarga": g.recarga,
                "blocos": [g.bloco()],
            }
            for i, g in enumerate(self.golpes)
        ]
        efeitos_dominio = []
        for e in self.golpes[0].ativos:
            ef = json.loads(json.dumps(EFEITOS[e][2]))
            if ef["tipo"] in ("puxar", "empurrar"):
                continue
            if ef["tipo"] == "dano":
                ef["valor"] = ef["valor"] / 2
            efeitos_dominio.append(ef)
        if not efeitos_dominio:
            efeitos_dominio = [{"tipo": "dano", "valor": 3}]
        fim, kanji = NOMES[self.nome % len(NOMES)]
        return {
            "nome": f"Técnica {fim}",
            "kanji": f"{kanji}術式",
            "cor": list(CORES[self.cor % len(CORES)]),
            "golpes": golpes,
            "dominio": {
                "nome": f"Domínio {fim}",
                "kanji": f"{kanji}領域",
                "duracao": 4.5,
                "tique": 0.5,
                "refinamento": 0.19,
                "efeitos": efeitos_dominio,
            },
        }

    def cru(self) -> dict:
        return {
            "cor": self.cor,
            "nome": self.nome,
            "golpes": [[g.forma, list(g.efeitos)] for g in self.golpes],
        }

    @classmethod
    def do_cru(cls, d: dict) -> Montagem:
        golpes = []
        for forma, efeitos in d["golpes"]:
            efeitos = [e if e in EFEITOS else VAZIO for e in efeitos][:MAX_EFEITOS]
            efeitos += [VAZIO] * (MAX_EFEITOS - len(efeitos))
            golpes.append(GolpeMontado(forma if forma in FORMAS else "disparo", efeitos))
        return cls(d.get("cor", 0), d.get("nome", 0), golpes)


def salvar(m: Montagem, caminho: Path | None = None) -> Path:
    if not m.valida:
        raise ValueError("todo golpe precisa de pelo menos um efeito")
    caminho = caminho or caminho_proprio()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = {"montagem": m.cru(), "tecnica": m.para_json()}
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return caminho


def carregar(caminho: Path | None = None) -> Montagem | None:
    caminho = caminho or caminho_proprio()
    if not caminho.exists():
        return None
    try:
        return Montagem.do_cru(json.loads(caminho.read_text(encoding="utf-8"))["montagem"])
    except (ValueError, KeyError, TypeError):
        return None  # arquivo estragado: a oficina começa do zero
