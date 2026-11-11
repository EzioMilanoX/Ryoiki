"""O combate corpo a corpo (v0, passo 2): golpe em combo, reforço, energia, Kokusen e hitstop.

Lógica pura, sem pygame. A cena chama `Golpeador.pedir` quando o botão é apertado (mesmo
durante o hitstop: o aperto conta), `Golpeador.atualizar` fora do hitstop, e recebe os
`Impacto`s para desenhar e congelar o quadro.

**Kokusen (o Clarão Negro):** depois de um golpe acertar, abre uma janela curtíssima. O
aperto que encadeia o próximo golpe precisa cair nela; quem aperta antes do impacto (quem
"esmaga" o botão) encadeia um golpe normal. O Kokusen multiplica o dano por 2,5, devolve
energia e põe o feiticeiro na **zona**, onde a janela fica mais larga por alguns segundos.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields
from pathlib import Path

from ryoiki.movimento import DADOS, Corpo

GOLPE, REFORCO = "golpe", "reforco"


@dataclass(frozen=True)
class FeelCombate:
    alcance: float = 64.0  # px além do raio do alvo
    angulo: float = 120.0  # graus de abertura do golpe
    antes: float = 0.05  # s até o golpe valer
    ativo: float = 0.07  # s em que ele acerta
    depois: float = 0.14  # s de recuperação
    combo_janela: float = 0.32  # s parado ainda encadeando o combo
    danos: tuple[float, ...] = (8.0, 8.0, 14.0)
    empurroes: tuple[float, ...] = (90.0, 90.0, 320.0)  # px/s no alvo
    avanco: float = 160.0  # px/s que o golpe leva o jogador para a frente
    lentidao: float = 0.35  # quanto o jogador anda enquanto golpeia (fração)
    kokusen_janela: float = 0.06
    kokusen_janela_zona: float = 0.12
    kokusen_mult: float = 2.5
    zona_duracao: float = 5.0
    hitstop: float = 0.045
    hitstop_final: float = 0.085
    hitstop_kokusen: float = 0.22
    energia_max: float = 100.0
    energia_regen: float = 5.0  # por segundo
    energia_por_golpe: float = 4.0
    energia_kokusen: float = 30.0
    reforco_custo: float = 25.0
    reforco_mult: float = 2.0
    reforco_antes: float = 0.12
    reforco_empurrao: float = 420.0

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> FeelCombate:
        dados = json.loads((caminho or DADOS / "feel.json").read_text(encoding="utf-8"))
        bruto = dados.get("combate", {})
        nomes = {f.name for f in fields(cls)}
        valores = {k: v for k, v in bruto.items() if k in nomes}
        for k in ("danos", "empurroes"):
            if k in valores:
                valores[k] = tuple(float(x) for x in valores[k])
        return cls(**valores)


@dataclass
class Alvo:
    """Algo que apanha: por enquanto, a maldição de treino."""

    x: float
    y: float
    raio: float = 24.0
    vida_max: float = 220.0
    vida: float = 220.0
    vx: float = 0.0
    vy: float = 0.0
    t_ferido: float = 0.0  # o clarão branco de quando apanha
    t_marca: float = 0.0  # > 0: marcado por uma técnica (ex.: o prego da Ressonância)
    t_atordoado: float = 0.0  # > 0: não ataca
    massa: float = 1.0  # o empurrão divide por ela (o chefe é pesado)

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    @property
    def marcado(self) -> bool:
        return self.t_marca > 0

    def receber(self, dano: float, dx: float, dy: float, forca: float) -> None:
        self.vida = max(0.0, self.vida - dano)
        self.vx += dx * forca / self.massa
        self.vy += dy * forca / self.massa
        self.t_ferido = 0.12

    def passo(self, dt: float, arena: tuple[float, float], atrito: float = 1400.0) -> None:
        self.t_ferido = max(0.0, self.t_ferido - dt)
        self.t_marca = max(0.0, self.t_marca - dt)
        self.t_atordoado = max(0.0, self.t_atordoado - dt)
        v = math.hypot(self.vx, self.vy)
        if v > 0:
            k = max(0.0, v - atrito * dt) / v
            self.vx *= k
            self.vy *= k
        self.x = min(max(self.x + self.vx * dt, self.raio), arena[0] - self.raio)
        self.y = min(max(self.y + self.vy * dt, self.raio), arena[1] - self.raio)


@dataclass(frozen=True)
class Impacto:
    x: float
    y: float
    dano: float
    dx: float  # a direção do golpe (para as faíscas)
    dy: float
    kokusen: bool
    final: bool  # o 3º do combo ou um reforço
    hitstop: float


@dataclass
class Ataque:
    tipo: str
    passo: int  # 0, 1, 2 no combo
    kokusen: bool
    fase: str = "antes"  # antes -> ativo -> depois
    t: float = 0.0
    atingidos: set[int] = field(default_factory=set)

    @property
    def final(self) -> bool:
        return self.tipo == REFORCO or self.passo == 2


@dataclass
class Golpeador:
    feel: FeelCombate
    energia: float = 0.0
    ataque: Ataque | None = None
    passo: int = 0  # o próximo golpe do combo
    t_combo: float = 0.0  # > 0: parado, mas o combo ainda encadeia
    t_kokusen: float = 0.0  # > 0: a janela do Kokusen está aberta
    t_zona: float = 0.0
    fila: str = ""  # o próximo golpe já pedido
    fila_kokusen: bool = False
    combo: int = 0  # acertos seguidos (o contador da tela)
    kokusens: int = 0

    def __post_init__(self) -> None:
        if not self.energia:
            self.energia = self.feel.energia_max * 0.5

    @property
    def atacando(self) -> bool:
        return self.ataque is not None

    @property
    def na_zona(self) -> bool:
        return self.t_zona > 0

    def pedir(self, tipo: str = GOLPE) -> bool:
        """O botão foi apertado. False se não deu (reforço sem energia, ou já há um na fila)."""
        if tipo == REFORCO and self.energia < self.feel.reforco_custo:
            return False
        kokusen = self.t_kokusen > 0
        if self.ataque is None:
            self._comecar(tipo, kokusen)
            return True
        if self.fila:
            return False
        self.fila, self.fila_kokusen = tipo, kokusen
        return True

    def _comecar(self, tipo: str, kokusen: bool) -> None:
        if tipo == REFORCO:
            self.energia -= self.feel.reforco_custo
            passo = 2
        else:
            passo = self.passo  # volta a 0 quando o combo esfria ou fecha
        self.ataque = Ataque(tipo, passo, kokusen)
        self.passo = (passo + 1) % 3
        self.t_kokusen = 0.0

    def atualizar(self, dt: float, corpo: Corpo, alvos: list[Alvo]) -> list[Impacto]:
        f = self.feel
        self.energia = min(f.energia_max, self.energia + f.energia_regen * dt)
        self.t_kokusen = max(0.0, self.t_kokusen - dt)
        self.t_zona = max(0.0, self.t_zona - dt)
        a = self.ataque
        if a is None:
            if self.t_combo > 0:
                self.t_combo = max(0.0, self.t_combo - dt)
                if self.t_combo == 0:
                    self.passo, self.combo = 0, 0
            return []
        a.t += dt
        impactos: list[Impacto] = []
        antes = f.reforco_antes if a.tipo == REFORCO else f.antes
        if a.fase == "antes" and a.t >= antes:
            a.fase, a.t = "ativo", 0.0
        if a.fase == "ativo":
            corpo.x += corpo.mira[0] * f.avanco * dt
            corpo.y += corpo.mira[1] * f.avanco * dt
            impactos = self._acertar(a, corpo, alvos)
            if a.t >= f.ativo:
                a.fase, a.t = "depois", 0.0
        elif a.fase == "depois" and a.t >= f.depois:
            self.ataque = None
            if self.fila:
                tipo, k = self.fila, self.fila_kokusen
                self.fila, self.fila_kokusen = "", False
                if tipo == REFORCO and self.energia < f.reforco_custo:
                    tipo = GOLPE
                self._comecar(tipo, k)
            else:
                self.t_combo = f.combo_janela
                if a.final:
                    self.passo = 0
        return impactos

    def no_alcance(self, corpo: Corpo, alvo: Alvo) -> bool:
        dx, dy = alvo.x - corpo.x, alvo.y - corpo.y
        d = math.hypot(dx, dy)
        if d > self.feel.alcance + alvo.raio + corpo.raio:
            return False
        if d <= alvo.raio + corpo.raio:  # colado: acerta de qualquer lado
            return True
        cos = (dx * corpo.mira[0] + dy * corpo.mira[1]) / d
        return cos >= math.cos(math.radians(self.feel.angulo / 2))

    def _acertar(self, a: Ataque, corpo: Corpo, alvos: list[Alvo]) -> list[Impacto]:
        f = self.feel
        impactos = []
        for alvo in alvos:
            if id(alvo) in a.atingidos or not alvo.vivo or not self.no_alcance(corpo, alvo):
                continue
            a.atingidos.add(id(alvo))
            dano = f.danos[a.passo % len(f.danos)]
            forca = f.empurroes[a.passo % len(f.empurroes)]
            if a.tipo == REFORCO:
                dano *= f.reforco_mult
                forca = f.reforco_empurrao
            if a.kokusen:
                dano *= f.kokusen_mult
                forca *= 1.5
            dx, dy = alvo.x - corpo.x, alvo.y - corpo.y
            n = math.hypot(dx, dy) or 1.0
            dx, dy = dx / n, dy / n
            alvo.receber(dano, dx, dy, forca)
            self.combo += 1
            self.energia = min(f.energia_max, self.energia + f.energia_por_golpe)
            if a.kokusen:
                self.kokusens += 1
                self.energia = min(f.energia_max, self.energia + f.energia_kokusen)
                self.t_zona = f.zona_duracao
                hitstop = f.hitstop_kokusen
            else:
                hitstop = f.hitstop_final if a.final else f.hitstop
            self.t_kokusen = f.kokusen_janela_zona if self.na_zona else f.kokusen_janela
            px = alvo.x - dx * alvo.raio
            py = alvo.y - dy * alvo.raio
            impactos.append(Impacto(px, py, dano, dx, dy, a.kokusen, a.final, hitstop))
        return impactos
