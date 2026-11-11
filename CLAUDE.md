# CLAUDE.md — Ryoiki

Guia para o Claude Code neste projeto. Idioma: PT-BR.

## O que é
Ação top-down de Jujutsu em tempo real: técnicas montadas por blocos (dados, não código),
energia amaldiçoada como tanque único (técnica, Técnica Reversa, reforço), Kokusen no timing
e o Domínio como clímax (expansão, choque de domínios, Domínio Simples). Joga-se com um
feiticeiro próprio ou com o elenco do anime (os mesmos blocos, fixos).

Promovido do blueprint `GAM-12` (R.Y.O.I.K.I.). Irmão em tempo real do Karmabound
(GAM-10/11): reaproveitar ideias de lá (Kokusen, votos), não código de turno.

## Escopo da v0 (o protótipo que prova a ideia)
Uma arena: o feiticeiro do jogador (uma técnica de blocos) contra uma maldição de grau
especial com domínio. Precisa ter: golpe, energia, Kokusen, Técnica Reversa, Domínio,
choque de domínios e Domínio Simples. Nada de elenco, mapa ou história antes disso divertir.

## Andamento da v0
1. ✅ Movimento, esquiva com invencibilidade e câmera (`movimento.py`).
2. ✅ Golpe em combo de 3, reforço com energia, Kokusen por timing (a janela abre no impacto;
   apertar antes não conta) e zona, hitstop e tremor (`combate.py`). Visual próprio em
   `visual.py`: rua de concreto dentro de uma cortina, feiticeiro visto de cima, maldição.
3. ✅ Técnica por blocos em `data/tecnicas.json` (`tecnica.py`: formas `projetil`, `area`,
   `marcados`; efeitos `dano`, `puxar`, `empurrar`, `marcar`, `atordoar`, `se_marcado`).
   Duas técnicas de exemplo (Boneco de Palha, Ilimitado), troca com Tab. Vida, Técnica
   Reversa (segurar R) e reforço como defesa (segurar o botão de reforço) em `defesa.py`; a
   maldição de treino revida com uma pancada avisada (`inimigo.py`). Feel em `feel.json`
   (`defesa`, `maldicao_treino`).
4. ✅ A maldição chefe em `data/maldicoes.json` (`chefe.py`): padrões `investida`,
   `erupcoes` e `brasas`, todos avisados no chão; o domínio entoa em cada gatilho de vida,
   é interrompido por dano ou atordoamento, dá acerto garantido (a esquiva não salva, o
   reforço reduz) e deixa a técnica queimada. A maldição de treino (`inimigo.py`) saiu da
   arena, mas segue testada.
5. ✅ O seu Domínio, o choque e o Domínio Simples (`dominio.py`). Cada técnica tem um
   `dominio` em `tecnicas.json` (efeitos por tique, onde o chefe estiver). Expande com a barra
   cheia (F); no fim, a técnica queima. Dois domínios abertos viram choque: o acerto
   garantido se anula, o tempo para e uma barra decide (o mais refinado empurra sozinho; o
   jogador empurra queimando energia segurando F ou batendo). Domínio Simples (segure C)
   anula o acerto garantido, custa energia e prende o pé. Feel em `feel.json` (`dominio`).

**A v0 está completa.**

## Andamento da v1 (proposta; a ordem pode mudar com o feedback do Enzo)
1. ✅ Tela de título (`tela_titulo.py`) com escolha de técnica e chefe vindos dos dados, e
   pausa na arena (Esc: continuar, recomeçar, voltar ao título, sair). `game.py` empilha a
   arena sobre o título.
2. ✅ Segundo chefe: Mahito (真人) em `maldicoes.json`, com o padrão novo `invocar`
   (lacaios que correm e explodem no contato, e podem ser mortos), `regeneracao` (vida/s,
   parada com a técnica queimada), `visual` (qual desenho usar: `vulcao`, `remendos`) e o
   domínio 自閉円頓裹. Avisos e domínio do chefe saem na cor dele. Golpes e técnicas
   acertam vários alvos (`ArenaScene.alvos`).
3. ✅ Feiticeiro próprio: a oficina (`oficina.py` + `tela_oficina.py`, aberta pelo título).
   Cada golpe = uma forma pronta + até 3 efeitos prontos; custo e recarga saem da soma dos
   blocos. O domínio próprio garante os efeitos do golpe 1 (meio dano, sem puxar/empurrar).
   Salva em `%APPDATA%/Ryoiki/tecnica_propria.json` (fora do repo); `carregar_tecnicas`
   junta como `propria`. Os testes isolam `APPDATA` em `tests/conftest.py`.
4. ✅ A rota (`rota.py` + `tela_rota.py`, dados em `data/rota.json`): lutas em sequência
   com `grau` (escala vida e dano do chefe), a vida passa de uma para a outra com cura
   parcial, e entre lutas escolhe-se 1 de 3 recompensas: bênçãos e votos (trocas), que mexem
   nos feels por `mods`. Na rota, a pausa não deixa recomeçar a luta. O título agora tem a
   linha de ações: lutar, rota, oficina.
5. Calibrar o feel quando o Enzo jogar (só quando ele pedir).
6. ✅ Terceiro chefe: Sukuna (両面宿儺, `visual: rei`), fecha a rota. Padrão novo `cortes`
   (riscos avisados que atravessam a arena; o primeiro passa em cima do jogador), Clivar
   (investida), Fuga (um projétil grande) e o domínio 伏魔御廚子, o mais refinado (0,3):
   no choque, sem reagir, perde-se rápido; o Domínio Simples é a resposta.

## Riscos conhecidos (limits do blueprint)
- Feel de ação exige muito ajuste (hitstop, knockback, i-frames).
- Choque de domínios pode virar QTE chato se não tiver escolha.
- Arte e animação top-down custam caro: começar com formas e VFX.
- IP de terceiros: todo conteúdo de Jujutsu fica em `ryoiki/data/` (JSON), para trocar por
  um universo original se um dia for publicar.

## Arquitetura
- **OuroborosEngine** (repo irmão, ECS Data-Oriented, Zero-GC no gameplay). Comportamento
  compartilhado começa na engine, não aqui. Em dev: `pip install -e ../OuroborosEngine`.
- Técnicas, personagens e maldições são dados em `ryoiki/data/`.

## Rodar / testar
```bash
python -m ryoiki     # rodar (ou run.bat)
pytest               # testes
ruff check .         # lint
```

## Convenções
- Pacote em `ryoiki/`, testes em `tests/`, pygame-ce.
- Segue as convenções gerais de [../../CLAUDE.md](../../CLAUDE.md).
- Só commitar quando o Enzo pedir (identidade local EzioMilanoX).
