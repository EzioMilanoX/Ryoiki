"""A técnica amaldiçoada como dados (v0, passo 3).

Cada técnica (`data/tecnicas.json`) tem golpes; cada golpe é uma lista de **blocos**:

- **formas** dizem *onde* a técnica pega: `projetil` (sai na mira), `area` (explode depois de
  um atraso, em você ou no cursor) e `marcados` (todo alvo marcado, esteja onde estiver);
- **efeitos** dizem *o que* acontece com quem foi pego: `dano`, `puxar`, `empurrar`, `marcar`,
  `atordoar` e a condição `se_marcado` (com `entao`, `senao` e `consome`).

Personagem novo é conteúdo, não código: basta outra combinação de blocos. Lógica pura.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from ryoiki.combate import Alvo
from ryoiki.movimento import DADOS, Corpo

FORMAS = {"projetil", "area", "marcados"}
EFEITOS = {"dano", "puxar", "empurrar", "marcar", "atordoar", "se_marcado"}


@dataclass(frozen=True)
class GolpeTecnica:
    id: str
    nome: str
    custo: float
    recarga: float
    blocos: tuple[dict, ...]
    cor: tuple[int, int, int, int] | None = None  # sem cor: a da técnica


@dataclass(frozen=True)
class Tecnica:
    id: str
    nome: str
    kanji: str
    cor: tuple[int, int, int, int]
    golpes: tuple[GolpeTecnica, ...]
    dominio: DadosDominio | None = None


@dataclass(frozen=True)
class DadosDominio:
    """O domínio da técnica: a cada `tique`, os `efeitos` pegam o alvo onde ele estiver."""

    nome: str
    kanji: str
    duracao: float
    tique: float
    refinamento: float  # o empurrão por segundo no choque de domínios
    efeitos: tuple[dict, ...]


def _validar_efeitos(efeitos: list, onde: str) -> None:
    for e in efeitos:
        if e.get("tipo") not in EFEITOS:
            raise ValueError(f"{onde}: efeito desconhecido {e.get('tipo')!r}")
        if e["tipo"] == "se_marcado":
            _validar_efeitos(e.get("entao", []), onde)
            _validar_efeitos(e.get("senao", []), onde)


def carregar_tecnicas(
    caminho: Path | None = None, propria: Path | None = None
) -> dict[str, Tecnica]:
    """As técnicas do jogo e, se o jogador montou uma na oficina, a dele (id `propria`)."""
    from ryoiki.oficina import ID_PROPRIA, caminho_proprio

    dados = json.loads((caminho or DADOS / "tecnicas.json").read_text(encoding="utf-8"))
    tecnicas = {tid: _ler_tecnica(tid, t) for tid, t in dados["tecnicas"].items()}
    arquivo = propria or caminho_proprio()
    if arquivo.exists():
        try:
            bruto = json.loads(arquivo.read_text(encoding="utf-8"))["tecnica"]
            tecnicas[ID_PROPRIA] = _ler_tecnica(ID_PROPRIA, bruto)
        except (ValueError, KeyError, TypeError):
            pass  # arquivo estragado: segue sem a técnica própria
    return tecnicas


def _ler_tecnica(tid: str, t: dict) -> Tecnica:
    golpes = []
    for g in t["golpes"]:
        onde = f"{tid}.{g['id']}"
        for b in g["blocos"]:
            if b.get("tipo") not in FORMAS:
                raise ValueError(f"{onde}: forma desconhecida {b.get('tipo')!r}")
            _validar_efeitos(b.get("efeitos", []), onde)
        golpes.append(
            GolpeTecnica(
                g["id"],
                g["nome"],
                g["custo"],
                g["recarga"],
                tuple(g["blocos"]),
                (*g["cor"], 255) if "cor" in g else None,
            )
        )
    cor = tuple(t.get("cor", [90, 160, 255])) + (255,)
    dominio = None
    if "dominio" in t:
        d = t["dominio"]
        _validar_efeitos(d["efeitos"], f"{tid}.dominio")
        dominio = DadosDominio(
            d["nome"],
            d["kanji"],
            d["duracao"],
            d["tique"],
            d["refinamento"],
            tuple(d["efeitos"]),
        )
    return Tecnica(tid, t["nome"], t["kanji"], cor[:4], tuple(golpes), dominio)


@dataclass
class Projetil:
    x: float
    y: float
    dx: float
    dy: float
    velocidade: float
    raio: float
    restante: float  # px até sumir
    efeitos: tuple[dict, ...]
    atravessa: bool = False
    cor: tuple = (90, 160, 255, 255)
    atingidos: set[int] = field(default_factory=set)
    vivo: bool = True


@dataclass
class AreaPendente:
    x: float
    y: float
    raio: float
    t: float  # s até explodir
    atraso: float
    efeitos: tuple[dict, ...]
    cor: tuple = (90, 160, 255, 255)


@dataclass(frozen=True)
class Acerto:
    """Para o desenho: onde a técnica pegou e quanto doeu."""

    x: float
    y: float
    dano: float
    forma: str
    raio: float = 0.0
    cor: tuple = (90, 160, 255, 255)


def aplicar(efeitos, alvo: Alvo, ox: float, oy: float, dx: float, dy: float) -> float:
    """Aplica os efeitos no alvo. (ox, oy): o centro de quem puxa; (dx, dy): a direção do
    golpe (para empurrar). Devolve o dano causado."""
    dano = 0.0
    for e in efeitos:
        tipo = e["tipo"]
        if tipo == "dano":
            alvo.receber(e["valor"], 0.0, 0.0, 0.0)
            dano += e["valor"]
        elif tipo in ("puxar", "empurrar"):
            if tipo == "puxar":
                vx, vy = ox - alvo.x, oy - alvo.y
            else:
                vx, vy = dx, dy
            n = math.hypot(vx, vy)
            if n > 1e-6:
                alvo.vx += vx / n * e["forca"] / alvo.massa
                alvo.vy += vy / n * e["forca"] / alvo.massa
        elif tipo == "marcar":
            alvo.t_marca = max(alvo.t_marca, e["duracao"])
        elif tipo == "atordoar":
            alvo.t_atordoado = max(alvo.t_atordoado, e["duracao"])
        elif tipo == "se_marcado":
            marcado = alvo.marcado
            if marcado and e.get("consome"):
                alvo.t_marca = 0.0
            ramo = e.get("entao", []) if marcado else e.get("senao", [])
            dano += aplicar(ramo, alvo, ox, oy, dx, dy)
    return dano


@dataclass
class Conjurador:
    """Quem usa a técnica: gasta energia do `Golpeador`, guarda as recargas e as formas no ar."""

    tecnica: Tecnica
    recargas: list[float] = field(default_factory=list)
    projeteis: list[Projetil] = field(default_factory=list)
    areas: list[AreaPendente] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.recargas = [0.0] * len(self.tecnica.golpes)

    def trocar(self, tecnica: Tecnica) -> None:
        self.tecnica = tecnica
        self.recargas = [0.0] * len(tecnica.golpes)

    def pronto(self, i: int, energia: float) -> bool:
        g = self.tecnica.golpes[i]
        return self.recargas[i] <= 0 and energia >= g.custo

    def usar(self, i: int, corpo: Corpo, cursor: tuple[float, float], golpeador) -> bool:
        """Solta o golpe `i`. False se ainda recarrega ou falta energia."""
        if i >= len(self.tecnica.golpes) or not self.pronto(i, golpeador.energia):
            return False
        g = self.tecnica.golpes[i]
        golpeador.energia -= g.custo
        self.recargas[i] = g.recarga
        mx, my = corpo.mira
        cor = g.cor or self.tecnica.cor
        for b in g.blocos:
            efeitos = tuple(b.get("efeitos", []))
            if b["tipo"] == "projetil":
                n = b.get("quantidade", 1)
                abertura = math.radians(b.get("espalhar", 0))
                base = math.atan2(my, mx)
                for k in range(n):
                    ang = base + (abertura * (k / (n - 1) - 0.5) if n > 1 else 0.0)
                    self.projeteis.append(
                        Projetil(
                            corpo.x + math.cos(ang) * corpo.raio,
                            corpo.y + math.sin(ang) * corpo.raio,
                            math.cos(ang),
                            math.sin(ang),
                            b["velocidade"],
                            b["raio"],
                            b["alcance"],
                            efeitos,
                            b.get("atravessa", False),
                            cor,
                        )
                    )
            elif b["tipo"] == "area":
                if b.get("onde") == "cursor":
                    vx, vy = cursor[0] - corpo.x, cursor[1] - corpo.y
                    d = math.hypot(vx, vy)
                    lim = b.get("distancia", 400)
                    k = min(1.0, lim / d) if d > 0 else 0.0
                    x, y = corpo.x + vx * k, corpo.y + vy * k
                else:
                    x, y = corpo.x, corpo.y
                atraso = b.get("atraso", 0.0)
                self.areas.append(AreaPendente(x, y, b["raio"], atraso, atraso, efeitos, cor))
            elif b["tipo"] == "marcados":
                self.areas.append(AreaPendente(corpo.x, corpo.y, -1, 0.0, 0.0, efeitos, cor))
        return True

    def atualizar(self, dt: float, corpo: Corpo, alvos: list[Alvo], arena) -> list[Acerto]:
        self.recargas = [max(0.0, r - dt) for r in self.recargas]
        acertos: list[Acerto] = []
        for p in self.projeteis:
            passo = p.velocidade * dt
            p.x += p.dx * passo
            p.y += p.dy * passo
            p.restante -= passo
            fora = not (0 <= p.x <= arena[0] and 0 <= p.y <= arena[1])
            if p.restante <= 0 or fora:
                p.vivo = False
                continue
            for alvo in alvos:
                if id(alvo) in p.atingidos or not alvo.vivo:
                    continue
                if math.hypot(alvo.x - p.x, alvo.y - p.y) <= alvo.raio + p.raio:
                    p.atingidos.add(id(alvo))
                    dano = aplicar(p.efeitos, alvo, corpo.x, corpo.y, p.dx, p.dy)
                    acertos.append(Acerto(p.x, p.y, dano, "projetil", cor=p.cor))
                    if not p.atravessa:
                        p.vivo = False
                        break
        self.projeteis = [p for p in self.projeteis if p.vivo]
        restantes = []
        for ar in self.areas:
            ar.t -= dt
            if ar.t > 0:
                restantes.append(ar)
                continue
            for alvo in alvos:
                if not alvo.vivo:
                    continue
                if ar.raio < 0:  # a forma `marcados`: só quem tem a marca
                    pega = alvo.marcado
                else:
                    pega = math.hypot(alvo.x - ar.x, alvo.y - ar.y) <= ar.raio + alvo.raio
                if pega:
                    dx, dy = alvo.x - ar.x, alvo.y - ar.y
                    dano = aplicar(ar.efeitos, alvo, ar.x, ar.y, dx, dy)
                    forma = "marcados" if ar.raio < 0 else "area"
                    acertos.append(Acerto(alvo.x, alvo.y, dano, forma, cor=ar.cor))
            if ar.raio > 0:
                acertos.append(Acerto(ar.x, ar.y, 0.0, "explosao", ar.raio, ar.cor))
        self.areas = restantes
        return acertos
