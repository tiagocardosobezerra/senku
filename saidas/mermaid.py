"""
Flowchart Mermaid: a prévia rápida (no chat, no GitHub, Notion, Confluence, Obsidian, artifact).

Cada raia vira um subgraph. O Mermaid não tem raia de verdade nem controla a posição: para o desenho
oficial use o SVG, o BPMN ou o draw.io. Os nós usam o id da carta, então a pessoa pode apontar
"o a3 está errado" olhando a prévia.
"""

import re

from carta.layout import calcular, numerar
from carta.modelo import SEM_PAPEL
from carta.util import sem_acento


def _t(texto):
    return str(texto).replace('"', '#quot;').replace('\n', ' ').replace('<', '#lt;').replace('>', '#gt;')


def _id(eid):
    s = re.sub(r'[^A-Za-z0-9_]', '_', sem_acento(str(eid)))
    return s if re.match(r'[A-Za-z]', s) and s not in ('end', 'graph', 'subgraph', 'style', 'class') else 'n_' + s


def gerar(c, raias=True, direcao='LR'):
    lay = calcular(c)
    nums = numerar(c, lay)
    L = [f'flowchart {direcao}']
    unicos, usados = {}, set()
    for eid in c.elementos:                         # "ação 1" e "acao_1" não podem virar o mesmo nó
        base = _id(eid)
        x, n = base, 2
        while x.lower() in usados:
            x, n = f'{base}_{n}', n + 1
        usados.add(x.lower())
        unicos[eid] = x

    def _idu(eid):
        return unicos[eid]

    def no(eid):
        e = c.elementos[eid]
        nome = _t(e['nome'] or '')
        t = e['tipo']
        i = _idu(eid)
        if t == 'inicio':
            return f'{i}(["{nome or "Início"}"]):::inicio'
        if t == 'fim' and e['encerra']:
            return f'{i}((("■ {nome or "Fim"}"))):::fim'          # fim terminal: círculo duplo
        if t == 'fim':
            return f'{i}(["{nome or "Fim"}"]):::fim'
        if t in ('evento', 'borda'):
            return f'{i}(("{nome}")):::evento'
        if t == 'decisao':
            return f'{i}{{"{nome or "?"}"}}:::porta'
        if t == 'corrida':
            return f'{i}{{{{"⬠ {nome or "o que vier primeiro"}"}}}}:::porta'      # hexágono: porta por evento
        if t == 'paralelo':
            return f'{i}{{"+"}}:::porta'
        if t == 'inclusivo':
            return f'{i}{{"O"}}:::porta'
        rot = f'{nums.get(eid, "")} {nome}'.strip()
        if t == 'subprocesso':
            return f'{i}[["{rot}"]]:::atividade'
        return f'{i}["{rot}"]:::atividade'

    if raias:
        for k, r in enumerate(lay.raias):
            membros = [eid for eid in c.elementos if lay.nos[eid]['raia'] == r['id']]
            L.append(f'  subgraph R{k}["{_t(r["nome"])}"]')
            L.append(f'    direction {direcao}')
            L += [f'    {no(eid)}' for eid in membros]
            L.append('  end')
    else:
        L += [f'  {no(eid)}' for eid in c.elementos]
    for f in c.fluxos:
        if f['de'] not in c.elementos or f['para'] not in c.elementos:
            continue
        seta = '-.->' if f['id'] in lay.volta or f['borda'] else '-->'
        rot = f['rotulo'] + (f' ({f["percentual"]:.0f}%)' if f['percentual'] is not None else '')
        rot = f'|"{_t(rot)}"|' if rot else ''
        L.append(f'  {_idu(f["de"])} {seta}{rot} {_idu(f["para"])}')
    L += ['  classDef inicio fill:#ffffff,stroke:#2e7d32,stroke-width:2px',
          '  classDef fim fill:#ffffff,stroke:#b3261e,stroke-width:4px',
          '  classDef evento fill:#ffffff,stroke:#a86b00,stroke-width:2px',
          '  classDef porta fill:#fff8e1,stroke:#a86b00',
          '  classDef atividade fill:#ffffff,stroke:#2f4a6d']
    if raias and any(r['id'] == SEM_PAPEL for r in lay.raias):
        L.append('  %% raia "(sem responsável)": falta dizer quem executa')
    return '\n'.join(L) + '\n'
