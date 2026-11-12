# Ryoiki

Acao top-down de Jujutsu: tecnicas montadas por blocos, Kokusen no timing e choque de dominios.

## Jogar

Baixe o `Ryoiki-windows.zip` da página de [Releases](https://github.com/EzioMilanoX/Ryoiki/releases), extraia e abra `Ryoiki/Ryoiki.exe`.

| Ação | Teclado | Controle |
|---|---|---|
| Andar | WASD / setas | direcional |
| Golpe / reforço | botão esquerdo, J / botão direito, L | X / Y |
| Esquiva | Espaço, K | A |
| Técnica 1 / 2 | E / Q | RB / LB |
| Técnica Reversa | R (segurar) | B |
| Domínio / Domínio Simples | F / C (segurar) | Back |
| Trocar técnica | Tab | |
| Pausa | Esc | Start |

## Rodar do código

```bash
pip install -r requirements.txt
python -m ryoiki        # ou: run.bat
```

O executável sai de `python -m PyInstaller ryoiki.spec` (em `dist/Ryoiki/`).

## Desenvolvimento

```bash
pytest            # testes
ruff check .      # lint
ruff format .     # formatação
```

## Estrutura

```
ryoiki/        código do pacote
tests/           testes (pytest)
run.bat          atalho para rodar no Windows
```
