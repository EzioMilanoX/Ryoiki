"""A maldição chefe (v0, passo 4): padrões de ataque avisados e um domínio. Dados em
`data/maldicoes.json`; lógica pura.

**Padrões** (o `tipo` diz o comportamento, o resto são números do JSON):
- `investida`: mira, avisa com uma faixa no chão e atravessa a arena;
- `erupcoes`: círculos que enchem no chão (um em cima de você) e estouram;
- `brasas`: um leque de projéteis lentos;
- `invocar`: lacaios que correm até você e explodem no contato (dá para matá-los antes);
- `cortes`: riscos finos que atravessam a arena perto de você e cortam depois do aviso.

**Domínio:** quando a vida cai abaixo de cada `gatilho`, o chefe para e **entoa** (領域展開).
Dano suficiente ou um atordoamento nesse tempo **interrompe**. Se não, o domínio fecha a
arena: o acerto é **garantido** (a esquiva não salva, só o reforço reduz) até ele acabar. Depois
o chefe fica **queimado** (sem técnica) por uns segundos: é a hora de bater.

**Fases:** `fases` no JSON troca o chefe quando a vida cai abaixo de `limiar` (outro
desenho, velocidade, ritmo e padrões). Ele para um instante para se transformar.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field, replace
from pathlib import Path

from ryoiki.combate import Alvo
from ryoiki.movimento import DADOS, Corpo

TIPOS = {"investida", "erupcoes", "brasas", "invocar", "cortes"}


@dataclass(frozen=True)
class Padrao:
    id: str
    nome: str
    tipo: str
    carga: float
    recuperacao: float
    p: dict  # os números do tipo (velocidade, dano, quantidade...)


@dataclass(frozen=True)
class Dominio:
    nome: str
    kanji: str
    entoar: float
    interromper: float  # dano que corta a entoação
    duracao: float
    tique: float
    dano_tique: float
    gatilhos: tuple[float, ...]  # frações de vida que disparam o domínio
    queimado: float
    refinamento: float = 0.2  # o empurrão por segundo no choque de domínios


@dataclass(frozen=True)
class DadosChefe:
    id: str
    nome: str
    titulo: str
    kanji: str
    cor: tuple[int, int, int, int]
    vida: float
    raio: float
    massa: float
    velocidade: float
    distancia: float  # a distância que ele gosta de manter
    espera: float  # s entre um padrão e o próximo
    padroes: tuple[Padrao, ...]
    dominio: Dominio
    visual: str = "vulcao"  # qual desenho usar (visual.desenhar_chefe)
    regeneracao: float = 0.0  # vida/s, menos com a técnica queimada
    fases: tuple = ()  # ((limiar, {campo: valor novo}), ...), do maior limiar ao menor


def carregar_chefe(cid: str | None = None, caminho: Path | None = None) -> DadosChefe:
    dados = json.loads((caminho or DADOS / "maldicoes.json").read_text(encoding="utf-8"))
    cid = cid or dados["chefe"]
    c = dados["maldicoes"][cid]
    padroes = _ler_padroes(cid, c["padroes"])
    fases = []
    for f in c.get("fases", []):
        novos = {k: f[k] for k in ("visual", "velocidade", "espera", "distancia", "raio") if k in f}
        if "padroes" in f:
            novos["padroes"] = _ler_padroes(cid, f["padroes"])
        fases.append((float(f["limiar"]), novos))
    d = c["dominio"]
    dominio = Dominio(
        d["nome"],
        d["kanji"],
        d["entoar"],
        d["interromper"],
        d["duracao"],
        d["tique"],
        d["dano_tique"],
        tuple(sorted(d["gatilhos"], reverse=True)),
        d["queimado"],
        d.get("refinamento", 0.2),
    )
    return DadosChefe(
        cid,
        c["nome"],
        c["titulo"],
        c["kanji"],
        (*c["cor"], 255),
        c["vida"],
        c["raio"],
        c["massa"],
        c["velocidade"],
        c["distancia"],
        c["espera"],
        tuple(padroes),
        dominio,
        c.get("visual", "vulcao"),
        c.get("regeneracao", 0.0),
        tuple(sorted(fases, key=lambda f: -f[0])),
    )


def _ler_padroes(cid: str, brutos: list) -> tuple[Padrao, ...]:
    padroes = []
    for p in brutos:
        if p["tipo"] not in TIPOS:
            raise ValueError(f"{cid}.{p['id']}: tipo de padrão desconhecido {p['tipo']!r}")
        fixos = {"id", "nome", "tipo", "carga", "recuperacao"}
        resto = {k: v for k, v in p.items() if k not in fixos}
        padroes.append(Padrao(p["id"], p["nome"], p["tipo"], p["carga"], p["recuperacao"], resto))
    return tuple(padroes)


@dataclass
class Brasa:
    x: float
    y: float
    vx: float
    vy: float
    raio: float
    dano: float
    restante: float
    viva: bool = True


@dataclass
class Corte:
    """Um risco reto: avisa como uma linha fina e corta tudo o que estiver em cima dele."""

    x1: float
    y1: float
    x2: float
    y2: float
    largura: float
    t: float
    atraso: float
    dano: float

    def distancia(self, x: float, y: float) -> float:
        """Do ponto até o segmento."""
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        n = dx * dx + dy * dy or 1.0
        k = max(0.0, min(1.0, ((x - self.x1) * dx + (y - self.y1) * dy) / n))
        return math.hypot(x - (self.x1 + dx * k), y - (self.y1 + dy * k))


@dataclass
class Erupcao:
    x: float
    y: float
    raio: float
    t: float
    atraso: float
    dano: float


@dataclass
class Lacaio(Alvo):
    """Um lacaio invocado: corre até o jogador e explode no contato."""

    velocidade: float = 120.0
    dano: float = 8.0


@dataclass(frozen=True)
class DanoChefe:
    valor: float
    garantido: bool  # o acerto garantido do domínio: a esquiva não salva
    fonte: str


@dataclass
class Chefe:
    dados: DadosChefe
    alvo: Alvo
    rng: random.Random = field(default_factory=lambda: random.Random(7))
    estado: str = "andando"  # andando | carga | investida | recupera | entoando | queimado
    t: float = 0.0
    t_espera: float = 1.2
    padrao: Padrao | None = None
    ultimo: str = ""
    direcao: tuple[float, float] = (1.0, 0.0)
    acertou: bool = False  # a investida pega uma vez só
    t_dominio: float = 0.0
    em_choque: bool = False  # no choque, o acerto garantido se anula e o tempo para
    t_tique: float = 0.0
    vida_entoar: float = 0.0
    gatilhos: list[float] = field(default_factory=list)
    brasas: list[Brasa] = field(default_factory=list)
    erupcoes: list[Erupcao] = field(default_factory=list)
    cortes: list[Corte] = field(default_factory=list)
    lacaios: list[Lacaio] = field(default_factory=list)
    fases: list = field(default_factory=list)  # as que ainda não aconteceram
    eventos: list[tuple] = field(default_factory=list)  # para o desenho; a cena esvazia

    @classmethod
    def novo(cls, dados: DadosChefe, x: float, y: float, seed: int = 7) -> Chefe:
        alvo = Alvo(x, y, raio=dados.raio, vida_max=dados.vida, vida=dados.vida)
        alvo.massa = dados.massa
        ch = cls(dados, alvo, random.Random(seed), gatilhos=list(dados.dominio.gatilhos))
        ch.fases = list(dados.fases)
        return ch

    def _mudar_de_fase(self) -> None:
        limiar, novos = self.fases.pop(0)
        self.dados = replace(self.dados, **novos)
        if "raio" in novos:
            self.alvo.raio = novos["raio"]
        self.estado, self.t, self.ultimo = "transformando", 1.4, ""
        self.brasas.clear()
        self.erupcoes.clear()
        self.cortes.clear()
        self.eventos.append(("fase", self.alvo.x, self.alvo.y))

    @property
    def dominio_ativo(self) -> bool:
        return self.t_dominio > 0

    @property
    def progresso(self) -> float:
        """0..1 do estado atual (a carga do aviso, a entoação)."""
        if self.estado == "carga" and self.padrao:
            return 1 - self.t / self.padrao.carga
        if self.estado == "entoando":
            return 1 - self.t / self.dados.dominio.entoar
        return 0.0

    @property
    def dano_na_entoacao(self) -> float:
        return self.vida_entoar - self.alvo.vida if self.estado == "entoando" else 0.0

    # ------------------------------------------------------------------ o quadro

    def atualizar(self, dt: float, corpo: Corpo, arena) -> list[DanoChefe]:
        al = self.alvo
        if not al.vivo:
            self.brasas.clear()
            self.erupcoes.clear()
            self.cortes.clear()
            self.lacaios.clear()
            self.t_dominio = 0.0
            return []
        if self.dados.regeneracao and self.estado != "queimado":  # remodela o corpo
            al.vida = min(al.vida_max, al.vida + self.dados.regeneracao * dt)
        danos = self._perigos(dt, corpo, arena)
        danos += self._dominio(dt)
        if al.t_atordoado > 0:
            if self.estado == "entoando":
                self._interromper()
            elif self.estado in ("carga", "investida"):
                self.estado, self.t_espera = "andando", self.dados.espera
            return danos
        if (
            self.fases
            and self.estado in ("andando", "recupera", "queimado")
            and not self.dominio_ativo
            and al.vida / al.vida_max <= self.fases[0][0]
        ):
            self._mudar_de_fase()
        d = self.dados
        if self.estado == "transformando":  # parado, mudando de forma (dá para bater)
            self.t -= dt
            if self.t <= 0:
                self.estado, self.t_espera = "andando", d.espera
            return danos
        if (
            self.estado == "andando"
            and self.gatilhos
            and not self.dominio_ativo
            and al.vida / al.vida_max <= self.gatilhos[0]
        ):
            self.gatilhos.pop(0)
            self.estado, self.t, self.vida_entoar = "entoando", d.dominio.entoar, al.vida
            self.eventos.append(("entoar", al.x, al.y))
        dx, dy = corpo.x - al.x, corpo.y - al.y
        dist = math.hypot(dx, dy) or 1.0
        if self.estado == "entoando":
            self.t -= dt
            if self.dano_na_entoacao >= d.dominio.interromper:
                self._interromper()
            elif self.t <= 0:
                self.t_dominio, self.t_tique = d.dominio.duracao, d.dominio.tique
                self.estado, self.t_espera = "andando", d.espera * 0.6
                self.eventos.append(("dominio", al.x, al.y))
        elif self.estado == "andando":
            if dist > d.distancia:
                al.x += dx / dist * d.velocidade * dt
                al.y += dy / dist * d.velocidade * dt
            self.t_espera -= dt
            if self.t_espera <= 0:
                opcoes = [p for p in d.padroes if p.id != self.ultimo] or list(d.padroes)
                self.padrao = self.rng.choice(opcoes)
                self.ultimo = self.padrao.id
                self.estado, self.t = "carga", self.padrao.carga
                self.direcao = (dx / dist, dy / dist)
        elif self.estado == "carga":
            self.t -= dt
            if self.t > 0.25:  # mira até pouco antes de soltar: dá para ler e esquivar
                self.direcao = (dx / dist, dy / dist)
            if self.t <= 0:
                self._executar(corpo, arena)
        elif self.estado == "investida":
            p = self.padrao.p
            al.x += self.direcao[0] * p["velocidade"] * dt
            al.y += self.direcao[1] * p["velocidade"] * dt
            al.x = min(max(al.x, al.raio), arena[0] - al.raio)
            al.y = min(max(al.y, al.raio), arena[1] - al.raio)
            if not self.acertou and math.hypot(corpo.x - al.x, corpo.y - al.y) <= (
                al.raio + corpo.raio + 6
            ):
                self.acertou = True
                danos.append(DanoChefe(p["dano"], False, "investida"))
            self.t -= dt
            if self.t <= 0:
                self.estado, self.t = "recupera", self.padrao.recuperacao
        elif self.estado == "recupera":
            self.t -= dt
            if self.t <= 0:
                self.estado = "andando"
                self.t_espera = d.espera * (0.6 if self.dominio_ativo else 1.0)
        elif self.estado == "queimado":
            self.t -= dt
            if self.t <= 0:
                self.estado, self.t_espera = "andando", d.espera
        return danos

    def separar(self, corpo: Corpo) -> None:
        """O chefe é sólido: empurra o jogador para fora do corpo dele."""
        al = self.alvo
        dx, dy = corpo.x - al.x, corpo.y - al.y
        d = math.hypot(dx, dy)
        minimo = al.raio + corpo.raio
        if not al.vivo or d >= minimo:
            return
        if d < 1e-6:
            dx, dy, d = 1.0, 0.0, 1.0
        corpo.x = al.x + dx / d * minimo
        corpo.y = al.y + dy / d * minimo

    def _interromper(self) -> None:
        self.estado, self.t_espera = "andando", self.dados.espera
        self.alvo.t_atordoado = max(self.alvo.t_atordoado, 1.5)
        self.eventos.append(("interrompido", self.alvo.x, self.alvo.y))

    def _executar(self, corpo: Corpo, arena) -> None:
        p, al = self.padrao, self.alvo
        q = p.p
        if p.tipo == "investida":
            self.estado, self.t, self.acertou = "investida", q["alcance"] / q["velocidade"], False
            return
        if p.tipo == "erupcoes":
            for k in range(q["quantidade"]):
                if k == 0:  # a primeira cai em cima de você
                    x, y = corpo.x, corpo.y
                else:
                    ang = self.rng.uniform(0, 2 * math.pi)
                    r = self.rng.uniform(q["raio"], q["espalhar"])
                    x, y = corpo.x + math.cos(ang) * r, corpo.y + math.sin(ang) * r
                x = min(max(x, 0.0), arena[0])
                y = min(max(y, 0.0), arena[1])
                atraso = q["atraso"] + 0.12 * k
                self.erupcoes.append(Erupcao(x, y, q["raio"], atraso, atraso, q["dano"]))
        elif p.tipo == "cortes":
            for k in range(q["quantidade"]):
                ang = self.rng.uniform(0, math.pi)
                ox = corpo.x + self.rng.uniform(-q["espalhar"], q["espalhar"])
                oy = corpo.y + self.rng.uniform(-q["espalhar"], q["espalhar"])
                if k == 0:  # o primeiro passa em cima de você
                    ox, oy = corpo.x, corpo.y
                meio = q["comprimento"] / 2
                atraso = q["atraso"] + k * q.get("intervalo", 0.1)
                self.cortes.append(
                    Corte(
                        ox - math.cos(ang) * meio,
                        oy - math.sin(ang) * meio,
                        ox + math.cos(ang) * meio,
                        oy + math.sin(ang) * meio,
                        q["largura"],
                        atraso,
                        atraso,
                        q["dano"],
                    )
                )
        elif p.tipo == "invocar":
            vivos = sum(1 for la in self.lacaios if la.vivo)
            for k in range(max(0, min(q["quantidade"], q["maximo"] - vivos))):
                ang = math.atan2(self.direcao[1], self.direcao[0]) + (k - 1) * 0.9
                d = al.raio + q["raio"] + 20
                self.lacaios.append(
                    Lacaio(
                        al.x + math.cos(ang) * d,
                        al.y + math.sin(ang) * d,
                        raio=q["raio"],
                        vida_max=q["vida"],
                        vida=q["vida"],
                        velocidade=q["velocidade"],
                        dano=q["dano"],
                    )
                )
                self.eventos.append(("invocar", al.x + math.cos(ang) * d, al.y + math.sin(ang) * d))
        elif p.tipo == "brasas":
            n, base = q["quantidade"], math.atan2(self.direcao[1], self.direcao[0])
            abertura = math.radians(q["espalhar"])
            for k in range(n):
                ang = base + (abertura * (k / (n - 1) - 0.5) if n > 1 else 0.0)
                self.brasas.append(
                    Brasa(
                        al.x + math.cos(ang) * al.raio,
                        al.y + math.sin(ang) * al.raio,
                        math.cos(ang) * q["velocidade"],
                        math.sin(ang) * q["velocidade"],
                        q["raio"],
                        q["dano"],
                        q["alcance"],
                    )
                )
        self.estado, self.t = "recupera", p.recuperacao

    def _perigos(self, dt: float, corpo: Corpo, arena) -> list[DanoChefe]:
        danos = []
        for b in self.brasas:
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.restante -= math.hypot(b.vx, b.vy) * dt
            if b.restante <= 0 or not (0 <= b.x <= arena[0] and 0 <= b.y <= arena[1]):
                b.viva = False
            elif math.hypot(corpo.x - b.x, corpo.y - b.y) <= corpo.raio + b.raio:
                b.viva = False
                danos.append(DanoChefe(b.dano, False, "brasa"))
        self.brasas = [b for b in self.brasas if b.viva]
        restantes = []
        for e in self.erupcoes:
            e.t -= dt
            if e.t > 0:
                restantes.append(e)
                continue
            self.eventos.append(("erupcao", e.x, e.y, e.raio))
            if math.hypot(corpo.x - e.x, corpo.y - e.y) <= e.raio + corpo.raio:
                danos.append(DanoChefe(e.dano, False, "erupcao"))
        self.erupcoes = restantes
        pendentes = []
        for c in self.cortes:
            c.t -= dt
            if c.t > 0:
                pendentes.append(c)
                continue
            self.eventos.append(("corte", c.x1, c.y1, c.x2, c.y2))
            if c.distancia(corpo.x, corpo.y) <= c.largura / 2 + corpo.raio:
                danos.append(DanoChefe(c.dano, False, "corte"))
        self.cortes = pendentes
        vivos = []
        for la in self.lacaios:
            if la.vivo and la.t_atordoado <= 0:
                dx, dy = corpo.x - la.x, corpo.y - la.y
                d = math.hypot(dx, dy) or 1.0
                la.x += dx / d * la.velocidade * dt
                la.y += dy / d * la.velocidade * dt
                if d <= la.raio + corpo.raio + 2:  # explode no contato
                    la.vida = 0.0
                    danos.append(DanoChefe(la.dano, False, "lacaio"))
                    self.eventos.append(("lacaio_explode", la.x, la.y))
                    continue
            la.passo(dt, arena)
            if la.vivo:
                vivos.append(la)
            else:
                self.eventos.append(("lacaio_morre", la.x, la.y))
        self.lacaios = vivos
        return danos

    def _dominio(self, dt: float) -> list[DanoChefe]:
        if not self.dominio_ativo:
            return []
        dm = self.dados.dominio
        if self.em_choque:
            return []
        danos = []
        self.t_dominio = max(0.0, self.t_dominio - dt)
        self.t_tique -= dt
        if self.t_tique <= 0:
            self.t_tique += dm.tique
            danos.append(DanoChefe(dm.dano_tique, True, "dominio"))
        if not self.dominio_ativo:  # acabou: a técnica queima
            self._queimar()
        return danos

    def quebrar_dominio(self) -> None:
        """Perdeu o choque: o domínio se desfaz e a técnica queima."""
        self.t_dominio, self.em_choque = 0.0, False
        self._queimar()

    def _queimar(self) -> None:
        self.estado, self.t = "queimado", self.dados.dominio.queimado
        self.brasas.clear()
        self.erupcoes.clear()
        self.cortes.clear()
        self.eventos.append(("fim_dominio", self.alvo.x, self.alvo.y))
