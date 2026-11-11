"""Gera os sprites dos chefes (`ryoiki/data/sprites/`): 8 quadros de animação parada por
chefe, cada um com a versão branca (o clarão de quando apanha), e `sprites.json`.

Como a arte é feita (para dar qualidade sem desenhista):
- tudo é pintado em 4x (`S`) e reduzido com `smoothscale`: as bordas saem lisas;
- cada peça (`Pintor.parte`) ganha **contorno** grosso, **sombra** própria (a faixa do
  lado oposto à luz, por máscara deslocada) e **brilho** (a faixa do lado da luz), em três
  tons tirados da cor base (sombra puxada para o roxo, brilho para o creme);
- luzes (lava, olhos, aura) vão numa camada **aditiva** borrada (reduz e amplia de novo).

Os chefes olham para a direita; o jogo espelha. Rodar: python tools/gerar_sprites.py
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

PASTA = Path(__file__).resolve().parent.parent / "ryoiki" / "data" / "sprites"
S = 4  # o super-amostragem
QUADROS = 8
LUZ = (-1.0, -1.2)  # a luz vem de cima, à esquerda (a frente olha para a direita)
CONTORNO = (18, 12, 22)


def mistura(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1[:3], c2[:3], strict=False))


def tons(base):
    """(base, sombra, brilho): a sombra puxa para o roxo frio, o brilho para o creme."""
    return base, mistura(base, (34, 20, 58), 0.5), mistura(base, (255, 244, 224), 0.38)


class Pintor:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.tela = pygame.Surface((w * S, h * S), pygame.SRCALPHA)
        self.luzes = pygame.Surface((w * S, h * S), pygame.SRCALPHA)

    # -- formas, em unidades de 1x (o pintor multiplica por S)
    def _novo(self):
        return pygame.Surface(self.tela.get_size(), pygame.SRCALPHA)

    def poligono(self, pts):
        return lambda s: pygame.draw.polygon(s, (255, 255, 255), [(x * S, y * S) for x, y in pts])

    def elipse(self, cx, cy, rx, ry):
        return lambda s: pygame.draw.ellipse(
            s, (255, 255, 255), pygame.Rect((cx - rx) * S, (cy - ry) * S, 2 * rx * S, 2 * ry * S)
        )

    def capsula(self, p1, p2, larg):
        def f(s):
            a, b = (p1[0] * S, p1[1] * S), (p2[0] * S, p2[1] * S)
            pygame.draw.line(s, (255, 255, 255), a, b, int(larg * S))
            for p in (a, b):
                pygame.draw.circle(s, (255, 255, 255), p, larg * S / 2)

        return f

    def uniao(self, *formas):
        def f(s):
            for forma in formas:
                forma(s)

        return f

    # -- pintura
    def parte(self, forma, base, *, contorno=2.2, sombra=0.32, brilho=0.12, tamanho=20):
        """Uma peça com contorno, sombra própria e brilho. `tamanho` (1x) gradua as faixas."""
        cor, cor_sombra, cor_brilho = tons(base)
        tmp = self._novo()
        forma(tmp)
        m = pygame.mask.from_surface(tmp)
        sil = m.to_surface(setcolor=(*CONTORNO, 255), unsetcolor=(0, 0, 0, 0))
        r = contorno * S
        for i in range(12):  # o contorno: a silhueta carimbada em volta
            a = 2 * math.pi * i / 12
            self.tela.blit(sil, (math.cos(a) * r, math.sin(a) * r))
        self.tela.blit(m.to_surface(setcolor=(*cor, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
        n = math.hypot(*LUZ)
        lx, ly = LUZ[0] / n, LUZ[1] / n
        d = tamanho * sombra * S
        faixa = m.copy()  # sombra: o que sobra longe da luz
        faixa.erase(m, (int(lx * d), int(ly * d)))
        self.tela.blit(
            faixa.to_surface(setcolor=(*cor_sombra, 255), unsetcolor=(0, 0, 0, 0)), (0, 0)
        )
        d = tamanho * brilho * S
        faixa = m.copy()  # brilho: a beira virada para a luz
        faixa.erase(m, (int(-lx * d), int(-ly * d)))
        self.tela.blit(
            faixa.to_surface(setcolor=(*cor_brilho, 255), unsetcolor=(0, 0, 0, 0)), (0, 0)
        )
        return m

    def linha(self, p1, p2, cor, larg=1.0):
        pygame.draw.line(
            self.tela, cor, (p1[0] * S, p1[1] * S), (p2[0] * S, p2[1] * S), int(larg * S)
        )

    def ponto(self, p, raio, cor):
        pygame.draw.circle(self.tela, cor, (p[0] * S, p[1] * S), raio * S)

    def luz(self, p, raio, cor, forca=1.0):
        """Um ponto de luz aditivo (vai borrado no fim)."""
        for i in range(6):
            k = 1 - i / 6
            pygame.draw.circle(
                self.luzes,
                (*[min(255, int(c * forca * (0.25 + 0.75 * (1 - k)))) for c in cor], 255),
                (p[0] * S, p[1] * S),
                raio * S * k,
            )

    def terminar(self) -> pygame.Surface:
        w, h = self.w, self.h
        final = pygame.transform.smoothscale(self.tela, (w, h))
        borrada = pygame.transform.smoothscale(self.luzes, (max(1, w // 4), max(1, h // 4)))
        borrada = pygame.transform.smoothscale(borrada, (w, h))
        final.blit(borrada, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        nitida = pygame.transform.smoothscale(self.luzes, (w, h))
        final.blit(nitida, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return final


# ======================================================================== os chefes


def jogo(t: float) -> Pintor:
    """Jogo: baixo e largo, pele de rocha cinza, manto creme com faixa escura; a cabeça é
    um vulcão com a cratera acesa, lava escorrendo e um olho só."""
    p = Pintor(150, 150)
    cx, pe = 72, 144
    resp = math.sin(t * 2 * math.pi) * 1.2  # a respiração
    pele = (104, 96, 100)
    for k in (-1, 1):  # as pernas
        p.parte(p.capsula((cx + k * 12, pe - 30), (cx + k * 14, pe - 5), 13), pele, tamanho=14)
        p.parte(p.elipse(cx + k * 14 + 4, pe - 3, 10, 5), (60, 52, 56), tamanho=8)
    p.parte(
        p.capsula((cx - 34, pe - 70 + resp), (cx - 40, pe - 44), 14), pele, tamanho=14
    )  # braço de trás
    p.parte(p.elipse(cx, pe - 52 + resp, 32, 26 - resp * 0.5), pele, tamanho=40)  # o tronco
    for i in range(5):  # as placas de rocha do peito
        x = cx - 22 + i * 10
        p.linha((x, pe - 70 + resp + abs(i - 2) * 2), (x + 4, pe - 58 + resp), (74, 66, 70), 1.3)
    tanga = [
        (cx - 28, pe - 34),
        (cx + 28, pe - 38),
        (cx + 22, pe - 16),
        (cx + 4, pe - 12),
        (cx - 24, pe - 16),
    ]
    p.parte(p.poligono(tanga), (214, 196, 160), tamanho=18)
    for i in range(3):
        p.linha((cx - 14 + i * 12, pe - 30), (cx - 12 + i * 12, pe - 16), (170, 150, 116), 1.0)
    faixa = [
        (cx - 26, pe - 68 + resp),
        (cx - 14, pe - 76 + resp),
        (cx + 30, pe - 38),
        (cx + 18, pe - 32),
    ]
    p.parte(p.poligono(faixa), (226, 210, 176), tamanho=12)
    p.parte(
        p.poligono(
            [(cx - 30, pe - 40), (cx + 30, pe - 44), (cx + 30, pe - 36), (cx - 30, pe - 32)]
        ),
        (88, 40, 46),
        tamanho=8,
    )
    base, topo = pe - 72 + resp, pe - 128 + resp  # a cabeça-vulcão
    cone = [
        (cx - 26, base),
        (cx + 26, base),
        (cx + 14, topo + 6),
        (cx + 8, topo),
        (cx - 8, topo),
        (cx - 14, topo + 6),
    ]
    p.parte(p.poligono(cone), pele, tamanho=34)
    for k in (-1, 1):
        p.linha((cx + k * 6, topo + 10), (cx + k * 12, base - 10), (72, 64, 68), 1.4)
    pulso = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 2)
    p.parte(p.elipse(cx, topo + 2, 12, 4.5), (52, 26, 22), contorno=1.5, tamanho=6)
    p.ponto((cx, topo + 2), 9, (255, 120 + int(40 * pulso), 30))
    p.ponto((cx, topo + 1.5), 5, (255, 220, 140))
    for i, (dx, comp) in enumerate(((-7, 18), (2, 26), (9, 14))):  # a lava escorrendo
        fim = (cx + dx * 1.4, topo + 6 + comp + 3 * math.sin(t * 6.28 + i))
        p.linha((cx + dx, topo + 4), fim, (255, 110, 30), 2.4)
        p.ponto(fim, 1.6, (255, 160, 60))
        p.luz(fim, 6, (255, 90, 20), 0.5)
    p.luz((cx, topo + 2), 16, (255, 100, 25), 0.8 + 0.3 * pulso)
    ey = base - 26  # o olho, grande, na frente
    p.parte(p.elipse(cx + 10, ey, 9, 6.5), (238, 230, 214), contorno=1.6, tamanho=8)
    p.ponto((cx + 14, ey + 0.5), 3.2, (20, 14, 18))
    p.ponto((cx + 13, ey - 1.5), 1, (255, 255, 255))
    p.linha((cx + 1, ey - 9), (cx + 20, ey - 7), (60, 52, 56), 2.2)  # a sobrancelha pesada
    p.parte(
        p.capsula((cx + 30, pe - 70 + resp), (cx + 40, pe - 46), 14), pele, tamanho=14
    )  # braço da frente
    p.parte(p.elipse(cx + 41, pe - 42, 8, 8), (86, 78, 82), tamanho=10)
    for i in range(3):  # a fumaça
        k = (t + i / 3) % 1
        y = topo - 16 - k * 22
        x = cx - 4 + math.sin(t * 6.28 + i * 2) * 5
        pygame.draw.circle(
            p.tela, (70, 66, 72, int(190 * (1 - k))), (x * S, y * S), (4 + 7 * k) * S
        )
    return p


def mahito(t: float) -> Pintor:
    """Mahito: alto e esguio, pele azul-acinzentada de retalhos costurados, cabelo comprido
    caindo para trás, casaco escuro aberto; o braço da frente vira uma lâmina."""
    p = Pintor(150, 160)
    cx, pe = 66, 154
    bal = math.sin(t * 2 * math.pi)
    pele, pele2 = (176, 198, 214), (138, 162, 186)
    roupa = (40, 44, 60)
    for i in range(5):  # o cabelo: mechas finas, caindo para trás
        x0 = cx - 2 - i * 3
        y_fim = pe - 70 + i * 7 + bal * 2
        p.parte(
            p.capsula((x0, pe - 128), (x0 - 10 - i * 3 + bal * 2, y_fim), 4),
            (104, 132, 168),
            contorno=1.2,
            tamanho=6,
        )
    for k, fase in ((-1, bal), (1, -bal)):  # as pernas
        p.parte(
            p.capsula((cx + k * 7, pe - 58), (cx + k * 8 + fase * 2, pe - 6), 10), roupa, tamanho=12
        )
        p.parte(p.elipse(cx + k * 8 + fase * 2 + 4, pe - 3, 8, 4), (20, 18, 24), tamanho=6)
    p.parte(
        p.capsula((cx - 14, pe - 102), (cx - 22, pe - 66 + bal), 8), pele2, tamanho=10
    )  # braço de trás
    p.parte(
        p.poligono(
            [(cx - 16, pe - 106), (cx + 16, pe - 106), (cx + 12, pe - 56), (cx - 12, pe - 56)]
        ),
        pele,
        tamanho=30,
    )
    for y0 in (pe - 96, pe - 78):  # as costuras do peito
        p.linha((cx - 10, y0), (cx + 10, y0 + 4), (60, 46, 70), 1.2)
        for i in range(5):
            x = cx - 8 + i * 4
            p.linha((x, y0 - 1.5 + i * 0.8), (x, y0 + 2.5 + i * 0.8), (60, 46, 70), 0.8)
    casaco = [(cx - 18, pe - 108), (cx - 6, pe - 104), (cx - 8, pe - 50), (cx - 20, pe - 48)]
    p.parte(p.poligono(casaco), roupa, tamanho=14)
    p.parte(
        p.poligono(
            [(cx + 18, pe - 108), (cx + 8, pe - 104), (cx + 10, pe - 50), (cx + 20, pe - 48)]
        ),
        roupa,
        tamanho=14,
    )
    p.parte(p.capsula((cx, pe - 112), (cx + 1, pe - 104), 8), pele, tamanho=8)  # o pescoço
    hx, hy = cx + 2, pe - 124
    p.parte(p.elipse(hx, hy, 12, 13), pele, tamanho=20)
    p.parte(
        p.poligono(
            [
                (hx - 13, hy - 2),
                (hx - 8, hy - 16),
                (hx + 6, hy - 15),
                (hx + 13, hy - 6),
                (hx + 2, hy - 9),
                (hx - 6, hy - 4),
            ]
        ),
        (88, 112, 146),
        contorno=1.6,
        tamanho=10,
    )
    p.linha((hx - 10, hy - 6), (hx + 10, hy + 8), (60, 46, 70), 1.4)  # a costura que corta o rosto
    for i in range(5):
        x = hx - 8 + i * 4
        y = hy - 5 + i * 3.2
        p.linha((x - 1.5, y + 1.5), (x + 1.5, y - 1.5), (60, 46, 70), 0.8)
    p.ponto((hx + 6, hy - 2), 1.8, (60, 150, 170))
    p.ponto((hx + 11, hy - 1), 1.6, (210, 220, 230))
    p.linha((hx + 3, hy + 6), (hx + 11, hy + 5), (70, 40, 60), 1.2)  # o sorriso
    k = 1 + 0.06 * math.sin(t * 2 * math.pi * 2)  # a lâmina pulsa
    ombro = (cx + 14, pe - 100)
    lamina = [
        (ombro[0] - 4, ombro[1] + 2),
        (ombro[0] + 30 * k, ombro[1] + 10),
        (ombro[0] + 70 * k, ombro[1] + 6 + bal * 2),
        (ombro[0] + 32 * k, ombro[1] + 18),
        (ombro[0] + 2, ombro[1] + 12),
    ]
    p.parte(p.poligono(lamina), pele2, tamanho=14)
    p.linha(
        (ombro[0] + 8, ombro[1] + 6),
        (ombro[0] + 66 * k, ombro[1] + 7 + bal * 2),
        (236, 244, 250),
        1.2,
    )
    p.luz((ombro[0] + 60 * k, ombro[1] + 7), 6, (120, 170, 210), 0.5)
    return p


def sukuna(t: float) -> Pintor:
    """Sukuna: quimono branco que abre embaixo, com faixa vinho e barra escura; quatro
    braços (os de cima saem de mangas largas, os de baixo nus, com as faixas tatuadas);
    cabelo rosa cheio de pontas, dois pares de olhos vermelhos, marcas e um sorriso torto."""
    p = Pintor(170, 170)
    cx, pe = 80, 164
    bal = math.sin(t * 2 * math.pi)
    pele, branco = (232, 204, 186), (238, 234, 226)
    tinta = (24, 14, 20)
    for i in range(5):  # a névoa vermelha nos pés
        p.luz((cx - 30 + i * 15, pe - 4), 14, (200, 20, 40), 0.3)

    def antebraco(cotovelo, mao):
        p.parte(p.capsula(cotovelo, mao, 10), pele, tamanho=12)
        for k in (0.35, 0.65):  # as faixas tatuadas
            x = cotovelo[0] + (mao[0] - cotovelo[0]) * k
            y = cotovelo[1] + (mao[1] - cotovelo[1]) * k
            p.linha((x - 1, y - 4.5), (x + 1, y + 4.5), tinta, 2.2)
        p.parte(p.elipse(mao[0], mao[1], 6.5, 6), pele, contorno=1.8, tamanho=8)
        p.linha((mao[0] + 2, mao[1] - 3), (mao[0] + 6, mao[1] - 1), tinta, 1.0)

    def manga(ombro, cotovelo):
        larga = [
            (ombro[0] - 9, ombro[1] - 4),
            (ombro[0] + 9, ombro[1] - 4),
            (cotovelo[0] + 10, cotovelo[1] + 4),
            (cotovelo[0] + 4, cotovelo[1] + 22),
            (cotovelo[0] - 12, cotovelo[1] + 16),
        ]
        p.parte(p.poligono(larga), branco, tamanho=20)

    # os braços de trás (um de manga, um nu)
    antebraco((cx - 30, pe - 92 + bal), (cx - 46, pe - 72 + bal))
    manga((cx - 16, pe - 114), (cx - 30, pe - 92 + bal))
    antebraco((cx - 20, pe - 80), (cx - 40, pe - 56 - bal))
    quimono = [
        (cx - 20, pe - 118),
        (cx + 20, pe - 118),
        (cx + 26, pe - 60),
        (cx + 36, pe - 6),
        (cx + 26 + bal, pe - 1),
        (cx - 28 + bal, pe - 1),
        (cx - 36, pe - 6),
        (cx - 26, pe - 60),
    ]
    p.parte(p.poligono(quimono), branco, tamanho=48)
    barra = [
        (cx - 36, pe - 14),
        (cx + 36, pe - 14),
        (cx + 36 + bal * 0.3, pe - 4),
        (cx - 36 + bal * 0.3, pe - 4),
    ]
    p.parte(p.poligono(barra), (60, 34, 44), contorno=1.4, tamanho=6)
    p.linha((cx - 9, pe - 118), (cx + 9, pe - 74), (110, 100, 104), 1.6)  # a gola cruzada
    p.linha((cx + 9, pe - 74), (cx + 4, pe - 14), (186, 178, 172), 1.0)
    obi = [(cx - 26, pe - 78), (cx + 26, pe - 80), (cx + 27, pe - 66), (cx - 27, pe - 64)]
    p.parte(p.poligono(obi), (118, 26, 42), tamanho=8)
    ponta = [
        (cx + 14, pe - 66),
        (cx + 20, pe - 66),
        (cx + 26 + bal, pe - 44),
        (cx + 18 + bal, pe - 44),
    ]
    p.parte(p.poligono(ponta), (118, 26, 42), contorno=1.4, tamanho=5)
    p.parte(p.capsula((cx + 2, pe - 126), (cx + 2, pe - 116), 10), pele, tamanho=8)
    hx, hy = cx + 4, pe - 137
    espetos = []
    for i in range(17):  # o cabelo rosa, cheio de pontas
        a = math.pi * (0.8 + 1.35 * i / 16)
        rr = 21 if i % 2 else 13
        espetos.append((hx - 3 + math.cos(a) * rr, hy - 4 + math.sin(a) * rr))
    espetos += [(hx + 12, hy - 2), (hx - 3, hy)]
    p.parte(p.elipse(hx, hy, 12.5, 13.5), pele, tamanho=20)
    p.parte(p.poligono(espetos), (244, 152, 172), contorno=1.8, tamanho=18)
    for dy in (-1.5, 4.5):  # dois pares de olhos (o de baixo, a marca)
        p.parte(p.elipse(hx + 7, hy + dy, 2.6, 1.6), (250, 230, 220), contorno=0.8, tamanho=2)
        p.ponto((hx + 8, hy + dy), 1.2, (210, 20, 40))
        p.luz((hx + 8, hy + dy), 3, (255, 40, 60), 0.6)
    p.linha((hx - 4, hy + 2), (hx + 2, hy + 8), tinta, 1.4)  # as marcas no rosto
    p.linha((hx + 3, hy - 9), (hx + 12, hy - 7), tinta, 1.2)
    p.linha((hx - 2, hy + 10), (hx + 4, hy + 13), tinta, 1.2)
    sorriso = [(hx + 3, hy + 9), (hx + 12, hy + 8), (hx + 10, hy + 11)]
    p.parte(p.poligono(sorriso), (90, 20, 30), contorno=0.8, tamanho=2)
    p.linha((hx + 4, hy + 9.2), (hx + 11, hy + 8.4), (240, 236, 230), 0.8)
    # os braços da frente (um de manga, um nu)
    antebraco((cx + 32, pe - 94 - bal), (cx + 50, pe - 78 - bal))
    manga((cx + 16, pe - 114), (cx + 32, pe - 94 - bal))
    antebraco((cx + 22, pe - 80), (cx + 44, pe - 58 + bal))
    return p


def dagon(t: float) -> Pintor:
    """Dagon, forma inicial: um útero amaldiçoado. Cabeça bulbosa enrugada e úmida, cor de
    carne doente, olhos pequenos e vazios afundados, uma boca grande entreaberta com dentes
    e baba; tentáculos grossos com ventosas e uma poça embaixo."""
    p = Pintor(160, 140)
    cx, pe = 78, 134
    bal = math.sin(t * 2 * math.pi)
    carne = (122, 60, 58)
    pygame.draw.ellipse(
        p.tela, (40, 120, 140, 110), pygame.Rect((cx - 58) * S, (pe - 10) * S, 116 * S, 16 * S)
    )
    for i in range(8):  # os tentáculos, grossos, de trás para a frente
        a = math.pi * (1.05 - 1.1 * i / 7)
        pts = [(cx + math.cos(a) * 18, pe - 30)]
        x, y = pts[0]
        for k in range(5):
            onda = math.sin(t * 2 * math.pi + i * 0.8 + k * 0.9) * 3
            x += math.cos(a) * 9 + onda
            y += 4.6 - k * 0.5
            pts.append((x, y))
        forma = p.uniao(*[p.capsula(pts[j], pts[j + 1], 12 - j * 1.8) for j in range(5)])
        p.parte(forma, mistura(carne, (84, 36, 40), 0.3), contorno=1.8, tamanho=12)
        for j in range(1, 5):
            p.ponto((pts[j][0], pts[j][1] + 2), 1.6 - j * 0.15, (196, 150, 140))
    cy = pe - 62 + bal * 1.5
    p.parte(p.elipse(cx, cy, 38, 35 + bal * 0.6), carne, tamanho=64)
    for i in range(5):  # as rugas, em arco
        r0 = 12 + i * 5
        pygame.draw.arc(
            p.tela,
            (84, 38, 40),
            pygame.Rect((cx - 6 - r0) * S, (cy - 30 - i) * S, 2 * r0 * S, 20 * S),
            0.4,
            2.7,
            int(1.4 * S),
        )
    for sx, sy, r in (
        (-18, -10, 3.4),
        (12, -22, 2.6),
        (-26, 8, 2.2),
        (22, -6, 3),
        (-4, -26, 2.2),
        (6, 2, 1.8),
    ):
        p.ponto((cx + sx, cy + sy), r, mistura(carne, (62, 22, 30), 0.5))
    brilho = pygame.Surface((18 * S, 8 * S), pygame.SRCALPHA)
    pygame.draw.ellipse(brilho, (255, 236, 226, 120), brilho.get_rect())
    p.tela.blit(brilho, ((cx - 24) * S, (cy - 28) * S))  # a umidade
    for dx in (6, 20):  # os olhos: fundos, pretos, com um reflexo frio
        p.parte(p.elipse(cx + dx, cy - 4, 4.2, 3.2), (40, 18, 24), contorno=1.2, tamanho=4)
        p.ponto((cx + dx + 1.2, cy - 5), 0.9, (170, 220, 230))
        p.luz((cx + dx, cy - 4), 3, (60, 160, 190), 0.35)
    boca = [(cx + 4, cy + 12), (cx + 34, cy + 9), (cx + 32, cy + 22), (cx + 8, cy + 24)]
    p.parte(p.poligono(boca), (196, 60, 74), contorno=1.8, tamanho=10)
    p.parte(
        p.poligono([(cx + 8, cy + 15), (cx + 30, cy + 13), (cx + 28, cy + 19), (cx + 10, cy + 20)]),
        (38, 10, 18),
        contorno=0.6,
        tamanho=3,
    )
    for i in range(5):  # os dentes
        x = cx + 10 + i * 4
        pygame.draw.polygon(
            p.tela,
            (236, 226, 206),
            [
                ((x) * S, (cy + 14.5) * S),
                ((x + 2.6) * S, (cy + 14.2) * S),
                ((x + 1.3) * S, (cy + 17.5) * S),
            ],
        )
    gota = cy + 22 + (t * 14) % 10  # a baba escorrendo
    p.linha((cx + 24, cy + 21), (cx + 24.5, gota), (200, 220, 230), 1.2)
    p.ponto((cx + 24.5, gota), 1.4, (210, 230, 240))
    return p


def dagon_final(t: float) -> Pintor:
    """Dagon, forma final: corpo humanoide alto e musculoso, cabeça de polvo alongada com
    tentáculos caindo sobre a boca e o peito, olhos frios acesos, braços longos com mãos de
    nadadeira e água subindo em volta dos pés."""
    p = Pintor(170, 190)
    cx, pe = 80, 184
    bal = math.sin(t * 2 * math.pi)
    pele, pele2 = (150, 70, 60), (112, 50, 48)
    for i in range(6):  # a água subindo em volta dos pés
        k = (t + i / 6) % 1
        x = cx - 36 + i * 14
        p.luz((x, pe - 4 - k * 20), 7, (40, 160, 190), 0.45 * (1 - k))
    pygame.draw.ellipse(
        p.tela, (40, 140, 170, 120), pygame.Rect((cx - 50) * S, (pe - 9) * S, 100 * S, 14 * S)
    )
    for k, fase in ((-1, bal), (1, -bal)):  # as pernas
        p.parte(
            p.capsula((cx + k * 10, pe - 76), (cx + k * 14 + fase * 2, pe - 40), 19),
            pele2,
            tamanho=18,
        )
        p.parte(
            p.capsula((cx + k * 14 + fase * 2, pe - 40), (cx + k * 12, pe - 8), 12),
            pele2,
            tamanho=14,
        )
        p.parte(
            p.poligono(
                [
                    (cx + k * 12 - 7, pe - 10),
                    (cx + k * 12 + 12, pe - 8),
                    (cx + k * 12 + 16, pe - 2),
                    (cx + k * 12 - 8, pe - 2),
                ]
            ),
            (90, 40, 40),
            contorno=1.6,
            tamanho=6,
        )

    def braco(ombro, frente):
        s = 1 if frente else -1
        cotovelo = (ombro[0] + s * 16, ombro[1] + 26 + bal * 2)
        mao = (cotovelo[0] + s * 4, cotovelo[1] + 28 - bal * 2)
        p.parte(p.capsula(ombro, cotovelo, 15), pele, tamanho=16)
        p.parte(p.elipse(ombro[0] + s * 2, ombro[1] + 2, 12, 11), pele, tamanho=14)  # o deltoide
        p.parte(p.capsula(cotovelo, mao, 11), pele, tamanho=12)
        dedos = [
            (mao[0] - 7, mao[1] - 2),
            (mao[0] + 7, mao[1] - 2),
            (mao[0] + 10 * s, mao[1] + 12),
            (mao[0], mao[1] + 16),
            (mao[0] - 9 * s, mao[1] + 11),
        ]
        p.parte(p.poligono(dedos), mistura(pele, (60, 140, 150), 0.25), contorno=1.6, tamanho=8)
        for j in (-1, 1):
            p.linha((mao[0], mao[1] + 1), (mao[0] + j * 5, mao[1] + 12), pele2, 1.0)

    braco((cx - 24, pe - 128), False)
    tronco = [
        (cx - 34, pe - 134),
        (cx - 20, pe - 142),
        (cx + 20, pe - 142),
        (cx + 34, pe - 134),
        (cx + 26, pe - 108),
        (cx + 16, pe - 74),
        (cx - 16, pe - 74),
        (cx - 26, pe - 108),
    ]
    p.parte(p.poligono(tronco), pele, tamanho=40)
    for k in (-1, 1):  # o peitoral
        p.parte(
            p.elipse(cx + k * 12, pe - 124, 13, 9),
            mistura(pele, pele2, 0.25),
            contorno=1.4,
            tamanho=10,
        )
    for i in range(3):
        p.linha((cx - 8, pe - 104 + i * 9), (cx + 8, pe - 104 + i * 9), pele2, 1.2)
    p.linha((cx, pe - 110), (cx, pe - 76), pele2, 1.2)
    p.parte(
        p.poligono(
            [(cx - 18, pe - 76), (cx + 18, pe - 76), (cx + 14, pe - 58), (cx - 14, pe - 58)]
        ),
        (46, 40, 56),
        contorno=1.6,
        tamanho=10,
    )
    hx, hy = cx + 2, pe - 152
    p.parte(p.elipse(hx - 2, hy - 8, 17, 24), pele, tamanho=34)  # a cabeça alongada
    for i, (dx, comp) in enumerate(
        ((-10, 26), (-4, 34), (2, 38), (8, 32), (14, 24))
    ):  # tentáculos da boca
        onda = math.sin(t * 2 * math.pi + i) * 3
        pts = [
            (hx + dx, hy + 6),
            (hx + dx + onda, hy + 6 + comp * 0.5),
            (hx + dx - onda * 0.6 + 2, hy + 6 + comp),
        ]
        forma = p.uniao(p.capsula(pts[0], pts[1], 6), p.capsula(pts[1], pts[2], 4))
        p.parte(forma, mistura(pele, (90, 40, 44), 0.25), contorno=1.4, tamanho=6)
        p.ponto((pts[2][0], pts[2][1]), 1.4, (200, 150, 140))
    for sx, sy in ((-8, -22), (6, -26), (-2, -12)):
        p.ponto((hx + sx, hy + sy), 2, pele2)
    for dx in (3, 13):  # os olhos frios
        p.parte(p.elipse(hx + dx, hy - 6, 3.6, 2.6), (14, 20, 26), contorno=1.0, tamanho=3)
        p.ponto((hx + dx + 0.6, hy - 6), 1.4, (120, 230, 240))
        p.luz((hx + dx, hy - 6), 5, (60, 200, 230), 0.7)
    brilho = pygame.Surface((10 * S, 16 * S), pygame.SRCALPHA)
    pygame.draw.ellipse(brilho, (255, 236, 226, 110), brilho.get_rect())
    p.tela.blit(brilho, ((hx - 14) * S, (hy - 28) * S))
    braco((cx + 24, pe - 128), True)
    return p


CHEFES = {
    "vulcao": jogo,
    "remendos": mahito,
    "rei": sukuna,
    "abismo": dagon,
    "abismo_final": dagon_final,
}


def main() -> None:
    pygame.init()
    PASTA.mkdir(parents=True, exist_ok=True)
    catalogo = {}
    for nome, desenho in CHEFES.items():
        topo = None
        for q in range(QUADROS):
            p = desenho(q / QUADROS)
            img = p.terminar()
            pygame.image.save(img, str(PASTA / f"{nome}_{q}.png"))
            mascara = pygame.mask.from_surface(img, 40)
            branca = mascara.to_surface(setcolor=(255, 255, 255, 235), unsetcolor=(0, 0, 0, 0))
            pygame.image.save(branca, str(PASTA / f"{nome}_flash_{q}.png"))
            caixa = mascara.get_bounding_rects()
            if caixa:
                topo = min(topo if topo is not None else 9999, min(c.top for c in caixa))
        catalogo[nome] = {
            "quadros": QUADROS,
            "fps": 8,
            "largura": p.w,
            "altura": p.h,
            "pes": [p.w * 0.48, p.h - 4],
            "topo": topo or 0,
        }
    (PASTA / "sprites.json").write_text(json.dumps(catalogo, indent=2) + "\n", encoding="utf-8")
    print("sprites em", PASTA)


if __name__ == "__main__":
    main()
