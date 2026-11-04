#!/usr/bin/env python3
"""
Empacota a skill num .zip para subir no claude.ai (área de Skills das configurações). Leva só o que a skill
usa: nada de git, cache, testes, saídas geradas, aceites locais nem zip dentro de zip.

Num clone git, só entra arquivo rastreado (`git ls-files`): mapeamento real deixado na pasta nunca vai junto.

Uso:
    python ferramentas/empacotar.py [-o senku-skill.zip]   (padrão: senku-skill-<versão>.zip na pasta da skill)
"""

import argparse
import os
import subprocess
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from carta import VERSAO  # noqa: E402

PASTAS_FORA = {'.git', '.github', '__pycache__', 'saida', 'local', 'testes', 'ferramentas', '.claude', '.ruff_cache',
               'assets', 'roteiros'}
ARQUIVOS_FORA = {'.gitignore', 'ruff.toml'}


def fica_de_fora(rel):
    partes = rel.split('/')
    nome = partes[-1]
    return (any(p in PASTAS_FORA for p in partes[:-1]) or nome in ARQUIVOS_FORA
            or nome.endswith(('.pyc', '.aprovacao.json', '.zip')))


def arquivos_da_skill():
    try:
        saida = subprocess.run(['git', 'ls-files'], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
        lista = [x.strip() for x in saida.splitlines() if x.strip()]
        if lista:
            return sorted(x for x in lista if not fica_de_fora(x))
    except (OSError, subprocess.CalledProcessError):
        pass
    out = []
    for raiz, pastas, arquivos in os.walk(RAIZ):
        pastas[:] = [p for p in pastas if p not in PASTAS_FORA]
        for a in arquivos:
            rel = os.path.relpath(os.path.join(raiz, a), RAIZ).replace(os.sep, '/')
            if not fica_de_fora(rel):
                out.append(rel)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description='Empacota o Senku para o claude.ai')
    ap.add_argument('-o', default=os.path.join(RAIZ, f'senku-skill-{VERSAO}.zip'))
    a = ap.parse_args()
    arquivos = arquivos_da_skill()
    if 'SKILL.md' not in arquivos:
        print('✗ SKILL.md não está na lista (fora do git?)')
        return 1
    with zipfile.ZipFile(a.o, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in arquivos:
            z.write(os.path.join(RAIZ, rel), 'senku/' + rel)
    print(f'✓ {a.o}: {len(arquivos)} arquivos')
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
