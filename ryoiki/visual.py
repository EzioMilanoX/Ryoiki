"""A cara do Ryoiki na visão 3/4 (2.5D): chão de concreto rachado em perspectiva, selos,
véu com a parede do fundo, avisos no chão, HUD e efeitos (faíscas de tinta, o Clarão Negro,
números). As figuras em pé ficam em `figuras.py`.

Tudo com as primitivas de UI do renderer, em coordenadas de tela. Nada de círculo em
grade: o chão é uma rua à noite dentro de uma cortina, e as figuras têm corpo.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ryoiki.movimento import ESCALA_Y

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
        y = y0 + k * LADO_PLACA * ESCALA_Y
        if 0 <= y <= lh:
            r.draw_ui_line(max(0, x0), y, min(lw, x1), y, JUNTA, 2)
        k += 1
    for cx, cy, raio in cenario.selos:  # selos de contenção, quase apagados
        sx, sy = cam.tela_de(cx, cy)
        if -raio < sx < lw + raio and -raio < sy < lh + raio:
            oval(r, sx, sy, raio, a(SELO, 34), 2)
            oval(r, sx, sy, raio * 0.78, a(SELO, 24), 1)
            for i in range(8):
                t = i * math.pi / 4 + relogio * 0.05
                r.draw_ui_line(
                    sx + math.cos(t) * raio * 0.78,
                    sy + math.sin(t) * raio * 0.78 * ESCALA_Y,
                    sx + math.cos(t) * raio,
                    sy + math.sin(t) * raio * ESCALA_Y,
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
            oval(r, sx, sy, raio, a(RACHADURA, 150))
    parede_do_fundo(r, x0, y0, x1, relogio)
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


def area_pendente(r, cam, ar, cor, relogio) -> None:
    """O aviso da área: um anel que fecha até a hora de explodir."""
    if ar.raio < 0:
        return
    sx, sy = cam.tela_de(ar.x, ar.y)
    k = 1 - ar.t / ar.atraso if ar.atraso > 0 else 1.0
    oval(r, sx, sy, ar.raio, a(cor, 40 + 60 * k))
    oval(r, sx, sy, ar.raio, a(cor, 200), 2)
    oval(r, sx, sy, ar.raio * (1 - k) + 6, a(cor, 220), 3)
    for i in range(6):  # a espiral sendo sugada para o centro
        t = relogio * 9 + i * math.pi / 3
        rr = ar.raio * (1 - k) * 0.9 + 8
        oval(r, sx + math.cos(t) * rr, sy + math.sin(t) * rr, 3, a(TINTA, 200))


# --------------------------------------------------------------- o chefe (passo 4)

ROCHA = (58, 50, 50, 255)
ROCHA_BORDA = (110, 92, 86, 255)
LAVA = (255, 120, 30, 255)
LAVA_CLARA = (255, 210, 120, 255)


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
    oval(r, sx, sy, e.raio, a(cor, 30 + 60 * k))
    oval(r, sx, sy, e.raio, a(cor, 210), 2)
    oval(r, sx, sy, e.raio * k, a(cor, 110))


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


# ------------------------------------------------------- o segundo chefe (v1, passo 2)

PELE_REMENDO = (170, 196, 214, 255)
PELE_REMENDO_2 = (130, 158, 182, 255)
CABELO_REMENDO = (70, 92, 120, 255)
COSTURA = (40, 34, 50, 255)


# ------------------------------------------------------- o terceiro chefe (v1, passo 6)

PELE_REI = (226, 196, 176, 255)
TATUAGEM = (20, 14, 18, 255)
CABELO_REI = (232, 150, 160, 255)
QUIMONO = (236, 232, 226, 255)


def aviso_corte(r, cam, c, cor) -> None:
    """O aviso do corte: uma linha fina que engrossa até cortar."""
    k = 1 - c.t / c.atraso if c.atraso > 0 else 1.0
    p1, p2 = cam.tela_de(c.x1, c.y1), cam.tela_de(c.x2, c.y2)
    r.draw_ui_line(p1[0], p1[1], p2[0], p2[1], a(cor, 40 + 60 * k), max(1, int(c.largura * k)))
    r.draw_ui_line(p1[0], p1[1], p2[0], p2[1], a(TINTA, 120 + 120 * k), 1)


# ------------------------------------------------------------- o quarto chefe (v1, passo 7)

CARNE_ABISMO = (150, 72, 62, 255)
CARNE_ABISMO_2 = (104, 44, 44, 255)
AGUA = (60, 170, 190, 255)


# ------------------------------------------------------ o acabamento (barras, luz, tinta)


def clarear(cor, k: float) -> tuple[int, int, int, int]:
    return (*(int(c + (255 - c) * k) for c in cor[:3]), cor[3] if len(cor) > 3 else 255)


def barra(r, x, y, w, h, frac, cor, *, fantasma=None, inclinacao=6) -> None:
    """Barra inclinada: fundo, o rastro claro do dano recente, o valor, um brilho e a borda."""
    frac = max(0.0, min(1.0, frac))

    def para(x0, x1, y0, y1, c, largura=0):
        pts = [(x0 + inclinacao, y0), (x1 + inclinacao, y0), (x1, y1), (x0, y1)]
        r.draw_ui_polygon(pts, c, largura)

    para(x - 3, x + w + 3, y - 3, y + h + 3, a(PRETO, 200))
    if fantasma is not None and fantasma > frac:
        para(x + w * frac, x + w * min(1.0, fantasma), y, y + h, a(TINTA, 210))
    if frac > 0:
        para(x, x + w * frac, y, y + h, cor)
        para(x, x + w * frac, y, y + max(2, h * 0.35), a(clarear(cor, 0.45), 220))
    para(x - 3, x + w + 3, y - 3, y + h + 3, a(clarear(cor, 0.2), 150), 1)


@dataclass
class Mancha:
    """Tinta que fica no chão depois de um acerto."""

    x: float
    y: float
    pts: tuple  # relativos ao centro
    cor: tuple


def nova_mancha(rng: random.Random, x, y, raio, cor) -> Mancha:
    pts = []
    n = 11
    for i in range(n):
        t = 2 * math.pi * i / n
        rr = raio * rng.uniform(0.55, 1.15)
        pts.append((math.cos(t) * rr, math.sin(t) * rr * 0.8))
    for _ in range(2):  # respingos soltos
        t, d = rng.uniform(0, 2 * math.pi), raio * rng.uniform(1.3, 2.0)
        pts.append((math.cos(t) * d, math.sin(t) * d))
    return Mancha(x, y, tuple(pts), cor)


def fundo_titulo(r, w, h, relogio) -> None:
    """A noite de Tóquio vista de longe: céu em degradê, lua, prédios com janelas e névoa."""
    for i in range(24):  # o céu: do roxo do véu, embaixo, ao preto, em cima
        k = i / 23
        cor = (int(10 + 34 * k), int(9 + 8 * k), int(13 + 46 * k), 255)
        r.draw_ui_rect(0, h * 0.62 * k, w, h * 0.62 / 23 + 1, cor)
    r.draw_ui_rect(0, h * 0.62, w, h * 0.38, NOITE)
    lx, ly = w * 0.78, h * 0.2
    for i in range(6):  # o halo da lua (no céu, não no chão: redondo)
        r.draw_ui_circle(lx, ly, 46 * (2.2 - i * 0.22), a((235, 225, 230, 255), 18))
    r.draw_ui_circle(lx, ly, 40, (232, 222, 228, 255))
    k = (ly - 6) / (h * 0.62)  # o disco que corta a lua tem a cor do céu ali
    ceu = (int(10 + 34 * k), int(9 + 8 * k), int(13 + 46 * k), 255)
    r.draw_ui_circle(lx + 12, ly - 6, 34, ceu)  # a lua em foice
    rng = random.Random(11)
    x = 0.0
    while x < w:  # os prédios, sempre os mesmos (semente fixa)
        larg = rng.uniform(40, 90)
        alto = rng.uniform(h * 0.18, h * 0.42)
        topo = h * 0.62 - alto + h * 0.1
        r.draw_ui_rect(x, topo, larg + 1, h - topo, (12, 10, 16, 255))
        for jy in range(int(topo) + 10, int(h * 0.7), 16):
            for jx in range(int(x) + 8, int(x + larg) - 6, 14):
                if rng.random() < 0.18:
                    acesa = 0.6 + 0.4 * math.sin(relogio * 0.7 + jx * 0.3 + jy)
                    r.draw_ui_rect(jx, jy, 5, 7, a((235, 200, 120, 255), 120 * acesa))
        x += larg + rng.uniform(2, 10)
    for i in range(3):  # a névoa passando
        y = h * (0.62 + 0.08 * i)
        dx = (relogio * (12 + 6 * i)) % w
        for k in (-1, 0):
            r.draw_ui_rect(dx + k * w, y, w * 0.7, 26, a(VEU, 40))
    r.draw_ui_rect(0, 0, w, h, a(PRETO, 60))


# ----------------------------------------------- a visão 3/4 (2.5D): o chão e as alturas

ALTURA_EFEITO = 30  # faíscas e números saem na altura do peito, não do chão
ALTURA_TIRO = 26  # projéteis voam acima do chão (com sombra embaixo)


def oval(r, sx, sy, raio, cor, largura=0) -> None:
    """Um círculo deitado no chão: na visão 3/4 ele vira oval."""
    r.draw_ui_polygon(elipse(sx, sy, raio, raio * ESCALA_Y, n=28), cor, largura)


def arco_chao(r, sx, sy, raio, a0, a1, cor, largura=2) -> None:
    """Um arco deitado no chão (ângulos do mundo)."""
    n = max(6, int(abs(a1 - a0) * 10))
    pts = [
        (
            sx + math.cos(a0 + (a1 - a0) * i / n) * raio,
            sy + math.sin(a0 + (a1 - a0) * i / n) * raio * ESCALA_Y,
        )
        for i in range(n + 1)
    ]
    for p, q in zip(pts, pts[1:], strict=False):
        r.draw_ui_line(p[0], p[1], q[0], q[1], cor, largura)


def brilho(r, sx, sy, raio, cor, forca: float = 1.0) -> None:
    """Uma luz suave no chão: ovais concêntricas bem transparentes."""
    if forca <= 0:
        return
    for i in range(6):
        oval(r, sx, sy, raio * (2.2 - i * 0.22), a(cor, 9 * forca))


def desenhar_mancha(r, cam, m: Mancha) -> None:
    sx, sy = cam.tela_de(m.x, m.y)
    corpo = [(sx + px, sy + py * ESCALA_Y) for px, py in m.pts[:-2]]
    r.draw_ui_polygon(corpo, m.cor)
    for px, py in m.pts[-2:]:
        r.draw_ui_circle(sx + px, sy + py * ESCALA_Y, 2.5, m.cor)


def marca(r, sx, sy, topo, raio, relogio, cor) -> None:
    """O prego cravado: um losango que pisca acima da cabeça e um anel no chão."""
    y = topo - 10 + math.sin(relogio * 6) * 2
    r.draw_ui_polygon([(sx, y - 7), (sx + 5, y), (sx, y + 7), (sx - 5, y)], a(cor, 230))
    oval(r, sx, sy, raio * 1.4, a(cor, 90 + 60 * math.sin(relogio * 8)), 1)


def atordoado(r, sx, topo, raio, relogio) -> None:
    for i in range(3):
        t = relogio * 5 + i * 2.1
        r.draw_ui_circle(sx + math.cos(t) * raio * 0.9, topo - 4 + math.sin(t) * 3, 3, a(OLHO, 220))


def entoando(r, sx, sy, topo, raio, k, dano_frac, cor=LAVA) -> None:
    """A entoação do domínio: anéis fechando no chão, 領域展開 e a barra do que falta cortar."""
    for i in range(3):
        oval(r, sx, sy, raio * (1.4 + (1 - k) * (2.5 + i)), a(cor, 90 + 50 * k), 2)
    r.draw_text(
        sx, topo - 30, "領域展開", 26, a(LAVA_CLARA, 240), anchor="center", font_id=FONTE_PINCEL
    )
    w = raio * 3
    r.draw_ui_rect(sx - w / 2, topo - 12, w, 5, a(PRETO, 180))
    r.draw_ui_rect(sx - w / 2, topo - 12, w * min(1.0, dano_frac), 5, TINTA)


def escudo(r, sx, sy, topo, raio, relogio, bloqueou: bool) -> None:
    """O reforço: um casco hexagonal de energia em volta do corpo de pé."""
    cy, ry, rx = (sy + topo) / 2, (sy - topo) * 0.62, raio * 1.9
    pts = [
        (
            sx + math.cos(i * math.pi / 3 + relogio * 0.8) * rx,
            cy + math.sin(i * math.pi / 3 + relogio * 0.8) * ry,
        )
        for i in range(6)
    ]
    r.draw_ui_polygon(pts, a(ENERGIA, 90 if bloqueou else 35))
    r.draw_ui_polygon(pts, a(ENERGIA, 220 if bloqueou else 120), 2)


def reversa(r, sx, sy, topo, raio, relogio) -> None:
    """A Técnica Reversa: energia clara subindo do chão até acima da cabeça."""
    oval(r, sx, sy, raio * 1.7 + math.sin(relogio * 10) * 2, a(CURA, 110), 2)
    for i in range(6):
        k = (relogio * 1.6 + i / 6) % 1
        x = sx + math.sin(i * 2.4 + relogio * 3) * raio * 0.9
        r.draw_ui_circle(x, sy - k * (sy - topo + 20), 3 + 2 * (1 - k), a(CURA, 220 * (1 - k)))


def dominio_simples(r, sx, sy, raio, relogio) -> None:
    """O Domínio Simples: um círculo no chão com marcas, em volta do pé."""
    rr = raio * 4.2
    oval(r, sx, sy, rr, a(TINTA, 25))
    oval(r, sx, sy, rr, a(TINTA, 200), 2)
    for i in range(16):
        t = i * math.pi / 8 + relogio * 0.5
        c, s = math.cos(t), math.sin(t) * ESCALA_Y
        r.draw_ui_line(
            sx + c * rr, sy + s * rr, sx + c * (rr - 8), sy + s * (rr - 8), a(TINTA, 200), 2
        )


def projetil(r, cam, p, cor) -> None:
    sx, sy = cam.tela_de(p.x, p.y)
    oval(r, sx, sy, p.raio, a(PRETO, 90))  # a sombra no chão
    sy -= ALTURA_TIRO
    for k in (3, 2, 1):  # o rastro: círculos que somem para trás
        d = k * p.raio * 1.1
        r.draw_ui_circle(
            sx - p.dx * d, sy - p.dy * d * ESCALA_Y, p.raio * (1 - k * 0.2), a(cor, 50 * (4 - k))
        )
    r.draw_ui_circle(sx, sy, p.raio + 3, a(cor, 200))
    r.draw_ui_circle(sx, sy, p.raio * 0.6, TINTA)


def brasa(r, cam, b, relogio, cor=LAVA) -> None:
    sx, sy = cam.tela_de(b.x, b.y)
    oval(r, sx, sy, b.raio, a(PRETO, 90))
    sy -= ALTURA_TIRO
    v = math.hypot(b.vx, b.vy) or 1
    for k in (3, 2, 1):
        d = k * b.raio * 0.9
        r.draw_ui_circle(
            sx - b.vx / v * d,
            sy - b.vy / v * d * ESCALA_Y,
            b.raio * (1 - k * 0.22),
            a(cor, 60 * (4 - k)),
        )
    r.draw_ui_circle(sx, sy, b.raio, cor)
    r.draw_ui_circle(sx, sy, b.raio * (0.45 + 0.15 * math.sin(relogio * 30)), LAVA_CLARA)


def desenhar_efeito(r, cam, e: Efeito) -> None:
    k = e.t / e.vida
    sx, sy = cam.tela_de(e.x, e.y)
    alto = sy - ALTURA_EFEITO
    if e.tipo == "faisca":
        cauda = 0.03
        r.draw_ui_line(
            sx, alto, sx - e.vx * cauda, alto - e.vy * cauda * ESCALA_Y, a(e.cor, 255 * (1 - k)), 2
        )
    elif e.tipo == "onda":
        oval(r, sx, sy, 10 + e.raio * k, a(e.cor, 160 * (1 - k)), 2)
    elif e.tipo == "linha":  # o rastro de um corte, sumindo
        p1, p2 = cam.tela_de(*e.pts[0]), cam.tela_de(*e.pts[1])
        r.draw_ui_line(
            p1[0], p1[1], p2[0], p2[1], a(e.cor, 230 * (1 - k)), max(1, int(6 * (1 - k)))
        )
        r.draw_ui_line(p1[0], p1[1], p2[0], p2[1], a(TINTA, 255 * (1 - k)), 1)
    elif e.tipo == "raio":
        pts = [cam.tela_de(x, y) for x, y in e.pts]
        pts = [(x, y - ALTURA_EFEITO) for x, y in pts]
        for p, q in zip(pts, pts[1:], strict=False):
            r.draw_ui_line(p[0], p[1], q[0], q[1], a(SANGUE, 230 * (1 - k)), 7)
            r.draw_ui_line(p[0], p[1], q[0], q[1], a(PRETO, 255 * (1 - k)), 3)
    elif e.tipo == "numero":
        grande = len(e.texto) and e.vida > 0.6
        r.draw_text(
            sx,
            alto - 20,
            e.texto,
            30 if grande else 20,
            a(SANGUE if grande else e.cor, 255 * (1 - k * k)),
            anchor="center",
            font_id=FONTE_PINCEL,
        )


def parede_do_fundo(r, x0, y0, x1, relogio) -> None:
    """A cortina do véu subindo atrás da arena: dá a profundidade da visão 3/4."""
    alto = 150
    for i in range(10):
        k = i / 9
        r.draw_ui_rect(x0, y0 - alto * (1 - k), x1 - x0, alto / 9 + 1, a(VEU, 40 + 120 * k))
    for i in range(int((x1 - x0) / 22) + 1):
        x = x0 + i * 22
        onda = math.sin(relogio * 1.5 + i * 0.7) * 5
        r.draw_ui_line(x, y0 - alto, x + onda, y0, a((70, 30, 96, 255), 120), 2)
