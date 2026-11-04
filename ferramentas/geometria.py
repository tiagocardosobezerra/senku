"""Geometry checker for Senku layout: edges over nodes, overlapping edges, overlapping labels."""
import sys, os
SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SK)
from carta import modelo
from carta.layout import calcular

def segs(pts):
    return list(zip(pts, pts[1:]))

def seg_hits_box(a, b, box, pad=0):
    x0, y0, x1, y1 = box[0]-pad, box[1]-pad, box[2]+pad, box[3]+pad
    (ax, ay), (bx, by) = a, b
    if abs(ay-by) < 0.01:  # horizontal
        if not (y0 < ay < y1): return False
        lo, hi = sorted((ax, bx))
        return hi > x0 and lo < x1
    if abs(ax-bx) < 0.01:
        if not (x0 < ax < x1): return False
        lo, hi = sorted((ay, by))
        return hi > y0 and lo < y1
    return False

def overlap_collinear(s1, s2, tol=1.0):
    (a, b), (c, d) = s1, s2
    if abs(a[1]-b[1]) < .01 and abs(c[1]-d[1]) < .01 and abs(a[1]-c[1]) < tol:
        lo1, hi1 = sorted((a[0], b[0])); lo2, hi2 = sorted((c[0], d[0]))
        return min(hi1, hi2) - max(lo1, lo2) > 4
    if abs(a[0]-b[0]) < .01 and abs(c[0]-d[0]) < .01 and abs(a[0]-c[0]) < tol:
        lo1, hi1 = sorted((a[1], b[1])); lo2, hi2 = sorted((c[1], d[1]))
        return min(hi1, hi2) - max(lo1, lo2) > 4
    return False

def check(path):
    c = modelo.carregar(path)
    lay = calcular(c)
    boxes = {eid: (n['x'], n['y'], n['x']+n['w'], n['y']+n['h']) for eid, n in lay.nos.items()}
    fl = {f['id']: f for f in c.fluxos}
    edge_over_node = []
    for fid, pts in lay.arestas.items():
        f = fl[fid]
        for s in segs(pts):
            for eid, bx in boxes.items():
                if eid in (f['de'], f['para']): continue
                if seg_hits_box(s[0], s[1], bx):
                    edge_over_node.append((fid, f['de'], f['para'], eid))
    # edges through own source/target interior (besides endpoints)
    overl = []
    ids = list(lay.arestas)
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            fi, fj = fl[ids[i]], fl[ids[j]]
            if fi['de'] == fj['de'] or fi['para'] == fj['para']: continue
            if any(overlap_collinear(s1, s2) for s1 in segs(lay.arestas[ids[i]]) for s2 in segs(lay.arestas[ids[j]])):
                overl.append((fi['de']+'->'+fi['para'], fj['de']+'->'+fj['para']))
    # labels: approx bbox 6px/char, 12px high
    lab = []
    for fid, (x, y, anc) in lay.rotulos.items():
        f = fl[fid]
        t = f['rotulo'] + (f' ({f["percentual"]:.0f}%)' if f['percentual'] is not None else '')
        if not t: continue
        w = 6.2*len(t)
        x0 = x - w if anc == 'end' else x
        lab.append((fid, t, (x0, y-10, x0+w, y+2)))
    def inter(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    lab_lab = [(a[1], b[1], fl[a[0]]['para'], fl[b[0]]['para']) for i, a in enumerate(lab) for b in lab[i+1:] if inter(a[2], b[2])]
    lab_node = [(l[1], fl[l[0]]['de']+'->'+fl[l[0]]['para'], eid) for l in lab for eid, bx in boxes.items() if inter(l[2], bx)]
    # node name labels for gateways (above-left) and events (below)
    return dict(n_nodes=len(boxes), n_edges=len(lay.arestas), edge_over_node=edge_over_node, edge_overlap=overl,
                label_label=lab_lab, label_node=lab_node, width=lay.largura, height=lay.altura)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        r = check(p)
        print('==', p)
        for k, v in r.items():
            if isinstance(v, list):
                print(f'  {k}: {len(v)}', v[:8])
            else:
                print(f'  {k}: {v}')

def text_boxes(c, lay):
    """gateway question (above-left, end-anchored at cx-8) and event names (below), as in svg.py"""
    from carta.util import quebrar
    out = []
    for eid, n in lay.nos.items():
        e = c.elementos[eid]
        if not e['nome']: continue
        if e['tipo'] in ('decisao', 'paralelo', 'inclusivo'):
            ls = quebrar(e['nome'], 16)[:3]
            w = max(len(l) for l in ls) * 6.0
            ycen = n['y'] - 6 - (len(ls) - 1) * 13.2 / 2 - 4
            h = len(ls) * 13.2
            out.append((eid, (n['cx'] - 8 - w, ycen - h / 2, n['cx'] - 8, ycen + h / 2)))
        elif e['tipo'] in ('inicio', 'fim', 'evento'):
            ls = quebrar(e['nome'], 20)[:3]
            w = max(len(l) for l in ls) * 6.0
            y0 = n['y'] + n['h'] + 10 + (len(ls) - 1) * 6.5 - 6.6 * len(ls)
            out.append((eid, (n['cx'] - w / 2, y0, n['cx'] + w / 2, y0 + 13.2 * len(ls))))
    return out

def check_text(path):
    c = modelo.carregar(path); lay = calcular(c)
    boxes = {eid: (n['x'], n['y'], n['x']+n['w'], n['y']+n['h']) for eid, n in lay.nos.items()}
    tb = text_boxes(c, lay)
    def inter(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    hits = [(t, eid) for t, bx in tb for eid, b in boxes.items() if eid != t and inter(bx, b)]
    tt = [(a[0], b[0]) for i, a in enumerate(tb) for b in tb[i+1:] if inter(a[1], b[1])]
    # edges crossing name text (excluding the element's own edges)
    fl = {f['id']: f for f in c.fluxos}
    ecross = []
    for t, bx in tb:
        for fid, pts in lay.arestas.items():
            if t in (fl[fid]['de'], fl[fid]['para']): continue
            if any(seg_hits_box(a, b, bx) for a, b in segs(pts)):
                ecross.append((t, fl[fid]['de'] + '->' + fl[fid]['para']))
    # lane-overflow: text above lane top
    return dict(name_over_node=hits, name_over_name=tt, edge_through_name=ecross)

