"""Composição: a OuroborosEngine com o título, que empilha a arena."""

from __future__ import annotations

from ouroboros.bootstrap.composition_root import CompositionRoot
from ouroboros.bootstrap.engine_config import EngineConfig
from ouroboros.bootstrap.game_loop import GameLoop

from ryoiki.movimento import DADOS
from ryoiki.tela_arena import ALTURA, LARGURA
from ryoiki.tela_oficina import OficinaScene
from ryoiki.tela_rota import ControleRota
from ryoiki.tela_titulo import TituloScene
from ryoiki.visual import FONTE_PINCEL


def build_game() -> GameLoop:
    config = EngineConfig(
        window_width=LARGURA,
        window_height=ALTURA,
        window_title="Ryoiki",
        entity_capacity=1024,  # as maldições e os projéteis vão morar no ECS
        difficulty_path=str(DADOS / "feel.json"),
        input_bindings_path=str(DADOS / "controles.json"),
    )
    loop = CompositionRoot(config).build()
    loop.renderer.load_font(FONTE_PINCEL, str(DADOS / "fontes" / "YujiSyuku-Regular.ttf"))

    def lutar(arena) -> None:
        arena.ao_titulo = loop.pop_scene  # a pausa volta para o título
        loop.push_scene(arena)

    def oficina() -> None:
        loop.push_scene(OficinaScene(loop.input_provider, ao_voltar=loop.pop_scene))

    def rota(tecnica: str) -> None:
        ControleRota(loop.input_provider, tecnica, loop.push_scene, loop.pop_scene).comecar()

    loop.reset_scenes(
        TituloScene(loop.input_provider, lutar, ao_sair=loop.stop, ao_oficina=oficina, ao_rota=rota)
    )
    return loop


def run(headless: bool = False) -> None:
    """Abre o jogo. headless=True roda um quadro e sai (para testes)."""
    loop = build_game()
    if headless:
        loop.tick_once(1 / 60)
        loop.renderer.shutdown()
        return
    try:
        loop.run()
    finally:
        loop.renderer.shutdown()
