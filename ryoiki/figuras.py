"""As figuras em pé, para a visão 3/4 (2.5D): o feiticeiro, os lacaios e os chefes.

`(sx, sy)` é o ponto dos **pés** no chão (já na tela). Cada função desenha a sombra e o corpo
de baixo para cima, vira para o lado da mira e devolve o **y do topo** da figura, que a cena
usa para a marca, o atordoamento e a barra de vida.
"""

from __future__ import annotations

import math

from ryoiki import sprites
from ryoiki.movimento import ESCALA_Y
from ryoiki.visual import (
    AGUA,
    CABELO,
    CABELO_REI,
    CABELO_REMENDO,
    CAMISA,
    CARNE_ABISMO,
    CARNE_ABISMO_2,
    CONTORNO,
    COSTURA,
    ENERGIA,
    LAVA,
    PELE,
    PELE_REI,
    PELE_REMENDO,
    PELE_REMENDO_2,
    PRETO,
    QUIMONO,
    ROCHA,
    ROCHA_BORDA,
    SANGUE,
    TATUAGEM,
    TINTA,
    UNIFORME,
    UNIFORME_BORDA,
    a,
    elipse,
)

DOURADO = (230, 190, 80, 255)


def sombra(r, sx, sy, largura: float) -> None:
    r.draw_ui_polygon(elipse(sx, sy, largura, largura * ESCALA_Y * 0.55), a(PRETO, 130))


def _lado(olhar) -> int:
    return 1 if olhar[0] >= 0 else -1


def _membro(r, x1, y1, x2, y2, cor, borda, largura) -> None:
    r.draw_ui_line(x1, y1, x2, y2, borda, largura + 3)
    r.draw_ui_line(x1, y1, x2, y2, cor, largura)


def _mira_tela(olhar) -> tuple[float, float]:
    """A direção da mira como ela aparece na tela (o chão é achatado)."""
    mx, my = olhar[0], olhar[1] * ESCALA_Y
    n = math.hypot(mx, my) or 1.0
    return mx / n, my / n


def _cabelo_espetado(r, hx, hy, raio, lado, cor, borda, pontas=9) -> None:
    pts = []
    for i in range(pontas + 1):  # do lado de trás, por cima, até a testa
        t = math.pi * (0.55 + 1.05 * i / pontas)
        t = t if lado > 0 else math.pi - t
        rr = raio * (1.35 if i % 2 else 1.0)
        pts.append((hx + math.cos(t) * rr, hy + math.sin(t) * rr))
    pts.append((hx, hy + raio * 0.2))
    r.draw_ui_polygon(pts, cor)
    r.draw_ui_polygon(pts, borda, 1)


# ------------------------------------------------------------------- o feiticeiro


def feiticeiro(
    r,
    sx,
    sy,
    raio,
    mira,
    relogio,
    *,
    punho=None,
    aura=0.0,
    zona=False,
    invencivel=False,
    andando=0.0,
) -> float:
    """Uniforme escuro de gola alta com botão dourado, cabelo espetado; o braço da frente
    (ou o de trás, alternando no combo) estica na direção da mira."""
    h = raio * 4.6
    lado = _lado(mira)
    mx, my = _mira_tela(mira)
    quadril, ombro, cab = sy - h * 0.42, sy - h * 0.72, sy - h * 0.86
    sombra(r, sx, sy, raio * 1.25)
    if aura > 0 or zona:  # a energia subindo do corpo como chama
        cor = SANGUE if zona else ENERGIA
        r.draw_ui_polygon(elipse(sx, sy, raio * 1.6, raio * 0.6), a(cor, 50 + 50 * aura), 2)
        for i in range(8):
            k = (relogio * 1.8 + i / 8) % 1
            x = sx + math.sin(i * 2.3 + relogio * 2) * raio * 0.95
            y = sy - k * h
            r.draw_ui_line(x, y, x, y - 8 - 10 * (1 - k), a(cor, (80 + 90 * aura) * (1 - k)), 3)
    passo = math.sin(relogio * 14) * andando
    for k, fase in ((-1, passo), (1, -passo)):  # as pernas
        px = sx + k * raio * 0.26
        _membro(
            r, px, quadril, px + fase * raio * 0.55, sy - 2, UNIFORME, CONTORNO, int(raio * 0.4)
        )
        r.draw_ui_line(
            px + fase * raio * 0.55 - 4,
            sy - 2,
            px + fase * raio * 0.55 + 5 * lado,
            sy - 2,
            PRETO,
            4,
        )

    def braco(ext: float, atras: bool) -> None:
        ox = sx + (-lado if atras else lado) * raio * 0.38
        oy = ombro + raio * 0.25
        if ext > 0.05:
            alcance = raio * (0.9 + 1.7 * ext)
            bx, by = ox + mx * alcance, oy + my * alcance
        else:
            bx, by = ox + lado * raio * 0.2, oy + raio * 1.25
        _membro(r, ox, oy, bx, by, UNIFORME, CONTORNO, int(raio * 0.34))
        r.draw_ui_circle(bx, by, raio * 0.22, PELE)
        if ext > 0.6:
            r.draw_ui_circle(bx, by, raio * 0.48, a(SANGUE if zona else ENERGIA, 170), 2)

    ext_tras = punho[1] if punho and punho[0] in (-1, 0) else 0.0
    ext_frente = punho[1] if punho and punho[0] in (1, 0) else 0.0
    braco(ext_tras, atras=True)
    corpo = UNIFORME_BORDA if invencivel else UNIFORME
    balanco = math.sin(relogio * 5) * raio * 0.08
    tronco = [  # o casaco do uniforme, abrindo um pouco embaixo
        (sx - raio * 0.5, ombro),
        (sx + raio * 0.5, ombro),
        (sx + raio * 0.62 - lado * balanco, quadril + raio * 0.55),
        (sx - raio * 0.62 - lado * balanco, quadril + raio * 0.55),
    ]
    r.draw_ui_polygon(tronco, corpo)
    r.draw_ui_polygon(tronco, CONTORNO, 1)
    r.draw_ui_line(
        sx + lado * raio * 0.1, ombro, sx + lado * raio * 0.1, quadril + raio * 0.5, PRETO, 1
    )
    gola = [
        (sx - raio * 0.3, ombro - raio * 0.32),
        (sx + raio * 0.3, ombro - raio * 0.32),
        (sx + raio * 0.36, ombro + raio * 0.05),
        (sx - raio * 0.36, ombro + raio * 0.05),
    ]
    r.draw_ui_polygon(gola, corpo)
    r.draw_ui_polygon(gola, CONTORNO, 1)
    r.draw_ui_circle(sx + lado * raio * 0.18, ombro - raio * 0.08, raio * 0.09, DOURADO)
    r.draw_ui_line(
        sx - raio * 0.2, ombro - raio * 0.3, sx + raio * 0.2, ombro - raio * 0.3, CAMISA, 2
    )
    hx = sx + lado * raio * 0.05
    r.draw_ui_circle(hx, cab, raio * 0.48, PELE)
    r.draw_ui_circle(hx + lado * raio * 0.24, cab + raio * 0.02, raio * 0.07, PRETO)  # o olho
    _cabelo_espetado(
        r, hx - lado * raio * 0.05, cab - raio * 0.1, raio * 0.48, lado, CABELO, CONTORNO
    )
    braco(ext_frente, atras=False)
    return cab - raio * 0.8


# ------------------------------------------------------------------- os lacaios


def transfigurado(r, sx, sy, raio, relogio, *, ferido=False, vida=1.0) -> float:
    """Um humano transfigurado: massa pálida e torta de pé, membros a mais, boca aberta."""
    h = raio * 2.6
    sombra(r, sx, sy, raio * 1.1)
    cy = sy - h * 0.5
    pts = []
    for i in range(14):
        t = 2 * math.pi * i / 14
        rr = 1 + 0.2 * math.sin(t * 3 + relogio * 6)
        pts.append((sx + math.cos(t) * raio * 0.9 * rr, cy + math.sin(t) * h * 0.5 * rr))
    for i in range(4):  # braços demais, mexendo
        t = i * 1.4 + math.sin(relogio * 8 + i) * 0.4
        r.draw_ui_line(
            sx, cy, sx + math.cos(t) * raio * 1.6, cy + math.sin(t) * raio * 1.2, PELE_REMENDO, 3
        )
    r.draw_ui_polygon(pts, TINTA if ferido else PELE_REMENDO_2)
    r.draw_ui_polygon(pts, COSTURA, 2)
    r.draw_ui_polygon(elipse(sx, cy + raio * 0.2, raio * 0.35, raio * 0.5), COSTURA)
    topo = sy - h - 4
    if vida < 1:
        r.draw_ui_rect(sx - raio, topo - 6, raio * 2, 3, a(PRETO, 160))
        r.draw_ui_rect(sx - raio, topo - 6, raio * 2 * vida, 3, SANGUE)
    return topo


# ------------------------------------------------------------------- os chefes


def chefe_vulcao(r, sx, sy, raio, relogio, olhar, *, ferido=False, queimado=False) -> float:
    """Jogo: corpo baixo e largo de rocha, a cabeça é um vulcão com lava e um olho só."""
    h = raio * 3.0
    lado = _lado(olhar)
    sombra(r, sx, sy, raio * 1.3)
    for k in (-1, 1):  # as pernas curtas
        _membro(
            r,
            sx + k * raio * 0.4,
            sy - h * 0.22,
            sx + k * raio * 0.45,
            sy - 2,
            ROCHA,
            ROCHA_BORDA,
            int(raio * 0.4),
        )
    cy = sy - h * 0.38
    corpo = elipse(sx, cy, raio * 1.0, h * 0.2)
    r.draw_ui_polygon(corpo, TINTA if ferido else ROCHA)
    r.draw_ui_polygon(corpo, ROCHA_BORDA, 2)
    for k in (-1, 1):  # os braços grossos
        bx = sx + k * raio * 1.25 + (lado * raio * 0.3 if k == lado else 0)
        _membro(
            r,
            sx + k * raio * 0.8,
            cy - h * 0.08,
            bx,
            cy + h * 0.06,
            ROCHA,
            ROCHA_BORDA,
            int(raio * 0.42),
        )
        r.draw_ui_circle(bx, cy + h * 0.06, raio * 0.28, ROCHA_BORDA)
    base, topo = sy - h * 0.55, sy - h
    cone = [
        (sx - raio * 0.72, base),
        (sx + raio * 0.72, base),
        (sx + raio * 0.36, topo),
        (sx - raio * 0.36, topo),
    ]
    r.draw_ui_polygon(cone, TINTA if ferido else ROCHA)
    r.draw_ui_polygon(cone, ROCHA_BORDA, 2)
    pulso = 0.5 + 0.5 * math.sin(relogio * 6)
    lava = (90, 90, 90, 255) if queimado else LAVA
    r.draw_ui_polygon(elipse(sx, topo, raio * 0.36, raio * 0.13), (40, 20, 18, 255))
    r.draw_ui_polygon(elipse(sx, topo, raio * (0.24 + 0.05 * pulso), raio * 0.08), lava)
    if not queimado:
        for i in range(3):  # a lava escorrendo pelo cone
            x = sx + (i - 1) * raio * 0.2
            r.draw_ui_line(x, topo + 2, x + (i - 1) * raio * 0.15, topo + h * 0.12 + i * 4, LAVA, 3)
    for i in range(3):  # a fumaça
        k = (relogio * 0.7 + i / 3) % 1
        r.draw_ui_circle(
            sx + math.sin(relogio + i * 2) * 8,
            topo - k * raio * 1.6,
            raio * (0.15 + 0.25 * k),
            a((70, 64, 66, 255), 150 * (1 - k)),
        )
    ex, ey = sx + lado * raio * 0.22, base - (base - topo) * 0.45
    r.draw_ui_polygon(elipse(ex, ey, raio * 0.22, raio * 0.16), (235, 228, 210, 255))
    r.draw_ui_circle(ex + lado * 3, ey, raio * 0.09, PRETO)
    return topo - raio * 0.5


def chefe_remendos(r, sx, sy, raio, relogio, olhar, *, ferido=False, queimado=False) -> float:
    """Mahito: alto e magro, pele de retalhos costurados, cabelo comprido caído para trás,
    um braço que vira lâmina apontando para você."""
    h = raio * 4.6
    lado = _lado(olhar)
    mx, my = _mira_tela(olhar)
    quadril, ombro, cab = sy - h * 0.44, sy - h * 0.74, sy - h * 0.87
    sombra(r, sx, sy, raio * 1.1)
    passo = math.sin(relogio * 6) * 0.2
    for k in (-1, 1):
        _membro(
            r,
            sx + k * raio * 0.22,
            quadril,
            sx + k * raio * (0.25 + passo),
            sy - 2,
            (36, 40, 52, 255),
            COSTURA,
            int(raio * 0.32),
        )
    hx = sx + lado * raio * 0.05
    for i in range(6):  # o cabelo comprido, para trás
        x0 = hx - lado * raio * (0.1 + i * 0.07)
        r.draw_ui_line(
            x0,
            cab - raio * 0.3,
            x0 - lado * raio * 0.35,
            ombro + raio * (0.5 + 0.15 * math.sin(relogio * 2 + i)),
            CABELO_REMENDO,
            4,
        )
    tronco = [
        (sx - raio * 0.45, ombro),
        (sx + raio * 0.45, ombro),
        (sx + raio * 0.38, quadril),
        (sx - raio * 0.38, quadril),
    ]
    r.draw_ui_polygon(tronco, TINTA if ferido else (36, 40, 52, 255))
    r.draw_ui_polygon(tronco, PELE_REMENDO_2, 1)
    _membro(
        r,
        sx - lado * raio * 0.4,
        ombro + 4,
        sx - lado * raio * 0.5,
        quadril,
        PELE_REMENDO,
        COSTURA,
        int(raio * 0.26),
    )
    ox, oy = sx + lado * raio * 0.4, ombro + 4
    k = 1.6 + 0.25 * math.sin(relogio * 4)
    ponta = (ox + mx * raio * k * 1.4, oy + my * raio * k * 1.4)
    px, py = -my, mx
    lamina = [
        (ox + px * raio * 0.16, oy + py * raio * 0.16),
        ponta,
        (ox - px * raio * 0.16, oy - py * raio * 0.16),
    ]
    r.draw_ui_polygon(lamina, PELE_REMENDO_2)
    r.draw_ui_polygon(lamina, COSTURA, 1)
    r.draw_ui_circle(hx, cab, raio * 0.42, PELE_REMENDO)
    r.draw_ui_circle(hx, cab, raio * 0.42, COSTURA, 1)
    r.draw_ui_line(
        hx - raio * 0.35, cab - raio * 0.15, hx + raio * 0.3, cab + raio * 0.2, COSTURA, 2
    )
    r.draw_ui_line(
        hx + lado * raio * 0.1,
        cab - raio * 0.4,
        hx + lado * raio * 0.2,
        cab + raio * 0.35,
        COSTURA,
        1,
    )
    for k2 in (0.12, 0.3):
        r.draw_ui_circle(hx + lado * raio * k2, cab - raio * 0.02, 2, (40, 120, 140, 255))
    if queimado:
        r.draw_ui_circle(hx, cab, raio * 0.5, a(PRETO, 120))
    return cab - raio * 0.7


def chefe_rei(r, sx, sy, raio, relogio, olhar, *, ferido=False, queimado=False) -> float:
    """Sukuna: quimono claro, quatro braços, cabelo rosa espetado, as marcas pretas e os
    olhos vermelhos."""
    h = raio * 3.8
    lado = _lado(olhar)
    quadril, ombro, cab = sy - h * 0.42, sy - h * 0.72, sy - h * 0.86
    sombra(r, sx, sy, raio * 1.4)
    for k in (-1, 1):
        _membro(
            r,
            sx + k * raio * 0.3,
            quadril,
            sx + k * raio * 0.35,
            sy - 2,
            QUIMONO,
            TATUAGEM,
            int(raio * 0.4),
        )

    def bracos(atras: bool) -> None:
        s = -lado if atras else lado
        for n, (dy, abre) in enumerate(((0.15, 1.0), (0.55, 1.25))):
            ox, oy = sx + s * raio * 0.55, ombro + raio * dy
            bal = math.sin(relogio * 3 + n + s) * raio * 0.15
            bx, by = ox + s * raio * abre, oy + raio * (0.6 + 0.3 * n) + bal
            _membro(r, ox, oy, bx, by, PELE_REI, TATUAGEM, int(raio * 0.3))
            r.draw_ui_line(
                ox + (bx - ox) * 0.5,
                oy + (by - oy) * 0.5 - 3,
                ox + (bx - ox) * 0.5,
                oy + (by - oy) * 0.5 + 3,
                TATUAGEM,
                3,
            )

    bracos(atras=True)
    quimono = [
        (sx - raio * 0.6, ombro),
        (sx + raio * 0.6, ombro),
        (sx + raio * 0.8, quadril + raio * 0.7),
        (sx - raio * 0.8, quadril + raio * 0.7),
    ]
    r.draw_ui_polygon(quimono, TINTA if ferido else QUIMONO)
    r.draw_ui_polygon(quimono, TATUAGEM, 2)
    r.draw_ui_line(sx - raio * 0.35, ombro, sx + raio * 0.2, quadril, TATUAGEM, 2)  # a gola cruzada
    r.draw_ui_line(
        sx - raio * 0.7, quadril, sx + raio * 0.7, quadril, (120, 30, 40, 255), 4
    )  # a faixa
    hx = sx + lado * raio * 0.05
    r.draw_ui_circle(hx, cab, raio * 0.45, PELE_REI)
    _cabelo_espetado(
        r,
        hx - lado * raio * 0.05,
        cab - raio * 0.12,
        raio * 0.45,
        lado,
        (120, 120, 120, 255) if queimado else CABELO_REI,
        TATUAGEM,
        11,
    )
    for dy in (-0.02, 0.16):  # os dois pares de olhos (o de baixo, a marca)
        r.draw_ui_circle(hx + lado * raio * 0.22, cab + raio * dy, 2.2, SANGUE)
    r.draw_ui_line(
        hx + lado * raio * 0.05,
        cab + raio * 0.25,
        hx + lado * raio * 0.35,
        cab + raio * 0.3,
        TATUAGEM,
        2,
    )
    bracos(atras=False)
    return cab - raio * 0.75


def chefe_abismo(r, sx, sy, raio, relogio, olhar, *, ferido=False, queimado=False) -> float:
    """Dagon: uma cabeça bulbosa de polvo sobre uma saia de tentáculos, olhos pequenos e uma
    boca de lábios grossos; um anel de água no chão."""
    h = raio * 2.8
    lado = _lado(olhar)
    sombra(r, sx, sy, raio * 1.4)
    if not queimado:
        r.draw_ui_polygon(elipse(sx, sy, raio * 1.7, raio * 1.7 * ESCALA_Y), a(AGUA, 80), 2)
    for i in range(8):  # os tentáculos, abrindo no chão
        t = math.pi * (i / 7)
        x, y = sx + math.cos(t) * raio * 0.5, sy - h * 0.25
        pts = [(x, y)]
        for k in range(4):
            x += math.cos(t) * raio * 0.3 + math.sin(relogio * 3 + i + k) * 3
            y += raio * 0.12
            pts.append((x, y))
        for p, q in zip(pts, pts[1:], strict=False):
            r.draw_ui_line(p[0], p[1], q[0], q[1], CARNE_ABISMO_2, 7)
            r.draw_ui_line(p[0], p[1], q[0], q[1], CARNE_ABISMO, 4)
    cy = sy - h * 0.6
    cabeca = elipse(sx, cy, raio * 1.0, h * 0.4)
    r.draw_ui_polygon(cabeca, TINTA if ferido else CARNE_ABISMO)
    r.draw_ui_polygon(cabeca, CARNE_ABISMO_2, 2)
    for k in (0.15, 0.5):
        ex, ey = sx + lado * raio * k, cy + h * 0.05
        r.draw_ui_circle(ex, ey, raio * 0.13, (240, 230, 200, 255))
        r.draw_ui_circle(ex + lado * 2, ey, raio * 0.06, PRETO)
    r.draw_ui_polygon(
        elipse(sx + lado * raio * 0.35, cy + h * 0.22, raio * 0.3, raio * 0.12), (200, 70, 80, 255)
    )
    return cy - h * 0.4 - raio * 0.3


DESENHOS_CHEFE = {
    "vulcao": chefe_vulcao,
    "remendos": chefe_remendos,
    "rei": chefe_rei,
    "abismo": chefe_abismo,
    "abismo_final": chefe_abismo,  # sem sprite, a forma final cai na inicial
}


def desenhar_chefe(visual, r, sx, sy, raio, relogio, olhar, **kw) -> float:
    """O sprite pintado, se carregado (`sprites.py`); senão, o desenho por primitivas."""
    sombra(r, sx, sy, raio * 1.3)
    topo = sprites.desenhar(
        r,
        visual,
        sx,
        sy,
        relogio,
        _lado(olhar),
        flash=kw.get("ferido", False),
        alpha=150 if kw.get("queimado") else 255,
    )
    if topo is not None:
        return topo
    return DESENHOS_CHEFE.get(visual, chefe_vulcao)(r, sx, sy, raio, relogio, olhar, **kw)
