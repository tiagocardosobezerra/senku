"""Procura "T" no desenho: o canto (ou a ponta) de uma linha encostado no meio de outra linha que não tem nada a
ver com ela. Quem lê vê uma ligação que não existe. Uso: python ferramentas/juncoes.py CARTA [CARTA ...]"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from carta.layout import calcular  # noqa: E402
from carta.modelo import carregar  # noqa: E402


def _no_segmento(p, a, b, tol=1.5):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if abs(x1 - x2) < 0.5:                                   # vertical
        return abs(x - x1) <= tol and min(y1, y2) + tol < y < max(y1, y2) - tol
    if abs(y1 - y2) < 0.5:                                   # horizontal
        return abs(y - y1) <= tol and min(x1, x2) + tol < x < max(x1, x2) - tol
    return False


def juncoes(c, lay):
    """[(fluxo, outro fluxo, ponto)] onde um canto de um fluxo encosta no meio de outro sem relação."""
    fluxos = [f for f in c.fluxos if lay.arestas.get(f['id'])]
    out = []
    for f in fluxos:
        pts = lay.arestas[f['id']]
        for g in fluxos:
            if g is f or g['de'] == f['de'] or g['para'] == f['para']:
                continue                                     # mesma origem ou mesmo destino: junção legítima
            q = lay.arestas[g['id']]
            for p in pts[1:-1]:                              # cantos de f (as pontas ficam nas caixas)
                if any(_no_segmento(p, a, b) for a, b in zip(q, q[1:])):
                    out.append((f['id'], g['id'], p))
                    break
    return out


if __name__ == '__main__':
    for arq in sys.argv[1:]:
        c = carregar(arq)
        lay = calcular(c)
        achados = juncoes(c, lay)
        print(f'{arq}: {len(achados)} junção(ões) em T')
        for f, g, p in achados[:10]:
            print(f'  {f} encosta em {g} em ({p[0]:.0f}, {p[1]:.0f})')
