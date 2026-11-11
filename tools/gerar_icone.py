"""Gera o ícone do jogo (atalho e janela): `ryoiki/data/icone.png` e `icone.ico`.

Um selo de domínio: disco escuro, anel duplo vermelho com marcas, e 領 em pincel no meio.
Rodar: python tools/gerar_icone.py
"""

from __future__ import annotations

import math
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

DADOS = Path(__file__).resolve().parent.parent / "ryoiki" / "data"
LADO = 512


def desenhar() -> pygame.Surface:
    pygame.init()
    s = pygame.Surface((LADO, LADO), pygame.SRCALPHA)
    c = LADO // 2
    for i in range(40):  # o disco: do roxo do véu no centro ao preto na borda
        k = i / 39
        cor = (int(52 * (1 - k) + 8 * k), int(18 * (1 - k) + 6 * k), int(70 * (1 - k) + 12 * k))
        pygame.draw.circle(s, cor, (c, c), int(c * (1 - k * 0.55)))
    pygame.draw.circle(s, (8, 6, 12), (c, c), c - 4, 18)
    vermelho = (205, 32, 44)
    pygame.draw.circle(s, vermelho, (c, c), c - 22, 10)
    pygame.draw.circle(s, vermelho, (c, c), c - 52, 4)
    for i in range(24):  # as marcas entre os anéis, como num selo
        a = 2 * math.pi * i / 24
        r1, r2 = c - 50, c - 30 if i % 2 else c - 40
        p1 = (c + math.cos(a) * r1, c + math.sin(a) * r1)
        p2 = (c + math.cos(a) * r2, c + math.sin(a) * r2)
        pygame.draw.line(s, vermelho, p1, p2, 5)
    fonte = pygame.font.Font(str(DADOS / "fontes" / "YujiSyuku-Regular.ttf"), 300)
    sombra = fonte.render("領", True, (0, 0, 0))
    letra = fonte.render("領", True, (238, 232, 244))
    s.blit(sombra, sombra.get_rect(center=(c + 8, c + 14)))
    s.blit(letra, letra.get_rect(center=(c, c + 6)))
    return s


def main() -> None:
    s = desenhar()
    png = DADOS / "icone.png"
    pygame.image.save(s, str(png))
    img = Image.open(png)
    img.save(
        DADOS / "icone.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(png, DADOS / "icone.ico")


if __name__ == "__main__":
    main()
