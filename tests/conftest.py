"""Os testes nunca leem nem gravam a técnica própria de verdade do jogador."""

import pytest


@pytest.fixture(autouse=True)
def _pasta_do_jogador_isolada(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
