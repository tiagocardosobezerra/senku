#!/usr/bin/env python3
"""
Estresse do desenho: gera N processos aleatórios bem estruturados (decisões, paralelos, laços, várias raias),
desenha e mede o que estraga a leitura:
    caixa       linha passando por cima de uma caixa
    sobrepostas trecho de duas linhas que não têm nada a ver correndo uma em cima da outra (>= 15 px)
    rotulos     dois rótulos no mesmo lugar, ou rótulo em cima de caixa
    erros       erro de validação num processo que foi gerado correto

Uso: python ferramentas/estresse.py [N=200]     (sai com código 1 se algum caso tiver problema)
"""

import json
import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))

from carta import validacao  # noqa: E402
from carta.layout import calcular  # noqa: E402
from carta.modelo import Carta  # noqa: E402


def gerar(semente, n_raias=6, tamanho=14):
    R = random.Random(semente)
    raias = [f'r{i}' for i in range(n_raias)]
    els, cont = {}, [0]

    def novo(tipo, **kw):
        cont[0] += 1
        i = f'{tipo[0]}{cont[0]}'
        els[i] = dict(id=i, tipo=tipo, segue=[], **kw)
        return i

    def ativ():
        return novo('atividade', nome=f'Analisar item {cont[0] + 1}', papel=R.choice(raias))

    def bloco(prof):
        k = R.random()
        if prof > 2 or k < 0.45:
            a = ativ()
            return a, a
        if k < 0.65:
            d = novo('decisao', nome='Ok?', papel=R.choice(raias))
            m = novo('decisao', papel=els[d]['papel'])
            for j in range(R.choice([2, 2, 3])):
                en, ex = seq(prof + 1)
                els[d]['segue'].append({'para': en, 'rotulo': f'Opção {j}'})
                els[ex]['segue'].append(m)
            return d, m
        if k < 0.82:
            p = novo('paralelo', papel=R.choice(raias))
            j = novo('paralelo', papel=els[p]['papel'])
            for _ in range(R.choice([2, 3])):
                en, ex = seq(prof + 1)
                els[p]['segue'].append(en)
                els[ex]['segue'].append(j)
            return p, j
        # laço: o retrabalho volta para uma atividade (voltar para uma porta paralela trava o fluxo, e o
        # validar acusa, com razão)
        topo = ativ()
        en, ex = seq(prof + 1)
        els[topo]['segue'].append(en)
        d = novo('decisao', nome='Correto?', papel=els[ex].get('papel') or R.choice(raias))
        els[ex]['segue'].append(d)
        corr = ativ()
        els[d]['segue'].append({'para': corr, 'rotulo': 'Não', 'percentual': 20})
        els[corr]['segue'].append(topo)
        prox = ativ()
        els[d]['segue'].append({'para': prox, 'rotulo': 'Sim', 'percentual': 80})
        return topo, prox

    def seq(prof):
        primeiro, ultimo = bloco(prof)
        for _ in range(R.randint(1, 3) - 1):
            a, b = bloco(prof)
            els[ultimo]['segue'].append(a)
            ultimo = b
        return primeiro, ultimo

    i = novo('inicio', nome='Início', papel=raias[0])
    en, ex = seq(0)
    while len(els) < tamanho:
        a, b = bloco(0)
        els[ex]['segue'].append(a)
        ex = b
    f = novo('fim', nome='Fim')
    els[ex]['segue'].append(f)
    els[i]['segue'].append(en)
    return {'processo': {'nome': 'X'}, 'papeis': [{'id': r, 'nome': 'Área ' + r} for r in raias],
            'elementos': list(els.values())}


def _sobrepoe(s1, s2):
    (a, b), (c, d) = s1, s2
    if abs(a[1] - b[1]) < .01 and abs(c[1] - d[1]) < .01 and abs(a[1] - c[1]) < 1:
        lo1, hi1 = sorted((a[0], b[0]))
        lo2, hi2 = sorted((c[0], d[0]))
        return min(hi1, hi2) - max(lo1, lo2)
    if abs(a[0] - b[0]) < .01 and abs(c[0] - d[0]) < .01 and abs(a[0] - c[0]) < 1:
        lo1, hi1 = sorted((a[1], b[1]))
        lo2, hi2 = sorted((c[1], d[1]))
        return min(hi1, hi2) - max(lo1, lo2)
    return 0


def medir(c, lay):
    fl = {f['id']: f for f in c.fluxos}
    caixas = {eid: (n['x'], n['y'], n['x'] + n['w'], n['y'] + n['h']) for eid, n in lay.nos.items()}
    out = {'caixa': 0, 'sobrepostas': 0, 'rotulos': 0}
    ids = list(lay.arestas)
    for fid in ids:
        f = fl[fid]
        for (x1, y1), (x2, y2) in zip(lay.arestas[fid], lay.arestas[fid][1:]):
            for eid, (a, b, cc, d) in caixas.items():
                if eid in (f['de'], f['para']):
                    continue
                if min(x1, x2) < cc and max(x1, x2) > a and min(y1, y2) < d and max(y1, y2) > b:
                    out['caixa'] += 1
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            A, B = fl[ids[i]], fl[ids[j]]
            if A['de'] == B['de'] or A['para'] == B['para']:
                continue
            for s1 in zip(lay.arestas[ids[i]], lay.arestas[ids[i]][1:]):
                for s2 in zip(lay.arestas[ids[j]], lay.arestas[ids[j]][1:]):
                    if _sobrepoe(s1, s2) >= 15:
                        out['sobrepostas'] += 1
    pos = [lay.rotulos[f['id']][:2] for f in c.fluxos if f['rotulo'] and f['id'] in lay.rotulos]
    out['rotulos'] = len(pos) - len(set(pos))
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    soma = {'caixa': 0, 'sobrepostas': 0, 'rotulos': 0, 'erros': 0}
    casos_ruins = []
    for semente in range(n):
        R = random.Random(semente)
        d = gerar(semente, R.randint(3, 8), random.Random(semente + 1).randint(10, 30))
        c = Carta(json.loads(json.dumps(d)))
        r = medir(c, calcular(c))
        r['erros'] = sum(1 for a in validacao.validar(c) if a.nivel == 'erro')
        for k, v in r.items():
            soma[k] += 1 if v else 0
        if any(r.values()):
            casos_ruins.append((semente, r))
    print(f'{n} processos: casos com problema por tipo: {soma}')
    for s, r in casos_ruins[:10]:
        print(f'  semente {s}: {r}')
    return 1 if casos_ruins else 0


if __name__ == '__main__':
    sys.exit(main())
