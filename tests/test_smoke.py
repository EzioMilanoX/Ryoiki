"""Smoke test: a importação funciona e o loop roda headless sem travar."""

import os


def test_import():
    import ryoiki

    assert ryoiki.__version__


def test_run_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from ryoiki.game import run

    run(headless=True)  # não deve lançar
