"""Os sprites pintados dos chefes (gerados por `tools/gerar_sprites.py`).

`carregar(renderer)` registra os PNGs como texturas (uma vez, ao abrir o jogo) e preenche
`CATALOGO`. Sem isso (testes, ou se os arquivos sumirem), `figuras` cai no desenho por
primitivas: o jogo nunca depende de os sprites existirem.
"""

from __future__ import annotations

import json

from ryoiki.movimento import DADOS

PASTA = DADOS / "sprites"
BASE_ID = 5000  # os ids de textura dos sprites (longe dos da engine)

CATALOGO: dict[str, dict] = {}


def carregar(renderer) -> int:
    """Registra todos os quadros. Devolve quantos chefes ficaram com sprite."""
    CATALOGO.clear()
    manifesto = PASTA / "sprites.json"
    if not manifesto.exists():
        return 0
    dados = json.loads(manifesto.read_text(encoding="utf-8"))
    for i, (nome, info) in enumerate(sorted(dados.items())):
        ids, flashes = [], []
        for q in range(info["quadros"]):
            tid, fid = BASE_ID + i * 100 + q, BASE_ID + i * 100 + 50 + q
            try:
                renderer.load_texture(tid, str(PASTA / f"{nome}_{q}.png"))
                renderer.load_texture(fid, str(PASTA / f"{nome}_flash_{q}.png"))
            except Exception:  # noqa: BLE001 — sem o arquivo, este chefe fica no procedural
                break
            ids.append(tid)
            flashes.append(fid)
        else:
            CATALOGO[nome] = {**info, "ids": ids, "flashes": flashes}
    return len(CATALOGO)


def desenhar(r, visual: str, sx, sy, relogio, lado: int, *, flash=False, alpha=255):
    """Desenha o quadro da vez com os pés em (sx, sy). Devolve o y do topo, ou None se esse
    chefe não tem sprite (aí quem chamou desenha por primitivas)."""
    info = CATALOGO.get(visual)
    if info is None:
        return None
    q = int(relogio * info["fps"]) % info["quadros"]
    w, h = info["largura"], info["altura"]
    ancora = (info["pes"][0] / w, info["pes"][1] / h)
    flip = lado < 0
    if flip:
        ancora = (1 - ancora[0], ancora[1])
    r.draw_ui_image(info["ids"][q], sx, sy, anchor=ancora, flip_x=flip, alpha=alpha)
    if flash:
        r.draw_ui_image(info["flashes"][q], sx, sy, anchor=ancora, flip_x=flip, alpha=200)
    return sy - (info["pes"][1] - info["topo"])
