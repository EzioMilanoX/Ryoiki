"""O feel do passo 1: andar, esquivar e a câmera."""

import math

import pytest

from ryoiki.movimento import Camera, Corpo, Feel

F = Feel()


def andar(c, segundos, dx, dy, dt=1 / 60):
    for _ in range(round(segundos / dt)):
        c.passo(F, dt, dx, dy)


def test_a_diagonal_nao_anda_mais_rapido():
    reto, diag = Corpo(800, 500), Corpo(800, 500)
    andar(reto, 0.5, 1, 0)
    andar(diag, 0.5, 1, 1)
    assert math.hypot(diag.vx, diag.vy) <= math.hypot(reto.vx, reto.vy) + 1e-6


def test_acelera_ate_a_velocidade_e_para_com_atrito():
    c = Corpo(800, 500)
    andar(c, 0.5, 1, 0)
    assert c.vx == F.velocidade
    andar(c, 0.5, 0, 0)
    assert c.vx == 0


def test_a_esquiva_e_rapida_invencivel_e_recarrega():
    c = Corpo(800, 500)
    assert c.esquivar(F, 1, 0) and c.invencivel
    assert not c.esquivar(F, 1, 0)  # no meio dela, não
    x0 = c.x
    andar(c, F.esquiva_duracao, 0, 0)
    assert c.x - x0 > F.esquiva_velocidade * F.esquiva_duracao * 0.8
    andar(c, F.esquiva_recarga + 0.05, 0, 0)
    assert not c.invencivel and c.esquivar(F, -1, 0)


def test_parado_a_esquiva_vai_para_a_mira():
    c = Corpo(800, 500)
    c.mirar(800, 100)
    c.esquivar(F, 0, 0)
    assert c.dir_esquiva == (0.0, -1.0)


def test_nao_sai_da_arena():
    c = Corpo(20, 20)
    andar(c, 1.0, -1, -1)
    assert (c.x, c.y) == (c.raio, c.raio)


def test_a_camera_segue_e_nao_mostra_fora_da_arena():
    c, cam = Corpo(800, 500), Camera(800, 500)
    andar(c, 1.0, 1, 0)
    for _ in range(120):
        cam.seguir(F, c, c.x, c.y, 1 / 60)
    assert abs(cam.x - c.x) < 5
    c.x = 0
    for _ in range(300):
        cam.seguir(F, c, 0, c.y, 1 / 60)
    assert cam.x == 480  # meia tela: a borda da arena encosta na borda da tela
    assert cam.tela_de(*cam.mundo_de(100, 200)) == pytest.approx((100, 200))


def test_o_feel_vem_do_json():
    assert Feel.carregar().arena == (1600.0, 1000.0)
