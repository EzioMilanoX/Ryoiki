"""A cara do Ryoiki: chão de concreto rachado, selos, véu, o feiticeiro visto de cima,
a maldição e os efeitos (faíscas de tinta, o Clarão Negro, números).

Tudo com as primitivas de UI do renderer, em coordenadas de tela. Nada de círculo em
grade: o chão é uma rua à noite dentro de uma cortina, e as figuras têm corpo.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

FONTE_PINCEL = 1  # a Yuji Syuku (game.py a carrega)

NOITE = (10, 9, 13, 255)
CONCRETO = (24, 22, 28, 255)
JUNTA = (16, 15, 19, 255)
RACHADURA = (7, 6, 9, 255)
SELO = (150, 40, 50, 255)
VEU = (40, 16, 58, 255)
UNIFORME = (24, 28, 42, 255)
UNIFORME_BORDA = (52, 60, 86, 255)
PELE = (226, 196, 170, 255)
CABELO = (34, 30, 40, 255)
CONTORNO = (150, 160, 190, 255)  # a luz de recorte: separa a figura do chão
CAMISA = (230, 230, 236, 255)
ENERGIA = (90, 160, 255, 255)
MALDICAO = (78, 58, 92, 255)
MALDICAO_BORDA = (130, 96, 150, 255)
OLHO = (235, 200, 70, 255)
SANGUE = (200, 30, 40, 255)
TINTA = (210, 204, 222, 255)
PRETO = (0, 0, 0, 255)

LADO_PLACA = 160  # as placas de concreto


def a(cor, alfa: float) -> tuple[int, int, int, int]:
    return (cor[0], cor[1], cor[2], max(0, min(255, round(alfa))))


def elipse(cx, cy, rx, ry, ang=0.0, n=18) -> list[tuple[float, float]]:
    c, s = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


# ------------------------------------------------------------------------ o chão


@dataclass(frozen=True)
class Cenario:
    """As marcas fixas do chão, sorteadas uma vez (seed): rachaduras, manchas e selos."""

    rachaduras: tuple[tuple[tuple[float, float], ...], ...]
    manchas: tuple[tuple[float, float, float], ...]
    selos: tuple[tuple[float, float, float], ...]

    @classmethod
    def novo(cls, arena: tuple[float, float], seed: int = 7) -> Cenario:
        rng = random.Random(seed)
        w, h = arena
        rach = []
        for _ in range(22):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            ang = rng.uniform(0, 2 * math.pi)
            pts = [(x, y)]
            for _ in range(rng.randint(3, 7)):
                ang += rng.uniform(-0.8, 0.8)
                passo = rng.uniform(14, 40)
                x, y = x + math.cos(ang) * passo, y + math.sin(ang) * passo
                pts.append((x, y))
            rach.append(tuple(pts))
        manchas = []
        for _ in range(14):  # respingos de tinta: um borrão e gotas em volta
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            manchas.append((cx, cy, rng.uniform(10, 26)))
            for _ in range(rng.randint(3, 7)):
                d, t = rng.uniform(14, 46), rng.uniform(0, 2 * math.pi)
                manchas.append((cx + math.cos(t) * d, cy + math.sin(t) * d, rng.uniform(2, 6)))
        selos = tuple(
            (rng.uniform(200, w - 200), rng.uniform(200, h - 200), rng.uniform(70, 120))
            for _ in range(3)
        )
        return cls(tuple(rach), tuple(manchas), selos)


def desenhar_chao(r, cam, arena, cenario: Cenario, relogio: float, tela) -> None:
    lw, lh = tela
    w, h = arena
    r.draw_ui_rect(0, 0, lw, lh, NOITE)
    x0, y0 = cam.tela_de(0, 0)
    x1, y1 = cam.tela_de(w, h)
    r.draw_ui_rect(
        max(0, x0), max(0, y0), min(lw, x1) - max(0, x0), min(lh, y1) - max(0, y0), CONCRETO
    )
    k = 1
    while k * LADO_PLACA < w:  # as juntas das placas
        x = x0 + k * LADO_PLACA
        if 0 <= x <= lw:
            r.draw_ui_line(x, max(0, y0), x, min(lh, y1), JUNTA, 2)
        k += 1
    k = 1
    while k * LADO_PLACA < h:
        y = y0 + k * LADO_PLACA
        if 0 <= y <= lh:
            r.draw_ui_line(max(0, x0), y, min(lw, x1), y, JUNTA, 2)
        k += 1
    for cx, cy, raio in cenario.selos:  # selos de contenção, quase apagados
        sx, sy = cam.tela_de(cx, cy)
        if -raio < sx < lw + raio and -raio < sy < lh + raio:
            r.draw_ui_circle(sx, sy, raio, a(SELO, 34), 2)
            r.draw_ui_circle(sx, sy, raio * 0.78, a(SELO, 24), 1)
            for i in range(8):
                t = i * math.pi / 4 + relogio * 0.05
                r.draw_ui_line(
                    sx + math.cos(t) * raio * 0.78,
                    sy + math.sin(t) * raio * 0.78,
                    sx + math.cos(t) * raio,
                    sy + math.sin(t) * raio,
                    a(SELO, 30),
                    1,
                )
            r.draw_text(
                sx, sy, "封", int(raio * 0.8), a(SELO, 30), anchor="center", font_id=FONTE_PINCEL
            )
    for pts in cenario.rachaduras:
        tela_pts = [cam.tela_de(x, y) for x, y in pts]
        if any(0 <= x <= lw and 0 <= y <= lh for x, y in tela_pts):
            for p, q in zip(tela_pts, tela_pts[1:], strict=False):
                r.draw_ui_line(p[0], p[1], q[0], q[1], RACHADURA, 2)
    for cx, cy, raio in cenario.manchas:
        sx, sy = cam.tela_de(cx, cy)
        if -30 < sx < lw + 30 and -30 < sy < lh + 30:
            r.draw_ui_circle(sx, sy, raio, a(RACHADURA, 150))
    _veu(r, x0, y0, x1, y1, relogio, tela)


def _veu(r, x0, y0, x1, y1, relogio, tela) -> None:
    """A cortina que fecha a arena: uma faixa escura com fios que tremem."""
    lw, lh = tela
    for i, alfa in enumerate((90, 60, 34, 16)):
        e = 6 * (i + 1)
        r.draw_ui_polygon(
            [(x0 - e, y0 - e), (x1 + e, y0 - e), (x1 + e, y1 + e), (x0 - e, y1 + e)],
            a(VEU, alfa),
            6,
        )
    passo = 26
    for borda in range(4):
        n = int(((x1 - x0) if borda < 2 else (y1 - y0)) / passo)
        for k in range(n + 1):
            onda = math.sin(relogio * 2.3 + k * 0.9 + borda) * 6
            if borda == 0:
                p, q = (x0 + k * passo, y0 - 4), (x0 + k * passo + onda, y0 - 22)
            elif borda == 1:
                p, q = (x0 + k * passo, y1 + 4), (x0 + k * passo + onda, y1 + 22)
            elif borda == 2:
                p, q = (x0 - 4, y0 + k * passo), (x0 - 22, y0 + k * passo + onda)
            else:
                p, q = (x1 + 4, y0 + k * passo), (x1 + 22, y0 + k * passo + onda)
            if -30 <= p[0] <= lw + 30 and -30 <= p[1] <= lh + 30:
                r.draw_ui_line(p[0], p[1], q[0], q[1], a(VEU, 120), 2)


def vinheta(r, tela, forca: float = 1.0) -> None:
    lw, lh = tela
    for i in range(6):
        e = 14 + i * 14
        alfa = (70 - i * 11) * forca
        r.draw_ui_rect(0, 0, lw, e, a(PRETO, alfa))
        r.draw_ui_rect(0, lh - e, lw, e, a(PRETO, alfa))
        r.draw_ui_rect(0, 0, e, lh, a(PRETO, alfa))
        r.draw_ui_rect(lw - e, 0, e, lh, a(PRETO, alfa))


def poeira(r, cam, arena, relogio, tela) -> None:
    """Fagulhas de energia amaldiçoada subindo devagar pelo ar."""
    lw, lh = tela
    for i in range(40):
        rng = random.Random(i * 97)
        x = rng.uniform(0, arena[0])
        ciclo = rng.uniform(6, 12)
        fase = ((relogio + rng.uniform(0, ciclo)) % ciclo) / ciclo
        y = arena[1] * (1 - fase)
        x += math.sin(relogio * 0.7 + i) * 18
        sx, sy = cam.tela_de(x, y)
        if 0 <= sx <= lw and 0 <= sy <= lh:
            r.draw_ui_circle(sx, sy, 1.6, a(MALDICAO_BORDA, 90 * math.sin(math.pi * fase)))


# ------------------------------------------------------------------- as figuras


def feiticeiro(
    r, sx, sy, raio, mira, relogio, *, punho=None, aura=0.0, zona=False, invencivel=False
) -> None:
    """Visto de cima: sombra, ombros do uniforme, braços, cabeça e cabelo, e a aura.

    `punho`: None, ou (lado, extensao 0..1): o braço que golpeia estica para a mira.
    """
    raio *= 1.35  # a figura é maior que a caixa de colisão: lê melhor na tela
    ang = math.atan2(mira[1], mira[0])
    px, py = -mira[1], mira[0]  # a perpendicular (os ombros)
    r.draw_ui_polygon(elipse(sx + 4, sy + 7, raio * 1.15, raio * 0.85, ang), a(PRETO, 130))
    if aura > 0 or zona:  # a energia em volta do corpo
        cor = SANGUE if zona else ENERGIA
        for i in range(3):
            tremor = math.sin(relogio * 17 + i * 2.1) * 2.5
            alfa = (60 + 50 * aura) / (i + 1)
            rx, ry = raio * (1.3 + 0.16 * i) + tremor, raio * (1.1 + 0.16 * i) + tremor
            r.draw_ui_polygon(elipse(sx, sy, ry, rx, ang), a(cor, alfa), 2)
    for lado in (-1, 1):  # os braços: manga escura com contorno claro e o punho
        ext = 0.0
        if punho is not None and punho[0] in (lado, 0):
            ext = punho[1]
        bx = sx + px * lado * raio * 0.8 + mira[0] * (raio * 0.3 + ext * raio * 1.5)
        by = sy + py * lado * raio * 0.8 + mira[1] * (raio * 0.3 + ext * raio * 1.5)
        ox, oy = sx + px * lado * raio * 0.62, sy + py * lado * raio * 0.62
        largura = int(raio * 0.42)
        r.draw_ui_line(ox, oy, bx, by, CONTORNO, largura + 4)
        r.draw_ui_line(ox, oy, bx, by, UNIFORME, largura)
        r.draw_ui_circle(bx, by, raio * 0.24, CONTORNO)
        r.draw_ui_circle(bx, by, raio * 0.2, PELE)
        if ext > 0.6:
            r.draw_ui_circle(bx, by, raio * 0.4, a(SANGUE if zona else ENERGIA, 170), 2)
    corpo = UNIFORME_BORDA if invencivel else UNIFORME
    ombros = elipse(sx, sy, raio * 0.5, raio * 0.95, ang)
    r.draw_ui_polygon(ombros, corpo)
    r.draw_ui_polygon(ombros, CONTORNO, 2)
    # a gola branca da camisa, na frente
    r.draw_ui_arc(
        sx + mira[0] * raio * 0.1,
        sy + mira[1] * raio * 0.1,
        raio * 0.42,
        ang - 1.0,
        ang + 1.0,
        CAMISA,
        3,
    )
    # a cabeça: cabelo espetado visto de cima, com o rosto aparecendo na frente
    hx, hy = sx + mira[0] * raio * 0.08, sy + mira[1] * raio * 0.08
    r.draw_ui_circle(hx + mira[0] * raio * 0.12, hy + mira[1] * raio * 0.12, raio * 0.36, PELE)
    espetos = []
    for i in range(14):
        t = ang + math.pi * 0.35 + (2 * math.pi - math.pi * 0.7) * i / 13
        rr = raio * (0.46 if i % 2 else 0.34)
        espetos.append(
            (
                hx - mira[0] * raio * 0.05 + math.cos(t) * rr,
                hy - mira[1] * raio * 0.05 + math.sin(t) * rr,
            )
        )
    espetos.append((hx + mira[0] * raio * 0.1, hy + mira[1] * raio * 0.1))
    r.draw_ui_polygon(espetos, CABELO)
    r.draw_ui_polygon(espetos, CONTORNO, 1)


def maldicao(r, sx, sy, raio, relogio, olhar, *, ferido=False, vida=1.0) -> None:
    """Uma maldição de treino: massa disforme que pulsa, com um olho só e uma boca torta."""
    pts = []
    for i in range(22):
        t = 2 * math.pi * i / 22
        rr = raio * (
            1 + 0.12 * math.sin(t * 3 + relogio * 3.1) + 0.07 * math.sin(t * 7 - relogio * 5)
        )
        pts.append((sx + math.cos(t) * rr, sy + math.sin(t) * rr * 0.9))
    r.draw_ui_polygon(elipse(sx + 5, sy + 8, raio * 1.1, raio * 0.75), a(PRETO, 110))
    r.draw_ui_polygon(pts, TINTA if ferido else MALDICAO)
    r.draw_ui_polygon(pts, MALDICAO_BORDA, 2)
    for i in range(4):  # os braços curtos que se mexem
        t = i * math.pi / 2 + 0.5 + math.sin(relogio * 2 + i) * 0.3
        r.draw_ui_line(
            sx + math.cos(t) * raio * 0.9,
            sy + math.sin(t) * raio * 0.9,
            sx + math.cos(t) * raio * 1.45,
            sy + math.sin(t) * raio * 1.45,
            MALDICAO_BORDA,
            4,
        )
    ex, ey = sx + olhar[0] * raio * 0.15, sy - raio * 0.2 + olhar[1] * raio * 0.15
    r.draw_ui_circle(ex, ey, raio * 0.36, (235, 228, 210, 255))
    r.draw_ui_circle(ex + olhar[0] * raio * 0.14, ey + olhar[1] * raio * 0.14, raio * 0.17, OLHO)
    r.draw_ui_circle(ex + olhar[0] * raio * 0.17, ey + olhar[1] * raio * 0.17, raio * 0.07, PRETO)
    boca = [
        (sx - raio * 0.45 + k * raio * 0.15, sy + raio * 0.38 + (k % 2) * raio * 0.12)
        for k in range(7)
    ]
    for p, q in zip(boca, boca[1:], strict=False):
        r.draw_ui_line(p[0], p[1], q[0], q[1], PRETO, 2)
    largura = raio * 2
    r.draw_ui_rect(sx - raio, sy - raio * 1.55, largura, 4, a(PRETO, 160))
    r.draw_ui_rect(sx - raio, sy - raio * 1.55, largura * vida, 4, SANGUE)


# ------------------------------------------------------------------- os efeitos


@dataclass
class Efeito:
    tipo: str  # faisca | raio | numero | onda
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    vida: float = 0.3
    t: float = 0.0
    texto: str = ""
    pts: tuple = ()
    cor: tuple = TINTA
    raio: float = 70.0

    @property
    def acabou(self) -> bool:
        return self.t >= self.vida


def efeitos_do_impacto(imp, rng: random.Random) -> list[Efeito]:
    out = []
    ang = math.atan2(imp.dy, imp.dx)
    n = 14 if imp.kokusen else (9 if imp.final else 6)
    for _ in range(n):  # faíscas em leque, para a frente do golpe
        t = ang + rng.uniform(-0.9, 0.9)
        v = rng.uniform(260, 620) * (1.4 if imp.kokusen else 1)
        out.append(
            Efeito(
                "faisca", imp.x, imp.y, math.cos(t) * v, math.sin(t) * v, rng.uniform(0.12, 0.24)
            )
        )
    out.append(Efeito("onda", imp.x, imp.y, vida=0.22 if not imp.kokusen else 0.4))
    if imp.kokusen:
        for _ in range(7):  # o raio negro: linhas quebradas que saem do ponto
            t = rng.uniform(0, 2 * math.pi)
            x, y, pts = imp.x, imp.y, [(imp.x, imp.y)]
            for _ in range(rng.randint(4, 7)):
                t += rng.uniform(-0.7, 0.7)
                passo = rng.uniform(16, 34)
                x, y = x + math.cos(t) * passo, y + math.sin(t) * passo
                pts.append((x, y))
            out.append(Efeito("raio", imp.x, imp.y, vida=0.35, pts=tuple(pts)))
    out.append(
        Efeito(
            "numero",
            imp.x,
            imp.y - 20,
            rng.uniform(-30, 30),
            -90,
            0.8 if imp.kokusen else 0.55,
            texto=f"{imp.dano:.0f}",
        )
    )
    return out


def desenhar_efeito(r, cam, e: Efeito) -> None:
    k = e.t / e.vida
    sx, sy = cam.tela_de(e.x, e.y)
    if e.tipo == "faisca":
        cauda = 0.03
        r.draw_ui_line(sx, sy, sx - e.vx * cauda, sy - e.vy * cauda, a(e.cor, 255 * (1 - k)), 2)
    elif e.tipo == "onda":
        r.draw_ui_circle(sx, sy, 10 + e.raio * k, a(e.cor, 160 * (1 - k)), 2)
    elif e.tipo == "linha":  # o rastro de um corte, sumindo
        p1, p2 = cam.tela_de(*e.pts[0]), cam.tela_de(*e.pts[1])
        r.draw_ui_line(
            p1[0], p1[1], p2[0], p2[1], a(e.cor, 230 * (1 - k)), max(1, int(6 * (1 - k)))
        )
        r.draw_ui_line(p1[0], p1[1], p2[0], p2[1], a(TINTA, 255 * (1 - k)), 1)
    elif e.tipo == "raio":
        pts = [cam.tela_de(x, y) for x, y in e.pts]
        for p, q in zip(pts, pts[1:], strict=False):
            r.draw_ui_line(p[0], p[1], q[0], q[1], a(SANGUE, 230 * (1 - k)), 7)
            r.draw_ui_line(p[0], p[1], q[0], q[1], a(PRETO, 255 * (1 - k)), 3)
    elif e.tipo == "numero":
        grande = len(e.texto) and e.vida > 0.6
        r.draw_text(
            sx,
            sy,
            e.texto,
            30 if grande else 20,
            a(SANGUE if grande else e.cor, 255 * (1 - k * k)),
            anchor="center",
            font_id=FONTE_PINCEL,
        )


def mover_efeito(e: Efeito, dt: float) -> None:
    e.t += dt
    e.x += e.vx * dt
    e.y += e.vy * dt
    if e.tipo == "faisca":
        e.vx *= 0.86
        e.vy *= 0.86


# ------------------------------------------------------- a técnica e a defesa (passo 3)

CURA = (150, 255, 200, 255)  # a Técnica Reversa: energia positiva, clara


def efeitos_da_tecnica(ac, cor, rng: random.Random) -> list[Efeito]:
    """Um acerto da técnica (`tecnica.Acerto`): faíscas na cor dela, ou a onda da explosão."""
    if ac.forma == "explosao":
        return [
            Efeito("onda", ac.x, ac.y, vida=0.35, cor=cor, raio=ac.raio),
            Efeito("onda", ac.x, ac.y, vida=0.5, cor=cor, raio=ac.raio * 0.6),
        ]
    out = []
    for _ in range(10 if ac.forma == "marcados" else 5):
        t = rng.uniform(0, 2 * math.pi)
        v = rng.uniform(180, 460)
        out.append(Efeito("faisca", ac.x, ac.y, math.cos(t) * v, math.sin(t) * v, 0.22, cor=cor))
    if ac.forma == "marcados":  # a Ressonância: o prego vibra e estoura
        out.append(Efeito("onda", ac.x, ac.y, vida=0.4, cor=cor, raio=90))
    if ac.dano:
        out.append(
            Efeito(
                "numero",
                ac.x,
                ac.y - 22,
                rng.uniform(-25, 25),
                -90,
                0.55,
                texto=f"{ac.dano:.0f}",
                cor=cor,
            )
        )
    return out


def projetil(r, cam, p, cor) -> None:
    sx, sy = cam.tela_de(p.x, p.y)
    for k in (3, 2, 1):  # o rastro: círculos que somem para trás
        d = k * p.raio * 1.1
        r.draw_ui_circle(sx - p.dx * d, sy - p.dy * d, p.raio * (1 - k * 0.2), a(cor, 50 * (4 - k)))
    r.draw_ui_circle(sx, sy, p.raio + 3, a(cor, 200))
    r.draw_ui_circle(sx, sy, p.raio * 0.6, TINTA)


def area_pendente(r, cam, ar, cor, relogio) -> None:
    """O aviso da área: um anel que fecha até a hora de explodir."""
    if ar.raio < 0:
        return
    sx, sy = cam.tela_de(ar.x, ar.y)
    k = 1 - ar.t / ar.atraso if ar.atraso > 0 else 1.0
    r.draw_ui_circle(sx, sy, ar.raio, a(cor, 40 + 60 * k))
    r.draw_ui_circle(sx, sy, ar.raio, a(cor, 200), 2)
    r.draw_ui_circle(sx, sy, ar.raio * (1 - k) + 6, a(cor, 220), 3)
    for i in range(6):  # a espiral sendo sugada para o centro
        t = relogio * 9 + i * math.pi / 3
        rr = ar.raio * (1 - k) * 0.9 + 8
        r.draw_ui_circle(sx + math.cos(t) * rr, sy + math.sin(t) * rr, 3, a(TINTA, 200))


def marca(r, sx, sy, raio, relogio, cor) -> None:
    """O prego cravado: um losango que pisca sobre o alvo marcado."""
    y = sy - raio * 1.9 + math.sin(relogio * 6) * 2
    pts = [(sx, y - 7), (sx + 5, y), (sx, y + 7), (sx - 5, y)]
    r.draw_ui_polygon(pts, a(cor, 230))
    r.draw_ui_circle(sx, sy, raio * 1.25, a(cor, 90 + 60 * math.sin(relogio * 8)), 1)


def atordoado(r, sx, sy, raio, relogio) -> None:
    for i in range(3):
        t = relogio * 5 + i * 2.1
        r.draw_ui_circle(
            sx + math.cos(t) * raio * 0.9, sy - raio * 1.2 + math.sin(t) * 4, 3, a(OLHO, 220)
        )


def aviso_pancada(r, sx, sy, raio, carga) -> None:
    """A pancada da maldição sendo carregada: o círculo vermelho enche até estourar."""
    r.draw_ui_circle(sx, sy, raio, a(SANGUE, 30 + 50 * carga))
    r.draw_ui_circle(sx, sy, raio, a(SANGUE, 200), 2)
    r.draw_ui_circle(sx, sy, raio * carga, a(SANGUE, 90))


def escudo(r, sx, sy, raio, relogio, bloqueou: bool) -> None:
    """O reforço: o corpo coberto de energia (acende quando segura um golpe)."""
    rr = raio * 1.35 * 1.25
    alfa = 220 if bloqueou else 120
    pts = []
    for i in range(6):
        t = i * math.pi / 3 + relogio * 0.8
        pts.append((sx + math.cos(t) * rr, sy + math.sin(t) * rr))
    r.draw_ui_polygon(pts, a(ENERGIA, 35 if not bloqueou else 90))
    r.draw_ui_polygon(pts, a(ENERGIA, alfa), 2)


def reversa(r, sx, sy, raio, relogio) -> None:
    """A Técnica Reversa: energia clara subindo do corpo."""
    for i in range(5):
        k = (relogio * 1.6 + i / 5) % 1
        x = sx + math.sin(i * 2.4 + relogio * 3) * raio * 0.9
        r.draw_ui_circle(x, sy + raio - k * raio * 3, 3 + 2 * (1 - k), a(CURA, 220 * (1 - k)))
    r.draw_ui_circle(sx, sy, raio * 1.6 + math.sin(relogio * 10) * 2, a(CURA, 110), 2)


# --------------------------------------------------------------- o chefe (passo 4)

ROCHA = (58, 50, 50, 255)
ROCHA_BORDA = (110, 92, 86, 255)
LAVA = (255, 120, 30, 255)
LAVA_CLARA = (255, 210, 120, 255)


def chefe_vulcao(r, sx, sy, raio, relogio, olhar, *, ferido=False, queimado=False) -> None:
    """Visto de cima: um corpo de rocha com uma cratera de lava no alto da cabeça e um olho."""
    r.draw_ui_polygon(elipse(sx + 7, sy + 10, raio * 1.25, raio * 0.9), a(PRETO, 140))
    ang = math.atan2(olhar[1], olhar[0])
    px, py = -olhar[1], olhar[0]
    for lado in (-1, 1):  # os braços grossos
        bx = sx + px * lado * raio * 1.0 + olhar[0] * raio * 0.5
        by = sy + py * lado * raio * 1.0 + olhar[1] * raio * 0.5
        r.draw_ui_line(
            sx + px * lado * raio * 0.7,
            sy + py * lado * raio * 0.7,
            bx,
            by,
            ROCHA_BORDA,
            int(raio * 0.5) + 4,
        )
        r.draw_ui_line(
            sx + px * lado * raio * 0.7, sy + py * lado * raio * 0.7, bx, by, ROCHA, int(raio * 0.5)
        )
        r.draw_ui_circle(bx, by, raio * 0.3, ROCHA_BORDA)
    pts = []
    for i in range(16):  # o corpo: um bloco de rocha irregular
        t = 2 * math.pi * i / 16
        rr = raio * (1 + 0.08 * math.sin(t * 5 + 1.3))
        pts.append((sx + math.cos(t) * rr, sy + math.sin(t) * rr))
    r.draw_ui_polygon(pts, TINTA if ferido else ROCHA)
    r.draw_ui_polygon(pts, ROCHA_BORDA, 3)
    # a cratera: um cone visto de cima, com a lava pulsando lá dentro
    cx, cy = sx - olhar[0] * raio * 0.15, sy - olhar[1] * raio * 0.15
    pulso = 0.5 + 0.5 * math.sin(relogio * 6)
    r.draw_ui_circle(cx, cy, raio * 0.62, ROCHA_BORDA)
    r.draw_ui_circle(cx, cy, raio * 0.48, (40, 20, 18, 255))
    lava = (90, 90, 90, 255) if queimado else LAVA
    r.draw_ui_circle(cx, cy, raio * (0.3 + 0.06 * pulso), lava)
    if not queimado:
        r.draw_ui_circle(cx, cy, raio * 0.14, LAVA_CLARA)
    for i in range(3):  # a fumaça subindo
        k = (relogio * 0.7 + i / 3) % 1
        r.draw_ui_circle(
            cx + math.sin(relogio + i * 2) * 8,
            cy - k * raio * 1.6,
            raio * (0.15 + 0.25 * k),
            a((70, 64, 66, 255), 150 * (1 - k)),
        )
    # o olho, na frente
    ex, ey = sx + olhar[0] * raio * 0.62, sy + olhar[1] * raio * 0.62
    r.draw_ui_polygon(elipse(ex, ey, raio * 0.2, raio * 0.3, ang), (235, 228, 210, 255))
    r.draw_ui_circle(ex + olhar[0] * 3, ey + olhar[1] * 3, raio * 0.12, PRETO)


def aviso_investida(r, cam, x, y, direcao, alcance, largura, k, cor=LAVA) -> None:
    """A faixa no chão por onde o chefe vai passar."""
    dx, dy = direcao
    px, py = -dy * largura, dx * largura
    fx, fy = x + dx * alcance, y + dy * alcance
    pts = [
        cam.tela_de(x + px, y + py),
        cam.tela_de(fx + px, fy + py),
        cam.tela_de(fx - px, fy - py),
        cam.tela_de(x - px, y - py),
    ]
    r.draw_ui_polygon(pts, a(cor, 25 + 60 * k))
    r.draw_ui_polygon(pts, a(cor, 200), 2)
    mx, my = x + dx * alcance * k, y + dy * alcance * k
    m1, m2 = cam.tela_de(mx + px, my + py), cam.tela_de(mx - px, my - py)
    r.draw_ui_line(m1[0], m1[1], m2[0], m2[1], a(LAVA_CLARA, 230), 3)


def aviso_erupcao(r, cam, e, cor=LAVA) -> None:
    sx, sy = cam.tela_de(e.x, e.y)
    k = 1 - e.t / e.atraso if e.atraso > 0 else 1.0
    r.draw_ui_circle(sx, sy, e.raio, a(cor, 30 + 60 * k))
    r.draw_ui_circle(sx, sy, e.raio, a(cor, 210), 2)
    r.draw_ui_circle(sx, sy, e.raio * k, a(cor, 110))


def brasa(r, cam, b, relogio, cor=LAVA) -> None:
    sx, sy = cam.tela_de(b.x, b.y)
    v = math.hypot(b.vx, b.vy) or 1
    for k in (3, 2, 1):
        d = k * b.raio * 0.9
        r.draw_ui_circle(
            sx - b.vx / v * d, sy - b.vy / v * d, b.raio * (1 - k * 0.22), a(cor, 60 * (4 - k))
        )
    r.draw_ui_circle(sx, sy, b.raio, cor)
    r.draw_ui_circle(sx, sy, b.raio * (0.45 + 0.15 * math.sin(relogio * 30)), LAVA_CLARA)


def entoando(r, sx, sy, raio, k, dano_frac, cor=LAVA) -> None:
    """A entoação do domínio: anéis fechando no chefe e a barra do que falta para cortar."""
    for i in range(3):
        rr = raio * (1.4 + (1 - k) * (2.5 + i))
        r.draw_ui_circle(sx, sy, rr, a(cor, 90 + 50 * k), 2)
    r.draw_text(
        sx,
        sy - raio * 2.4,
        "領域展開",
        26,
        a(LAVA_CLARA, 240),
        anchor="center",
        font_id=FONTE_PINCEL,
    )
    w = raio * 3
    r.draw_ui_rect(sx - w / 2, sy - raio * 1.85, w, 5, a(PRETO, 180))
    r.draw_ui_rect(sx - w / 2, sy - raio * 1.85, w * min(1.0, dano_frac), 5, TINTA)


def dominio_tela(r, tela, relogio, forca: float, cor=LAVA) -> None:
    """Dentro do domínio do chefe: a tela toma a cor dele, com veios subindo nas bordas."""
    w, h = tela
    r.draw_ui_rect(0, 0, w, h, a(cor, 38 * forca))
    for i in range(14):
        x = (i * 97 + relogio * 40) % w
        alto = 30 + 25 * math.sin(relogio * 3 + i)
        r.draw_ui_line(x, h, x + 12, h - alto, a(cor, 120 * forca), 3)
        r.draw_ui_line(w - x, 0, w - x - 12, alto, a(cor, 120 * forca), 3)


def seta_fora_da_tela(r, pos, tela, cor, margem: float = 26) -> None:
    """Quando o chefe sai da tela, uma seta na borda aponta para ele."""
    x, y = pos
    w, h = tela
    if margem <= x <= w - margem and margem <= y <= h - margem:
        return
    cx, cy = w / 2, h / 2
    ang = math.atan2(y - cy, x - cx)
    bx = min(max(x, margem), w - margem)
    by = min(max(y, margem), h - margem)
    c, s_ = math.cos(ang), math.sin(ang)
    pts = [
        (bx + c * 12, by + s_ * 12),
        (bx - s_ * 9 - c * 6, by + c * 9 - s_ * 6),
        (bx + s_ * 9 - c * 6, by - c * 9 - s_ * 6),
    ]
    r.draw_ui_polygon(pts, a(cor, 230))


# ------------------------------------------------- o seu domínio e o choque (passo 5)


def dominio_jogador_tela(r, tela, relogio, cor, forca: float) -> None:
    """Dentro do seu domínio: a tela toma a cor da técnica e pontos de luz giram devagar."""
    w, h = tela
    r.draw_ui_rect(0, 0, w, h, a(PRETO, 90 * forca))
    r.draw_ui_rect(0, 0, w, h, a(cor, 30 * forca))
    for i in range(40):
        ang = i * 2.39996 + relogio * 0.15
        rr = (i * 37) % (w // 2) + 40
        x = w / 2 + math.cos(ang) * rr
        y = h / 2 + math.sin(ang) * rr * 0.6
        brilho = 0.5 + 0.5 * math.sin(relogio * 3 + i)
        r.draw_ui_circle(x, y, 1.5 + brilho, a(TINTA, 200 * forca * brilho))


def choque_tela(r, tela, relogio, frac: float, cor) -> None:
    """O choque: o seu domínio (cor da técnica) e o dele (lava) disputando a tela."""
    w, h = tela
    corte = w * frac
    r.draw_ui_rect(0, 0, corte, h, a(cor, 45))
    r.draw_ui_rect(corte, 0, w - corte, h, a((255, 90, 20, 255), 45))
    pts = []
    for i in range(13):  # a linha de frente, serrilhada e tremendo
        y = h * i / 12
        pts.append((corte + math.sin(relogio * 20 + i * 1.7) * 10, y))
    for p, q in zip(pts, pts[1:], strict=False):
        r.draw_ui_line(p[0], p[1], q[0], q[1], a(TINTA, 220), 3)


def dominio_simples(r, sx, sy, raio, relogio) -> None:
    """O Domínio Simples: um círculo no chão com marcas, em volta do pé."""
    rr = raio * 4.2
    r.draw_ui_circle(sx, sy, rr, a(TINTA, 25))
    r.draw_ui_circle(sx, sy, rr, a(TINTA, 200), 2)
    for i in range(16):
        t = i * math.pi / 8 + relogio * 0.5
        x1, y1 = sx + math.cos(t) * rr, sy + math.sin(t) * rr
        x2, y2 = sx + math.cos(t) * (rr - 8), sy + math.sin(t) * (rr - 8)
        r.draw_ui_line(x1, y1, x2, y2, a(TINTA, 200), 2)


# ------------------------------------------------------- o segundo chefe (v1, passo 2)

PELE_REMENDO = (170, 196, 214, 255)
PELE_REMENDO_2 = (130, 158, 182, 255)
CABELO_REMENDO = (70, 92, 120, 255)
COSTURA = (40, 34, 50, 255)


def chefe_remendos(r, sx, sy, raio, relogio, olhar, *, ferido=False, queimado=False) -> None:
    """Visto de cima: um corpo humano feito de retalhos costurados, cabelo comprido caído
    para trás e braços que mudam de forma (um deles vira lâmina)."""
    raio *= 1.4
    ang = math.atan2(olhar[1], olhar[0])
    px, py = -olhar[1], olhar[0]
    r.draw_ui_polygon(elipse(sx + 5, sy + 8, raio * 1.1, raio * 0.8, ang), a(PRETO, 130))
    for lado in (-1, 1):  # os braços: o direito é uma lâmina que pulsa
        ox, oy = sx + px * lado * raio * 0.7, sy + py * lado * raio * 0.7
        if lado == 1:
            k = 1.3 + 0.2 * math.sin(relogio * 4)
            ponta = (ox + olhar[0] * raio * k * 1.4, oy + olhar[1] * raio * k * 1.4)
            base1 = (ox + px * raio * 0.18, oy + py * raio * 0.18)
            base2 = (ox - px * raio * 0.18, oy - py * raio * 0.18)
            r.draw_ui_polygon([base1, ponta, base2], PELE_REMENDO_2)
            r.draw_ui_polygon([base1, ponta, base2], COSTURA, 1)
        else:
            bx, by = ox + olhar[0] * raio * 0.6, oy + olhar[1] * raio * 0.6
            r.draw_ui_line(ox, oy, bx, by, COSTURA, int(raio * 0.36) + 3)
            r.draw_ui_line(ox, oy, bx, by, PELE_REMENDO, int(raio * 0.36))
            r.draw_ui_circle(bx, by, raio * 0.2, PELE_REMENDO)
    ombros = elipse(sx, sy, raio * 0.48, raio * 0.92, ang)
    r.draw_ui_polygon(ombros, TINTA if ferido else (36, 40, 52, 255))
    r.draw_ui_polygon(ombros, PELE_REMENDO_2, 2)
    # a cabeça: pele de retalhos e o cabelo comprido escorrendo para trás
    hx, hy = sx + olhar[0] * raio * 0.1, sy + olhar[1] * raio * 0.1
    for i in range(7):
        t = ang + math.pi + (i - 3) * 0.22
        comp = raio * (0.9 + 0.12 * math.sin(relogio * 2 + i))
        r.draw_ui_line(hx, hy, hx + math.cos(t) * comp, hy + math.sin(t) * comp, CABELO_REMENDO, 4)
    r.draw_ui_circle(hx, hy, raio * 0.36, PELE_REMENDO)
    r.draw_ui_circle(hx, hy, raio * 0.36, COSTURA, 1)
    for k in (-1, 1):  # as costuras atravessando o rosto
        x1 = hx + px * raio * 0.3 * k - olhar[0] * raio * 0.2
        y1 = hy + py * raio * 0.3 * k - olhar[1] * raio * 0.2
        x2 = hx + olhar[0] * raio * 0.3 + px * raio * 0.05 * k
        y2 = hy + olhar[1] * raio * 0.3 + py * raio * 0.05 * k
        r.draw_ui_line(x1, y1, x2, y2, COSTURA, 2)
    if queimado:
        r.draw_ui_circle(hx, hy, raio * 0.5, a(PRETO, 120))


def transfigurado(r, sx, sy, raio, relogio, *, ferido=False, vida=1.0) -> None:
    """Um humano transfigurado: massa pálida e torta, membros a mais, uma boca aberta."""
    pts = []
    for i in range(14):
        t = 2 * math.pi * i / 14
        rr = raio * (1 + 0.25 * math.sin(t * 3 + relogio * 6) + 0.1 * math.sin(t * 5))
        pts.append((sx + math.cos(t) * rr, sy + math.sin(t) * rr))
    r.draw_ui_polygon(elipse(sx + 3, sy + 5, raio, raio * 0.7), a(PRETO, 110))
    r.draw_ui_polygon(pts, TINTA if ferido else PELE_REMENDO_2)
    r.draw_ui_polygon(pts, COSTURA, 2)
    for i in range(5):
        t = i * 1.3 + math.sin(relogio * 8 + i) * 0.4
        r.draw_ui_line(
            sx + math.cos(t) * raio * 0.8,
            sy + math.sin(t) * raio * 0.8,
            sx + math.cos(t) * raio * 1.6,
            sy + math.sin(t) * raio * 1.6,
            PELE_REMENDO,
            3,
        )
    r.draw_ui_circle(sx, sy, raio * 0.35, COSTURA)
    if vida < 1:
        r.draw_ui_rect(sx - raio, sy - raio * 1.8, raio * 2, 3, a(PRETO, 160))
        r.draw_ui_rect(sx - raio, sy - raio * 1.8, raio * 2 * vida, 3, SANGUE)


DESENHOS_CHEFE = {"vulcao": chefe_vulcao, "remendos": chefe_remendos}


def desenhar_chefe(visual, r, sx, sy, raio, relogio, olhar, **kw) -> None:
    DESENHOS_CHEFE.get(visual, chefe_vulcao)(r, sx, sy, raio, relogio, olhar, **kw)


# ------------------------------------------------------- o terceiro chefe (v1, passo 6)

PELE_REI = (226, 196, 176, 255)
TATUAGEM = (20, 14, 18, 255)
CABELO_REI = (232, 150, 160, 255)
QUIMONO = (236, 232, 226, 255)


def chefe_rei(r, sx, sy, raio, relogio, olhar, *, ferido=False, queimado=False) -> None:
    """Visto de cima: quatro braços, quimono claro, cabelo rosa espetado e as marcas pretas."""
    raio *= 1.75
    ang = math.atan2(olhar[1], olhar[0])
    px, py = -olhar[1], olhar[0]
    r.draw_ui_polygon(elipse(sx + 5, sy + 8, raio * 1.15, raio * 0.85, ang), a(PRETO, 140))
    for par, (frente, abre) in enumerate(((0.55, 0.85), (0.05, 1.05))):  # os 4 braços
        for lado in (-1, 1):
            ox, oy = sx + px * lado * raio * 0.6, sy + py * lado * raio * 0.6
            balanco = math.sin(relogio * 3 + par + lado) * 0.08
            bx = sx + px * lado * raio * abre + olhar[0] * raio * (frente + balanco)
            by = sy + py * lado * raio * abre + olhar[1] * raio * (frente + balanco)
            r.draw_ui_line(ox, oy, bx, by, TATUAGEM, int(raio * 0.36) + 4)
            r.draw_ui_line(ox, oy, bx, by, PELE_REI, int(raio * 0.36))
            r.draw_ui_circle(bx, by, raio * 0.17, PELE_REI)
            r.draw_ui_line(  # a faixa tatuada no antebraço
                ox + (bx - ox) * 0.55 - px * 3,
                oy + (by - oy) * 0.55 - py * 3,
                ox + (bx - ox) * 0.55 + px * 3,
                oy + (by - oy) * 0.55 + py * 3,
                TATUAGEM,
                2,
            )
    ombros = elipse(sx, sy, raio * 0.5, raio * 0.95, ang)
    r.draw_ui_polygon(ombros, TINTA if ferido else QUIMONO)
    r.draw_ui_polygon(ombros, TATUAGEM, 2)
    r.draw_ui_line(  # a gola cruzada do quimono
        sx + olhar[0] * raio * 0.45 - px * raio * 0.3,
        sy + olhar[1] * raio * 0.45 - py * raio * 0.3,
        sx + px * raio * 0.1,
        sy + py * raio * 0.1,
        TATUAGEM,
        2,
    )
    hx, hy = sx + olhar[0] * raio * 0.08, sy + olhar[1] * raio * 0.08
    espetos = []
    for i in range(16):
        t = 2 * math.pi * i / 16
        rr = raio * (0.46 if i % 2 else 0.32)
        espetos.append((hx + math.cos(t) * rr, hy + math.sin(t) * rr))
    r.draw_ui_polygon(espetos, (120, 120, 120, 255) if queimado else CABELO_REI)
    r.draw_ui_polygon(espetos, TATUAGEM, 1)
    fx, fy = hx + olhar[0] * raio * 0.32, hy + olhar[1] * raio * 0.32
    r.draw_ui_circle(fx, fy, raio * 0.16, PELE_REI)
    for k in (-1, 1):  # os dois pares de olhos, o de baixo é a marca
        r.draw_ui_circle(fx + px * k * raio * 0.08, fy + py * k * raio * 0.08, 2, SANGUE)


def aviso_corte(r, cam, c, cor) -> None:
    """O aviso do corte: uma linha fina que engrossa até cortar."""
    k = 1 - c.t / c.atraso if c.atraso > 0 else 1.0
    p1, p2 = cam.tela_de(c.x1, c.y1), cam.tela_de(c.x2, c.y2)
    r.draw_ui_line(p1[0], p1[1], p2[0], p2[1], a(cor, 40 + 60 * k), max(1, int(c.largura * k)))
    r.draw_ui_line(p1[0], p1[1], p2[0], p2[1], a(TINTA, 120 + 120 * k), 1)


DESENHOS_CHEFE["rei"] = chefe_rei
