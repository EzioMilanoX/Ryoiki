"""A arena (v0, passos 2–5): andar, esquivar, golpear em combo, reforçar, acertar o
Kokusen, usar a técnica (blocos em JSON), curar com a Técnica Reversa e segurar golpes com
o reforço, contra a maldição chefe (padrões avisados e um domínio que dá para interromper), e o seu
Domínio, com choque de domínios e Domínio Simples.
O hitstop congela o mundo no impacto.

Desenho em `visual.py`; regras em `movimento.py`, `combate.py`, `tecnica.py`, `defesa.py` e
`chefe.py` e `dominio.py`.
"""

from __future__ import annotations

import json
import math
import random

from ouroboros.bootstrap.scene import IScene

from ryoiki import visual as v
from ryoiki.chefe import Chefe, carregar_chefe
from ryoiki.combate import GOLPE, REFORCO, Alvo, FeelCombate, Golpeador
from ryoiki.defesa import FeelDefesa, Vitalidade
from ryoiki.dominio import Expansao, FeelDominio
from ryoiki.movimento import DADOS, Camera, Corpo, Feel
from ryoiki.tecnica import Conjurador, carregar_tecnicas

LARGURA, ALTURA = 960, 540
TELA = (LARGURA, ALTURA)
VITORIA = 3.5  # s com o 祓除 na tela antes de recomeçar


class ArenaScene(IScene):
    def __init__(
        self,
        entrada,
        ao_sair=None,
        feel: Feel | None = None,
        feel_combate: FeelCombate | None = None,
        tecnica: str | None = None,
        chefe: str | None = None,
        ao_titulo=None,
        *,
        feel_defesa: FeelDefesa | None = None,
        feel_dominio: FeelDominio | None = None,
        dados_chefe=None,
        vida_inicial: float | None = None,
        ao_fim=None,
        rotulo: str = "",
    ) -> None:
        """Avulsa (só `tecnica`/`chefe`) ou dentro da rota: aí a rota passa os feels com as
        recompensas, o chefe escalado, a vida que sobrou e `ao_fim(venceu, vida)`."""
        self.entrada = entrada
        self.ao_sair = ao_sair
        self.ao_titulo = ao_titulo  # None: a pausa não oferece voltar ao título
        self.ao_fim = ao_fim  # na rota: chamado no fim da luta, em vez de recomeçar
        self.vida_inicial = vida_inicial
        self.rotulo = rotulo  # na rota: o progresso e as recompensas, no canto
        self.pausado = False
        self.opcao = 0
        self.feel = feel or Feel.carregar()
        self.fc = feel_combate or FeelCombate.carregar()
        w, h = self.feel.arena
        self.fd = feel_defesa or FeelDefesa.carregar()
        self.dados_chefe = dados_chefe or carregar_chefe(chefe)
        self.fdom = feel_dominio or FeelDominio.carregar()
        self.tecnicas = carregar_tecnicas()
        dados = json.loads((DADOS / "tecnicas.json").read_text(encoding="utf-8"))
        self.ordem = list(self.tecnicas)
        self.conjurador = Conjurador(self.tecnicas[tecnica or dados["jogador"]])
        self.camera = Camera(w / 2, h / 2, TELA)
        self._recomecar()
        self.cenario = v.Cenario.novo(self.feel.arena)
        self.efeitos: list[v.Efeito] = []
        self.rng = random.Random(3)
        self.relogio = 0.0
        self.t_parado = 0.0  # o hitstop
        self.tremor = 0.0
        self.t_clarao = 0.0  # a tela escurece no Kokusen
        self.t_kokusen = 0.0  # o 黒閃 na tela
        self.t_vitoria = 0.0
        self.t_faixa = 0.0  # o nome do domínio na tela
        self.faixa = ("", "", self.cor_chefe)  # kanji, nome, cor
        self.t_aviso = 0.0  # "interrompido!"
        self.t_aviso_txt = ("", 0.0)  # avisos do seu domínio (texto, segundos)
        self.t_sem_energia = 0.0
        self.t_derrota = 0.0
        self.guardando = False

    def _recomecar(self) -> None:
        w, h = self.feel.arena
        self.corpo = Corpo(w / 2 - 120, h / 2)
        self.golpeador = Golpeador(self.fc)
        self.vitalidade = Vitalidade(
            self.fd, vida=-1.0 if self.vida_inicial is None else self.vida_inicial
        )
        self.expansao = Expansao(self.fdom)
        self.alvo = self._nova_maldicao()
        self.conjurador.trocar(self.conjurador.tecnica)

    def _nova_maldicao(self) -> Alvo:
        w, h = self.feel.arena
        self.chefe = Chefe.novo(self.dados_chefe, w / 2 + 260, h / 2)
        return self.chefe.alvo

    @property
    def cor_chefe(self):
        return self.dados_chefe.cor

    @property
    def alvos(self) -> list[Alvo]:
        """Quem apanha: o chefe e os lacaios dele."""
        return [self.alvo, *self.chefe.lacaios]

    @property
    def opcoes(self) -> list[str]:
        base = ["Continuar"]
        if self.ao_fim is None:  # na rota não dá para recomeçar a luta (seria trapaça)
            base.append("Recomeçar a luta")
        if self.ao_titulo is not None:
            base.append("Abandonar a rota" if self.ao_fim else "Voltar ao título")
        if self.ao_sair is not None:
            base.append("Sair do jogo")
        return base

    def _pausa(self, e) -> None:
        n = len(self.opcoes)
        if e.is_action_pressed("cima"):
            self.opcao = (self.opcao - 1) % n
        if e.is_action_pressed("baixo"):
            self.opcao = (self.opcao + 1) % n
        if not e.is_action_pressed("confirmar"):
            return
        escolha = self.opcoes[self.opcao]
        self.pausado = False
        if escolha == "Recomeçar a luta":
            self._recomecar()
        elif escolha in ("Voltar ao título", "Abandonar a rota"):
            self.ao_titulo()
        elif escolha == "Sair do jogo":
            self.ao_sair()

    def _desenhar_pausa(self, r) -> None:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, v.a(v.PRETO, 180))
        r.draw_text(
            LARGURA / 2,
            150,
            "一時停止",
            54,
            v.a(v.TINTA, 230),
            anchor="center",
            font_id=v.FONTE_PINCEL,
        )
        for i, nome in enumerate(self.opcoes):
            sel = i == self.opcao
            y = 240 + i * 40
            if sel:
                r.draw_ui_rect(LARGURA / 2 - 150, y - 16, 300, 32, v.a(v.SANGUE, 90))
            r.draw_text(
                LARGURA / 2, y, nome, 20, v.a(v.TINTA, 255 if sel else 140), anchor="center"
            )
        r.draw_text(
            LARGURA / 2,
            ALTURA - 40,
            "W/S escolhe · Enter confirma · Esc volta à luta",
            13,
            v.a(v.TINTA, 120),
            anchor="center",
        )

    def _eixos(self) -> tuple[float, float]:
        e = self.entrada
        dx = float(e.is_action_held("direita")) - float(e.is_action_held("esquerda"))
        dy = float(e.is_action_held("baixo")) - float(e.is_action_held("cima"))
        return dx, dy

    def update(self, world, delta_time: float) -> None:
        dt = min(delta_time, 1 / 30)  # um engasgo não teleporta o jogador
        self.relogio += dt
        e = self.entrada
        if e.is_action_pressed("sair"):
            self.pausado, self.opcao = not self.pausado, 0
            return
        if self.pausado:
            self._pausa(e)
            return
        if not self.vitalidade.vivo:  # derrota: a arena recomeça sozinha
            self.t_derrota += dt
            if self.t_derrota >= self.fd.renascer:
                self.t_derrota = 0.0
                if self.ao_fim is not None:
                    self.ao_fim(False, 0.0)
                else:
                    self._recomecar()
            return
        if not self.alvo.vivo:  # vitória: o chefe foi exorcizado
            self.t_vitoria += dt
            for ef in self.efeitos:
                v.mover_efeito(ef, dt)
            self.efeitos = [ef for ef in self.efeitos if not ef.acabou]
            if self.t_vitoria >= VITORIA:
                self.t_vitoria = 0.0
                if self.ao_fim is not None:
                    self.ao_fim(True, self.vitalidade.vida)
                else:
                    self._recomecar()
            return
        g, vit = self.golpeador, self.vitalidade
        if e.is_action_pressed("trocar"):
            i = self.ordem.index(self.conjurador.tecnica.id)
            self.conjurador.trocar(self.tecnicas[self.ordem[(i + 1) % len(self.ordem)]])
        # os apertos contam até no hitstop: é aí que mora o Kokusen
        if e.is_action_pressed("golpe"):
            g.pedir(GOLPE)
        if e.is_action_pressed("reforco") and not g.pedir(REFORCO):
            self.t_sem_energia = 0.6
        self.tremor *= math.exp(-14 * dt)
        self.t_clarao = max(0.0, self.t_clarao - dt)
        self.t_kokusen = max(0.0, self.t_kokusen - dt)
        self.t_sem_energia = max(0.0, self.t_sem_energia - dt)
        self.t_faixa = max(0.0, self.t_faixa - dt)
        self.t_aviso = max(0.0, self.t_aviso - dt)
        self.t_aviso_txt = (self.t_aviso_txt[0], max(0.0, self.t_aviso_txt[1] - dt))
        if self.t_parado > 0:
            self.t_parado = max(0.0, self.t_parado - dt)
            return
        mx, my = self.camera.mundo_de(*e.get_cursor_position())
        self.corpo.mirar(mx, my)
        dx, dy = self._eixos()
        xp = self.expansao
        if e.is_action_pressed("dominio") and not xp.ativo:
            if not xp.expandir(g, self.conjurador.tecnica):
                self.t_sem_energia = 0.6
        for i, acao in enumerate(("tecnica_1", "tecnica_2")):
            if e.is_action_pressed(acao) and not g.atacando and not xp.queimado:
                if not self.conjurador.usar(i, self.corpo, (mx, my), g):
                    self.t_sem_energia = 0.6 if self.conjurador.recargas[i] <= 0 else 0.0
        self.guardando = e.is_action_held("reforco") and not g.atacando
        vit.passo(dt)
        curando = vit.reverter(dt, g, e.is_action_held("reversa") and not g.atacando)
        if e.is_action_pressed("esquiva"):
            a = g.ataque
            if a is None or a.fase == "depois":  # a esquiva cancela a recuperação
                if self.corpo.esquivar(self.feel, dx, dy):
                    g.ataque, g.fila = None, ""
        if xp.simples:  # o Domínio Simples prende o pé no círculo
            dx = dy = 0.0
        elif g.atacando:
            dx, dy = dx * self.fc.lentidao, dy * self.fc.lentidao
        elif curando:
            dx, dy = dx * self.fd.reversa_lentidao, dy * self.fd.reversa_lentidao
        elif self.guardando:
            dx, dy = dx * self.fd.guarda_lentidao, dy * self.fd.guarda_lentidao
        self.corpo.passo(self.feel, dt, dx, dy)
        vida_antes = self.alvo.vida
        for imp in g.atualizar(dt, self.corpo, self.alvos):
            self.efeitos += v.efeitos_do_impacto(imp, self.rng)
            self.t_parado = max(self.t_parado, imp.hitstop)
            self.tremor = max(self.tremor, 16 if imp.kokusen else (7 if imp.final else 3.5))
            if imp.kokusen:
                self.t_clarao, self.t_kokusen = 0.1, 0.9
        for ac in self.conjurador.atualizar(dt, self.corpo, self.alvos, self.feel.arena):
            self.efeitos += v.efeitos_da_tecnica(ac, ac.cor, self.rng)
            if ac.dano:
                self.t_parado = max(self.t_parado, 0.06 if ac.dano >= 20 else 0.03)
                self.tremor = max(self.tremor, 9 if ac.dano >= 20 else 3)
        for ac in xp.atualizar(
            dt,
            g,
            self.chefe,
            bombeando=e.is_action_held("dominio"),
            segurando_simples=e.is_action_held("simples"),
            dano_causado=vida_antes - self.alvo.vida,
        ):
            self.efeitos += v.efeitos_da_tecnica(ac, self.conjurador.tecnica.cor, self.rng)
        self._eventos_da_expansao()
        for dano in self.chefe.atualizar(dt, self.corpo, self.feel.arena):
            self._sofrer(dano.valor, dano.garantido)
        self._eventos_do_chefe()
        self.chefe.separar(self.corpo)
        self.alvo.passo(dt, self.feel.arena)
        if not self.alvo.vivo:
            self.tremor, self.t_clarao = 18, 0.12
            for la in self.chefe.lacaios:  # os lacaios morrem com ele
                self.efeitos += v.efeitos_da_tecnica(_Explosao(la.x, la.y, 45), v.TINTA, self.rng)
            self.chefe.lacaios.clear()
            self.efeitos += v.efeitos_da_tecnica(
                _Explosao(self.alvo.x, self.alvo.y, 160), self.cor_chefe, self.rng
            )
        for ef in self.efeitos:
            v.mover_efeito(ef, dt)
        self.efeitos = [ef for ef in self.efeitos if not ef.acabou]
        self.camera.seguir(self.feel, self.corpo, mx, my, dt)

    def _eventos_do_chefe(self) -> None:
        for ev in self.chefe.eventos:
            tipo, x, y = ev[0], ev[1], ev[2]
            if tipo == "erupcao":
                self.efeitos += v.efeitos_da_tecnica(
                    _Explosao(x, y, ev[3]), self.cor_chefe, self.rng
                )
                for _ in range(6):
                    t = self.rng.uniform(0, 2 * math.pi)
                    vel = self.rng.uniform(120, 340)
                    self.efeitos.append(
                        v.Efeito(
                            "faisca",
                            x,
                            y,
                            math.cos(t) * vel,
                            math.sin(t) * vel,
                            0.3,
                            cor=self.cor_chefe,
                        )
                    )
                self.tremor = max(self.tremor, 4)
            elif tipo == "dominio":
                self.t_faixa, self.tremor, self.t_clarao = 2.2, 16, 0.12
                dm = self.dados_chefe.dominio
                self.faixa = (dm.kanji, dm.nome, self.cor_chefe)
            elif tipo == "interrompido":
                self.t_aviso, self.tremor = 1.2, 10
                self.efeitos.append(v.Efeito("onda", x, y, vida=0.5, cor=v.TINTA, raio=140))
            elif tipo == "corte":
                self.efeitos.append(
                    v.Efeito(
                        "linha", x, y, vida=0.3, pts=((x, y), (ev[3], ev[4])), cor=self.cor_chefe
                    )
                )
                self.tremor = max(self.tremor, 3)
            elif tipo == "invocar":
                self.efeitos.append(v.Efeito("onda", x, y, vida=0.4, cor=self.cor_chefe, raio=50))
            elif tipo in ("lacaio_explode", "lacaio_morre"):
                cor = v.SANGUE if tipo == "lacaio_explode" else v.TINTA
                self.efeitos += v.efeitos_da_tecnica(_Explosao(x, y, 45), cor, self.rng)
                self.tremor = max(self.tremor, 5)
            elif tipo == "fim_dominio":
                self.efeitos.append(v.Efeito("onda", x, y, vida=0.6, cor=self.cor_chefe, raio=400))
        self.chefe.eventos.clear()

    def _eventos_da_expansao(self) -> None:
        xp, c, t = self.expansao, self.corpo, self.conjurador.tecnica
        for ev in xp.eventos:
            if ev == "expandir":
                self.t_faixa, self.tremor, self.t_clarao = 2.2, 14, 0.12
                self.faixa = (xp.dados.kanji, xp.dados.nome, t.cor)
                self.efeitos.append(v.Efeito("onda", c.x, c.y, vida=0.6, cor=t.cor, raio=600))
            elif ev == "choque":
                self.t_aviso_txt = ("領域の押し合い — choque de domínios", 1.6)
                self.tremor = 14
            elif ev == "venceu":
                self.t_aviso_txt = ("勝 — o domínio dele quebrou", 1.6)
                self.tremor, self.t_clarao = 18, 0.12
            elif ev == "perdeu":
                self.t_aviso_txt = ("敗 — o seu domínio quebrou", 1.6)
                self.tremor = 12
        xp.eventos.clear()

    def _sofrer(self, dano: float, garantido: bool = False) -> None:
        c = self.corpo
        if garantido and self.expansao.simples:  # o Domínio Simples anula o acerto garantido
            self.efeitos.append(v.Efeito("onda", c.x, c.y, vida=0.25, cor=v.TINTA, raio=40))
            return
        entrou = self.vitalidade.sofrer(
            dano,
            self.golpeador,
            invencivel=c.invencivel and not garantido,  # o acerto garantido ignora a esquiva
            guardando=self.guardando,
        )
        if entrou > 0:
            self.efeitos.append(
                v.Efeito("numero", c.x, c.y - 24, 0, -80, 0.6, texto=f"-{entrou:.0f}", cor=v.SANGUE)
            )
            self.tremor = max(self.tremor, 4 if garantido else 10)
            if not garantido:
                self.t_parado = max(self.t_parado, 0.07)

    # ------------------------------------------------------------------ desenho

    def render(self, world, r) -> None:
        cam = self.camera
        ox = math.sin(self.relogio * 91) * self.tremor
        oy = math.cos(self.relogio * 73) * self.tremor
        cam.x, cam.y = cam.x + ox, cam.y + oy
        try:
            self._mundo(r)
        finally:
            cam.x, cam.y = cam.x - ox, cam.y - oy
        ch = self.chefe
        xp, cor_t = self.expansao, self.conjurador.tecnica.cor
        if xp.em_choque:
            v.choque_tela(r, TELA, self.relogio, xp.choque, cor_t)
        elif ch.dominio_ativo:
            v.dominio_tela(r, TELA, self.relogio, min(1.0, ch.t_dominio * 2), self.cor_chefe)
        elif xp.ativo:
            v.dominio_jogador_tela(r, TELA, self.relogio, cor_t, min(1.0, xp.t_dominio * 2))
        if self.t_clarao > 0:  # o Clarão Negro apaga a tela por um instante
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, v.a(v.PRETO, 210))
            sx, sy = cam.tela_de(self.alvo.x, self.alvo.y)
            r.draw_ui_circle(sx, sy, 90, v.a(v.SANGUE, 200), 6)
        v.vinheta(r, TELA, 1.4 if self.golpeador.na_zona else 1.0)
        if self.alvo.vivo:
            v.seta_fora_da_tela(r, cam.tela_de(self.alvo.x, self.alvo.y), TELA, self.cor_chefe)
        self._hud(r)
        if self.pausado:
            self._desenhar_pausa(r)

    def _mundo(self, r) -> None:
        cam, c, g = self.camera, self.corpo, self.golpeador
        v.desenhar_chao(r, cam, self.feel.arena, self.cenario, self.relogio, TELA)
        v.poeira(r, cam, self.feel.arena, self.relogio, TELA)
        al = self.alvo
        cor = self.conjurador.tecnica.cor
        ch = self.chefe
        if al.vivo and ch.estado == "carga" and ch.padrao.tipo == "investida":
            q = ch.padrao.p
            v.aviso_investida(
                r, cam, al.x, al.y, ch.direcao, q["alcance"], al.raio, ch.progresso, self.cor_chefe
            )
        for co in ch.cortes:
            v.aviso_corte(r, cam, co, self.cor_chefe)
        for er in ch.erupcoes:
            v.aviso_erupcao(r, cam, er, self.cor_chefe)
        for ar in self.conjurador.areas:
            v.area_pendente(r, cam, ar, ar.cor, self.relogio)
        if al.vivo:
            sx, sy = cam.tela_de(al.x, al.y)
            if ch.estado in ("carga", "investida"):
                olhar = ch.direcao
            else:
                d = math.hypot(c.x - al.x, c.y - al.y) or 1
                olhar = ((c.x - al.x) / d, (c.y - al.y) / d)
            if ch.estado == "carga":  # brilha mais forte perto de soltar
                r.draw_ui_circle(
                    sx,
                    sy,
                    al.raio * (1.3 + 0.3 * ch.progresso),
                    v.a(self.cor_chefe, 60 + 120 * ch.progresso),
                    3,
                )
            v.desenhar_chefe(
                ch.dados.visual,
                r,
                sx,
                sy,
                al.raio,
                self.relogio,
                olhar,
                ferido=al.t_ferido > 0,
                queimado=ch.estado == "queimado",
            )
            if ch.estado == "entoando":
                v.entoando(
                    r,
                    sx,
                    sy,
                    al.raio,
                    ch.progresso,
                    ch.dano_na_entoacao / ch.dados.dominio.interromper,
                    self.cor_chefe,
                )
            if al.marcado:
                v.marca(r, sx, sy, al.raio, self.relogio, cor)
            if al.t_atordoado > 0:
                v.atordoado(r, sx, sy, al.raio, self.relogio)
        for i, (x, y) in enumerate(c.rastro):  # o rastro da esquiva
            sx, sy = cam.tela_de(x, y)
            r.draw_ui_circle(sx, sy, c.raio * 0.8, v.a(v.ENERGIA, 30 + 22 * i))
        sx, sy = cam.tela_de(c.x, c.y)
        vit = self.vitalidade
        if not vit.vivo:
            v.feiticeiro(r, sx, sy, c.raio, c.mira, 0.0, invencivel=True)
            return
        if vit.curando:
            v.reversa(r, sx, sy, c.raio, self.relogio)
        v.feiticeiro(
            r,
            sx,
            sy,
            c.raio,
            c.mira,
            self.relogio,
            punho=self._punho(),
            aura=g.energia / self.fc.energia_max if g.energia > 60 else 0.0,
            zona=g.na_zona,
            invencivel=c.invencivel or vit.t_ferido > 0,
        )
        if self.expansao.simples:
            v.dominio_simples(r, sx, sy, c.raio, self.relogio)
        if self.guardando and g.energia > 0:
            v.escudo(r, sx, sy, c.raio, self.relogio, vit.t_bloqueio > 0)
        if g.atacando and g.ataque.fase == "ativo":  # o arco do golpe
            ang = math.atan2(c.mira[1], c.mira[0])
            meio = math.radians(self.fc.angulo / 2)
            cor = v.SANGUE if g.ataque.kokusen else v.TINTA
            r.draw_ui_arc(
                sx, sy, c.raio + self.fc.alcance * 0.8, ang - meio, ang + meio, v.a(cor, 150), 3
            )
        if c.t_recarga > 0:
            frac = c.t_recarga / (self.feel.esquiva_duracao + self.feel.esquiva_recarga)
            r.draw_ui_arc(sx, sy, c.raio + 8, 0, 6.283 * frac, v.a(v.TINTA, 90), 2)
        for p in self.conjurador.projeteis:
            v.projetil(r, cam, p, p.cor)
        for la in self.chefe.lacaios:
            lx, ly = cam.tela_de(la.x, la.y)
            v.transfigurado(
                r,
                lx,
                ly,
                la.raio,
                self.relogio,
                ferido=la.t_ferido > 0,
                vida=la.vida / la.vida_max,
            )
            if la.marcado:
                v.marca(r, lx, ly, la.raio, self.relogio, self.conjurador.tecnica.cor)
        for b in self.chefe.brasas:
            v.brasa(r, cam, b, self.relogio, self.cor_chefe)
        for ef in self.efeitos:
            v.desenhar_efeito(r, cam, ef)

    def _hud_chefe(self, r) -> None:
        """A barra do chefe no alto, com as marcas de onde o domínio dispara."""
        ch, al = self.chefe, self.alvo
        d = ch.dados
        w, x, y = 460, LARGURA / 2 - 230, 30
        r.draw_text(
            LARGURA / 2,
            y - 22,
            f"{d.kanji}  {d.nome}",
            18,
            v.a(v.TINTA, 230),
            anchor="center",
            font_id=v.FONTE_PINCEL,
        )
        r.draw_ui_rect(x, y, w, 9, v.a(v.PRETO, 180))
        r.draw_ui_rect(x, y, w * al.vida / al.vida_max, 9, d.cor)
        for gat in d.dominio.gatilhos:
            gx = x + w * gat
            r.draw_ui_line(
                gx, y - 3, gx, y + 12, v.a(v.TINTA, 200 if gat in ch.gatilhos else 60), 2
            )
        estado = {"queimado": "técnica queimada", "entoando": "entoando o domínio"}.get(ch.estado)
        if estado and al.vivo:
            r.draw_text(LARGURA / 2, y + 22, estado, 13, v.a(v.LAVA_CLARA, 220), anchor="center")
        if ch.dominio_ativo and not self.expansao.em_choque:
            r.draw_text(
                LARGURA / 2,
                y + 22,
                f"{d.dominio.kanji}  {ch.t_dominio:.1f}s · acerto garantido: reforço reduz, "
                "Domínio Simples (C) anula",
                13,
                v.a(v.LAVA_CLARA, 230),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
        if self.t_faixa > 0:  # 領域展開 + o nome do domínio
            k = min(1.0, self.t_faixa / 0.4)
            r.draw_ui_rect(0, ALTURA / 2 - 70, LARGURA, 150, v.a(v.PRETO, 170 * k))
            r.draw_text(
                LARGURA / 2,
                ALTURA / 2 - 30,
                "領域展開",
                34,
                v.a(v.LAVA_CLARA, 255 * k),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
            r.draw_text(
                LARGURA / 2,
                ALTURA / 2 + 15,
                self.faixa[0],
                52,
                v.a(self.faixa[2], 255 * k),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
            r.draw_text(
                LARGURA / 2,
                ALTURA / 2 + 62,
                self.faixa[1],
                14,
                v.a(v.TINTA, 200 * k),
                anchor="center",
            )
        if self.t_aviso > 0:
            r.draw_text(
                LARGURA / 2,
                110,
                "中断 — domínio interrompido",
                22,
                v.a(v.TINTA, 255 * min(1.0, self.t_aviso)),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
        if not al.vivo:
            k = min(1.0, self.t_vitoria * 2)
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, v.a(v.PRETO, 140 * k))
            r.draw_text(
                LARGURA / 2,
                ALTURA / 2 - 20,
                "祓除",
                90,
                v.a(v.TINTA, 240 * k),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
            r.draw_text(
                LARGURA / 2,
                ALTURA / 2 + 50,
                f"{d.nome} foi exorcizado",
                16,
                v.a(v.TINTA, 180 * k),
                anchor="center",
            )

    def _hud_dominio(self, r) -> None:
        """O seu domínio: pronto, aberto, queimado, o Simples e a barra do choque."""
        xp, g, t = self.expansao, self.golpeador, self.conjurador.tecnica
        x, y = 24, ALTURA - 132
        if xp.em_choque:
            w, bx, by = 360, LARGURA / 2 - 180, 92
            r.draw_ui_rect(bx, by, w, 12, v.a(self.cor_chefe, 220))
            r.draw_ui_rect(bx, by, w * xp.choque, 12, t.cor)
            r.draw_ui_line(bx + w / 2, by - 4, bx + w / 2, by + 16, v.a(v.TINTA, 200), 2)
            dica = "segure F: queime energia · bata nele: cada golpe empurra"
            r.draw_text(LARGURA / 2, by + 20, dica, 13, v.a(v.TINTA, 220), anchor="center")
        elif xp.ativo:
            txt = f"{xp.dados.kanji}  {xp.t_dominio:.1f}s · acerto garantido"
            r.draw_text(x, y, txt, 16, v.a(t.cor, 230), font_id=v.FONTE_PINCEL)
        elif xp.queimado:
            txt = f"術式焼き切れ  {xp.t_queimado:.1f}s (sem técnica)"
            r.draw_text(x, y, txt, 16, v.a(v.SANGUE, 220), font_id=v.FONTE_PINCEL)
        elif t.dominio is not None:
            pronto = xp.pode_expandir(g, t)
            pulso = 0.6 + 0.4 * math.sin(self.relogio * 6) if pronto else 0.35
            txt = f"F  領域展開 {t.dominio.kanji}" + ("" if pronto else "  (barra cheia)")
            cor = t.cor if pronto else v.TINTA
            r.draw_text(x, y, txt, 16, v.a(cor, 255 * pulso), font_id=v.FONTE_PINCEL)
        if xp.simples:
            r.draw_text(
                x + 250, ALTURA - 110, "簡易領域", 18, v.a(v.TINTA, 230), font_id=v.FONTE_PINCEL
            )
        texto, tempo = self.t_aviso_txt
        if tempo > 0:
            r.draw_text(
                LARGURA / 2,
                140,
                texto,
                22,
                v.a(v.TINTA, 255 * min(1.0, tempo)),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )

    def _hud_tecnica(self, r) -> None:
        """A técnica embaixo à direita: o nome e os dois golpes com custo e recarga."""
        t, cj, g = self.conjurador.tecnica, self.conjurador, self.golpeador
        x0, y0 = LARGURA - 24, ALTURA - 96
        r.draw_text(
            x0, y0 - 50, t.kanji, 22, v.a(t.cor, 230), anchor="topright", font_id=v.FONTE_PINCEL
        )
        r.draw_text(x0, y0 - 6, f"{t.nome}  (Tab troca)", 12, v.a(v.TINTA, 130), anchor="topright")
        for i, (gol, tecla) in enumerate(zip(t.golpes, ("E", "Q"), strict=False)):
            bx, by = x0 - 290 + 150 * i, y0 + 16
            pronto = cj.pronto(i, g.energia) and not self.expansao.queimado
            r.draw_ui_rect(bx, by, 140, 34, v.a(v.PRETO, 160))
            if cj.recargas[i] > 0:
                r.draw_ui_rect(bx, by, 140 * cj.recargas[i] / gol.recarga, 34, v.a(t.cor, 50))
            borda = v.a(t.cor, 200) if pronto else v.a(v.TINTA, 70)
            cantos = [(bx, by), (bx + 140, by), (bx + 140, by + 34), (bx, by + 34)]
            r.draw_ui_polygon(cantos, borda, 1)
            r.draw_text(
                bx + 8, by + 3, f"{tecla}  {gol.nome}", 14, v.a(v.TINTA, 230 if pronto else 110)
            )
            r.draw_text(bx + 8, by + 20, f"{gol.custo:.0f} de energia", 11, v.a(v.TINTA, 110))

    def _punho(self):
        a = self.golpeador.ataque
        if a is None:
            return None
        lado = 0 if a.tipo == REFORCO else (-1 if a.passo % 2 == 0 else 1)
        if a.fase == "antes":
            antes = self.fc.reforco_antes if a.tipo == REFORCO else self.fc.antes
            return lado, -0.3 * min(1.0, a.t / antes)  # recolhe antes de soltar
        if a.fase == "ativo":
            return lado, 1.0
        return lado, max(0.0, 1 - a.t / self.fc.depois)

    def _hud(self, r) -> None:
        g, fc, vit = self.golpeador, self.fc, self.vitalidade
        x, y, w = 24, ALTURA - 54, 220
        vy = y - 44  # a vida, acima da energia
        r.draw_ui_rect(x, vy, w, 8, v.a(v.PRETO, 170))
        cor_vida = v.CURA if vit.curando else (v.TINTA if vit.t_ferido <= 0 else v.SANGUE)
        r.draw_ui_rect(x, vy, w * vit.vida / self.fd.vida_max, 8, cor_vida)
        if vit.curando:
            r.draw_text(
                x + w + 12, vy - 8, "反転術式", 18, v.a(v.CURA, 220), font_id=v.FONTE_PINCEL
            )
        self._hud_tecnica(r)
        self._hud_chefe(r)
        self._hud_dominio(r)
        if self.rotulo:
            r.draw_text(16, 12, self.rotulo, 12, v.a(v.TINTA, 150))
        if not vit.vivo:
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, v.a(v.PRETO, 150))
            r.draw_text(
                LARGURA / 2,
                ALTURA / 2 - 20,
                "敗北",
                90,
                v.a(v.SANGUE, 230),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
            r.draw_text(
                LARGURA / 2,
                ALTURA / 2 + 50,
                "a arena recomeça...",
                16,
                v.a(v.TINTA, 160),
                anchor="center",
            )
        r.draw_text(x, y - 26, "呪力", 20, v.a(v.TINTA, 200), font_id=v.FONTE_PINCEL)
        r.draw_ui_rect(x, y, w, 10, v.a(v.PRETO, 170))
        cor = v.SANGUE if g.na_zona else v.ENERGIA
        r.draw_ui_rect(x, y, w * g.energia / fc.energia_max, 10, cor)
        corte = x + w * fc.reforco_custo / fc.energia_max
        r.draw_ui_line(corte, y - 2, corte, y + 12, v.a(v.TINTA, 160), 1)
        if self.t_sem_energia > 0:
            r.draw_text(
                x + w + 12, y - 4, "sem energia", 14, v.a(v.SANGUE, 255 * self.t_sem_energia)
            )
        if g.na_zona:
            r.draw_text(
                x + 58,
                y - 24,
                f"ゾーン  {g.t_zona:.1f}",
                18,
                v.a(v.SANGUE, 230),
                font_id=v.FONTE_PINCEL,
            )
        if g.combo > 1:
            r.draw_text(
                LARGURA - 28,
                70,
                f"{g.combo}",
                44,
                v.a(v.TINTA, 230),
                anchor="topright",
                font_id=v.FONTE_PINCEL,
            )
            r.draw_text(
                LARGURA - 28,
                118,
                "連撃",
                18,
                v.a(v.TINTA, 150),
                anchor="topright",
                font_id=v.FONTE_PINCEL,
            )
        if g.kokusens:
            r.draw_text(
                LARGURA - 28,
                24,
                f"黒閃 ×{g.kokusens}",
                18,
                v.a(v.SANGUE, 200),
                anchor="topright",
                font_id=v.FONTE_PINCEL,
            )
        if self.t_kokusen > 0:
            k = self.t_kokusen / 0.9
            tam = int(96 + 30 * (k - 0.8) * 5) if k > 0.8 else 96
            r.draw_text(
                LARGURA / 2 + 3,
                120 + 3,
                "黒閃",
                tam,
                v.a(v.SANGUE, 255 * k),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
            r.draw_text(
                LARGURA / 2,
                120,
                "黒閃",
                tam,
                v.a(v.PRETO, 255 * k),
                anchor="center",
                font_id=v.FONTE_PINCEL,
            )
        dica = (
            "Espaço esquiva · clique golpe · direito reforço · E/Q técnica · R cura · "
            "F domínio · C Domínio Simples"
        )
        r.draw_text(LARGURA / 2, ALTURA - 14, dica, 12, v.a(v.TINTA, 110), anchor="center")


class _Explosao:
    """Um `Acerto` de explosão para reaproveitar os efeitos da técnica."""

    forma = "explosao"
    dano = 0.0

    def __init__(self, x: float, y: float, raio: float) -> None:
        self.x, self.y, self.raio = x, y, raio
