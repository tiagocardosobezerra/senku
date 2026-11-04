"""
Layout em raias: onde cada elemento fica no desenho.

O fluxo corre da esquerda para a direita; cada papel é uma raia horizontal, na
ordem da carta. A coluna de um elemento é o caminho mais longo desde o início
(sem contar os laços de retrabalho), então tudo que vem depois fica à direita.
Dois elementos da mesma raia na mesma coluna ganham linhas dentro da raia.

As linhas são ortogonais (só horizontal e vertical): para a frente, saem pela
direita e entram pela esquerda; o retrabalho (voltar para trás) sai por baixo,
corre num canal abaixo dos elementos e entra por baixo do destino.

As coordenadas são do conteúdo (a raia começa em x=0); cada saída (BPMN,
draw.io, SVG) soma a largura do cabeçalho da raia.
"""

from .modelo import NOS_DE_TRABALHO, PORTAS

COLUNA = 190            # largura de uma coluna
LINHA = 120             # altura de uma linha dentro da raia
TAMANHOS = {'atividade': (130, 70), 'subprocesso': (130, 70), 'decisao': (50, 50), 'paralelo': (50, 50),
            'inclusivo': (50, 50), 'corrida': (50, 50), 'inicio': (40, 40), 'fim': (40, 40), 'evento': (40, 40)}


class Layout:
    def __init__(self):
        self.nos = {}           # id -> {x, y, w, h, cx, cy, coluna, linha, raia}
        self.raias = []         # {id, nome, y, h, linhas}
        self.arestas = {}       # fluxo id -> [(x, y), ...]
        self.rotulos = {}       # fluxo id -> (x, y) do texto
        self.largura = 0
        self.altura = 0
        self.volta = set()
        self.portas = {}        # fluxo id -> lado de saída (dir, cima, baixo)


def colunas(c):
    """Coluna de cada elemento: caminho mais longo desde um início no grafo sem os laços."""
    volta = c.arestas_de_volta()
    grau = {i: 0 for i in c.elementos}
    for f in c.fluxos:
        if f['id'] not in volta and f['para'] in grau and f['de'] in grau:
            grau[f['para']] += 1
    col = {i: 0 for i in c.elementos}
    fila = [i for i in c.elementos if grau[i] == 0]
    # inícios primeiro, na ordem da carta, para o desenho começar por eles
    fila.sort(key=lambda i: (c.elementos[i]['tipo'] != 'inicio', list(c.elementos).index(i)))
    vistos = []
    while fila:
        x = fila.pop(0)
        vistos.append(x)
        for f in c.saidas[x]:
            d = f['para']
            if f['id'] in volta or d not in grau:
                continue
            col[d] = max(col[d], col[x] + (0 if f.get('borda') else 1))   # a borda fica na coluna da atividade
            grau[d] -= 1
            if grau[d] == 0:
                fila.append(d)
    return col, volta


def calcular(c):
    lay = Layout()
    col, volta = colunas(c)
    lay.volta = volta
    ordem = list(c.elementos)
    raias = c.raias()
    # linha de cada elemento dentro da raia: quem chega primeiro (ordem da carta) fica em cima
    ocupado = {}
    linha = {}
    # o elemento herda a linha do antecessor quando der: o caminho principal fica reto
    for eid in sorted(ordem, key=lambda i: (col[i], ordem.index(i))):
        if c.elementos[eid]['tipo'] == 'borda':
            continue                                   # a borda não ocupa lugar na grade: fica presa na atividade
        r = c.raia_de(eid)
        preferida = 0
        for f in c.entradas[eid]:
            if f['de'] in linha and c.raia_de(f['de']) == r and f['id'] not in volta:
                preferida = linha[f['de']]
                break
        k = preferida
        while (r, col[eid], k) in ocupado:
            k += 1
        if k != preferida and (r, col[eid], 0) not in ocupado:
            k = 0
            while (r, col[eid], k) in ocupado:
                k += 1
        ocupado[(r, col[eid], k)] = eid
        linha[eid] = k
    y = 0
    for r in raias:
        n = max([linha[e] for e in ordem if c.raia_de(e) == r and e in linha] + [0]) + 1
        lay.raias.append({'id': r, 'nome': c.nome_papel(None if r == '_sem_papel' else r), 'y': y,
                          'h': n * LINHA, 'linhas': n,
                          'tipo': (c.papeis.get(r) or {}).get('tipo', 'interno')})
        y += n * LINHA
    topo = {r['id']: r['y'] for r in lay.raias}
    bordas_de = {}
    for eid in ordem:
        e = c.elementos[eid]
        if e['tipo'] == 'borda':
            host = lay.nos.get(e['anexo'])
            if not host:
                continue
            k = bordas_de.get(e['anexo'], 0)
            bordas_de[e['anexo']] = k + 1
            # as bordas se espalham pela borda de baixo da atividade, sem sair dela (5 ou mais ficam mais juntas)
            total = sum(1 for x in c.elementos.values() if x.get('anexo') == e['anexo'])
            passo = min(30.0, (host['w'] - 30) / max(1, total - 1)) if total > 1 else 0
            cx, cy = host['x'] + host['w'] - 15 - passo * k, host['y'] + host['h']
            d = max(14.0, min(24.0, passo - 3)) if total > 1 else 24.0     # muitas bordas: círculos menores
            lay.nos[eid] = {'x': cx - d / 2, 'y': cy - d / 2, 'w': d, 'h': d, 'cx': cx, 'cy': cy,
                            'coluna': host['coluna'], 'linha': host['linha'], 'raia': host['raia'], 'tipo': 'borda',
                            'anexo': e['anexo']}
            continue
        w, h = TAMANHOS[e['tipo']]
        cx = col[eid] * COLUNA + COLUNA / 2
        cy = topo[c.raia_de(eid)] + linha[eid] * LINHA + LINHA / 2
        lay.nos[eid] = {'x': cx - w / 2, 'y': cy - h / 2, 'w': w, 'h': h, 'cx': cx, 'cy': cy,
                        'coluna': col[eid], 'linha': linha[eid], 'raia': c.raia_de(eid), 'tipo': e['tipo']}
    lay.largura = (max(col.values()) + 1) * COLUNA if col else COLUNA
    lay.altura = y
    _rotear(c, lay)
    return lay


_DESLOCA_V = (0, 7, -7, 14, -14, 21, -21, 26, -26)
_DESLOCA_H = (8, -8, 15, -15, 22, -22)
# corredor com um lado só: deslocamentos todos diferentes e menores que a folga até a caixa (25 px)
_UM_LADO = (5, 10, 15, 20, 3, 8, 13, 18, 22)              # nunca 0: a divisa entre linhas é a linha da raia


def _portas(c, lay):
    """Por qual lado cada fluxo sai: 'dir', 'cima' ou 'baixo'. Numa porta com várias saídas, cada saída ganha
    um lado (para cima o que vai para cima, para baixo o que vai para baixo), e o rótulo fica junto da porta.
    Quando os três lados já estão ocupados, a saída extra divide a direita e o rótulo vai para perto do destino."""
    porta, rotulo_no_destino = {}, set()
    for eid, a in lay.nos.items():
        saidas = [f for f in c.saidas[eid] if f['para'] in lay.nos]
        if not saidas:
            continue
        saidas = [f for f in saidas if not f['borda']]
        if a['tipo'] == 'borda':
            for f in saidas:
                porta[f['id']] = 'baixo'               # da borda, o caminho da exceção desce
            continue
        if a['tipo'] not in PORTAS or len(saidas) < 2:
            for f in saidas:
                b = lay.nos[f['para']]
                volta = f['id'] in lay.volta or b['coluna'] <= a['coluna']
                porta[f['id']] = 'baixo' if volta else 'dir'
            continue
        livres = {'dir', 'cima', 'baixo'}

        def preferida(f):
            b = lay.nos[f['para']]
            if f['id'] in lay.volta or b['coluna'] <= a['coluna']:
                return 'baixo', 0
            dy = b['cy'] - a['cy']
            return ('dir' if abs(dy) < 1 else 'cima' if dy < 0 else 'baixo'), abs(dy)
        alternativas = {'cima': ('dir', 'baixo'), 'baixo': ('dir', 'cima'), 'dir': ('baixo', 'cima')}
        for f in sorted(saidas, key=lambda f: (preferida(f)[1], f['id'])):
            p, _ = preferida(f)
            escolha = p if p in livres else next((x for x in alternativas[p] if x in livres), None)
            if escolha is None:
                escolha = 'dir'
                rotulo_no_destino.add(f['id'])
            livres.discard(escolha)
            porta[f['id']] = escolha
        # duas saídas para o mesmo lado (as duas para baixo, uma pela direita e outra por baixo): a que sai por
        # baixo tem de ir para o destino mais à esquerda, senão as linhas se cruzam
        for lado in ('baixo', 'cima'):
            por_lado = [f for f in saidas if porta.get(f['id']) == lado and f['id'] not in lay.volta]
            pela_dir = [f for f in saidas if porta.get(f['id']) == 'dir' and f['id'] not in lay.volta]
            for f in por_lado:
                b = lay.nos[f['para']]
                mesmo_sentido = (b['cy'] > a['cy'] + 1) if lado == 'baixo' else (b['cy'] < a['cy'] - 1)
                for g in pela_dir:
                    bg = lay.nos[g['para']]
                    g_sentido = (bg['cy'] > a['cy'] + 1) if lado == 'baixo' else (bg['cy'] < a['cy'] - 1)
                    if mesmo_sentido and g_sentido and b['coluna'] > bg['coluna']:
                        porta[f['id']], porta[g['id']] = 'dir', lado
    return porta, rotulo_no_destino


def _limpar_linha(pts):
    """Tira ponto repetido e ponto no meio de um trecho reto: o canto que sobra é canto de verdade."""
    out = []
    for p in pts:
        if out and abs(p[0] - out[-1][0]) < 0.05 and abs(p[1] - out[-1][1]) < 0.05:
            continue
        if len(out) >= 2:
            (x1, y1), (x2, y2) = out[-2], out[-1]
            if (abs(x1 - x2) < 0.05 and abs(x2 - p[0]) < 0.05) or (abs(y1 - y2) < 0.05 and abs(y2 - p[1]) < 0.05):
                out[-1] = p                              # três pontos na mesma reta: o do meio sai
                continue
        out.append(p)
    return out


def _rotear(c, lay):
    """Linhas só por corredores: entre colunas (vertical) e entre linhas da grade (horizontal). Como nenhuma
    caixa fica num corredor, nenhuma linha passa por cima de uma caixa. Cada linha no mesmo corredor ganha
    um deslocamento próprio. Quem vem de outra linha entra no destino por cima ou por baixo, e só quem vem da
    mesma linha entra pela esquerda: assim duas linhas nunca se emendam numa ligação que não existe."""
    ocupado_v, ocupado_h = {}, {}
    n_linhas = max(1, round(lay.altura / LINHA))
    na_linha = {}
    for eid, n in lay.nos.items():
        na_linha.setdefault(round(n['cy']), []).append(n['coluna'])

    def corredor_v(col_borda):
        k = ocupado_v.get(col_borda, 0)
        ocupado_v[col_borda] = k + 1
        d = _DESLOCA_V[k % len(_DESLOCA_V)]
        if col_borda == 0:                                   # à esquerda só há o cabeçalho da raia
            return _UM_LADO[k % len(_UM_LADO)] + 2       # um lado só: cada linha com o seu deslocamento
        return col_borda * COLUNA + d

    def corredor_h(k_borda):
        k = ocupado_h.get(k_borda, 0)
        ocupado_h[k_borda] = k + 1
        d = _DESLOCA_H[k % len(_DESLOCA_H)]
        # corredor de um lado só (topo, fundo, abaixo das bordas): abs(d) faria 8 e -8 caírem na mesma linha, e
        # duas setas se emendariam num "T" que não existe; cada uma ganha o seu deslocamento
        u = _UM_LADO[k % len(_UM_LADO)]
        if k_borda <= 0:
            return u
        if k_borda >= n_linhas:
            if (k_borda - 1) in linhas_com_borda:
                lay.altura_extra = max(getattr(lay, 'altura_extra', 0), u + 6)
                return n_linhas * LINHA + u                   # abaixo das bordas da última linha
            return n_linhas * LINHA - u
        if (k_borda - 1) in linhas_com_borda:
            return k_borda * LINHA + u                        # as bordas descem até a divisa: passa por baixo delas
        return k_borda * LINHA + d

    com_bordas = {n['anexo'] for n in lay.nos.values() if n['tipo'] == 'borda'}
    linhas_com_borda = {int(lay.nos[n['anexo']]['cy'] // LINHA) for n in lay.nos.values()
                        if n['tipo'] == 'borda' and n.get('anexo') in lay.nos}

    def linha(n):
        return int(n['cy'] // LINHA)

    portas, no_destino = _portas(c, lay)
    extras = {}
    for f in c.fluxos:
        if f['borda']:
            continue                                   # atividade -> borda: a borda já está desenhada presa nela
        a, b = lay.nos.get(f['de']), lay.nos.get(f['para'])
        if not a or not b:
            continue
        porta = portas.get(f['id'], 'dir')
        topo_a, base_a = a['cy'] - a['h'] / 2, a['cy'] + a['h'] / 2
        topo_b, base_b = b['cy'] - b['h'] / 2, b['cy'] + b['h'] / 2
        a_dir, b_esq = a['cx'] + a['w'] / 2, b['cx'] - b['w'] / 2
        volta = f['id'] in lay.volta or b['coluna'] <= a['coluna']
        b_acima = b['cy'] < a['cy'] - 1
        if porta == 'dir':
            inicio = (a_dir, a['cy'])
            rot = (a_dir + 4, a['cy'] - 6, 'start')
        elif porta == 'cima':
            inicio = (a['cx'], topo_a)
            rot = (a['cx'] + 5, topo_a - 6, 'start')
        else:
            inicio = (a['cx'], base_a)
            rot = (a['cx'] + 5, base_a + 13, 'start')
        if volta:
            # retrabalho: corre no corredor de baixo (ou de cima) e entra por baixo (ou por cima) do destino.
            # Na caixa, sai e entra um pouco fora do centro: o centro é de quem chega pela frente.
            desce = porta != 'cima'
            if a['tipo'] in NOS_DE_TRABALHO:
                inicio = (a['cx'] + 42, inicio[1])
                rot = (inicio[0] + 5, rot[1], 'start')
            ka = linha(a) + 1 if desce else linha(a)
            kb = linha(b) + 1 if desce else linha(b)
            ya = corredor_h(ka)
            borda_b = base_b if desce else topo_b
            # na caixa, o retrabalho entra à esquerda do centro: o centro é de quem sai da porta de baixo, na
            # mesma coluna (senão as duas linhas se emendam num "T")
            bx = b['cx'] - 30 if b['tipo'] in NOS_DE_TRABALHO else b['cx']
            if desce and f['para'] in com_bordas:
                # a parte de baixo da atividade é das bordas: o retrabalho entra por cima
                kb, borda_b = linha(b), topo_b
            if ka == kb:
                pts = [inicio, (inicio[0], ya), (bx, ya), (bx, borda_b)]
            else:
                x2 = corredor_v(b['coluna'])
                yb = corredor_h(kb)
                pts = [inicio, (inicio[0], ya), (x2, ya), (x2, yb), (bx, yb), (bx, borda_b)]
        elif porta == 'dir':
            mesma = abs(a['cy'] - b['cy']) < 1
            livre = mesma and not any(a['coluna'] < k < b['coluna'] for k in na_linha.get(round(a['cy']), []))
            if livre:
                pts = [inicio, (b_esq, b['cy'])]
            elif mesma:
                # mesma linha, com caixa no meio: contorna por baixo e entra por baixo
                x1 = corredor_v(a['coluna'] + 1)
                y = corredor_h(linha(b) + 1)
                pts = [inicio, (x1, a['cy']), (x1, y), (b['cx'], y), (b['cx'], base_b)]
            else:
                x1 = corredor_v(a['coluna'] + 1)
                kb = linha(b) + 1 if b_acima else linha(b)
                y = corredor_h(kb)
                borda_b = base_b if b_acima else topo_b
                pts = [inicio, (x1, a['cy']), (x1, y), (b['cx'], y), (b['cx'], borda_b)]
        else:
            sobe = porta == 'cima'
            ka = linha(a) if sobe else linha(a) + 1
            ya = corredor_h(ka)
            # destino acima entra por baixo; abaixo, por cima; na mesma linha, pelo lado da saída
            if b_acima:
                kb, borda_b = linha(b) + 1, base_b
            elif b['cy'] > a['cy'] + 1:
                kb, borda_b = linha(b), topo_b
            else:
                kb, borda_b = ka, (topo_b if sobe else base_b)
            if kb == ka:
                pts = [inicio, (a['cx'], ya), (b['cx'], ya), (b['cx'], borda_b)]
            else:
                x2 = corredor_v(b['coluna'])
                yb = corredor_h(kb)
                pts = [inicio, (a['cx'], ya), (x2, ya), (x2, yb), (b['cx'], yb), (b['cx'], borda_b)]
        if (not volta and f['para'] in com_bordas and len(pts) > 2 and abs(pts[-1][1] - base_b) < 0.5
                and abs(pts[-1][0] - b['cx']) < 0.5):
            # a parte de baixo da atividade é das bordas: quem chega por baixo sobe no corredor da esquerda e
            # entra pelo lado, um pouco abaixo do centro (o centro é de quem vem da mesma linha)
            x2 = corredor_v(b['coluna'])
            y_corr = pts[-2][1]
            pts = pts[:-2] + [(x2, y_corr), (x2, b['cy'] + 10), (b_esq, b['cy'] + 10)]
        elif not volta and b['tipo'] in NOS_DE_TRABALHO and len(pts) > 2 and abs(pts[-1][0] - b['cx']) < 0.5:
            (x_pen, y_pen), (x_fim, y_fim) = pts[-2], pts[-1]
            if abs(x_pen - x_fim) < 0.5:                          # chega na vertical, por cima ou por baixo
                # vagas na caixa: por cima chega à esquerda do centro, por baixo à direita; o centro de baixo é do
                # retrabalho que volta e a ponta direita de baixo, do retrabalho que sai. Assim, duas caixas
                # empilhadas nunca usam a mesma vertical no corredor entre elas.
                dx = -20 if y_fim < b['cy'] else 20
                pts[-2] = (b['cx'] + dx, y_pen)
                pts[-1] = (b['cx'] + dx, y_fim)
        if not volta and b['tipo'] in PORTAS and len(pts) > 2 and abs(pts[-1][0] - b['cx']) < 0.5:
            # na porta, cima e baixo são saídas: quem chega entra sempre pela ponta da esquerda
            y_corr = pts[-2][1]
            x2 = corredor_v(b['coluna'])
            pts = pts[:-2] + [(x2, y_corr), (x2, b['cy']), (b_esq, b['cy'])]
        if f['id'] in no_destino:
            # saída extra (os três lados já tinham dono): o rótulo vai no começo do trecho vertical, perto da porta
            xv = pts[1][0]
            desce = len(pts) > 2 and pts[2][1] > pts[1][1]
            k = extras.get((f['de'], desce), 0)
            extras[(f['de'], desce)] = k + 1
            rot = (xv - 4, a['cy'] + (18 + 13 * k if desce else -10 - 13 * k), 'end')
        lay.arestas[f['id']] = _limpar_linha([(round(x, 1), round(y, 1)) for x, y in pts])
        lay.rotulos[f['id']] = (round(rot[0], 1), round(rot[1], 1), rot[2])
        lay.portas[f['id']] = porta
    _separar(lay, c.fluxos)
    for fid in lay.arestas:
        lay.arestas[fid] = _limpar_linha(lay.arestas[fid])
    _afastar_rotulos(c, lay)
    extra = getattr(lay, 'altura_extra', 0)
    if extra and lay.raias:                                # corredor abaixo das bordas da última linha
        lay.raias[-1]['h'] += extra
        lay.altura += extra


def _toca(p, trecho, tol=1.5):
    """O ponto p cai no meio (não na ponta) do trecho (i, 'h'|'v', posição, ini, fim)?"""
    _, o, k, a, b = trecho
    x, y = p
    if o == 'h':
        return abs(y - k) <= tol and a + tol < x < b - tol
    return abs(x - k) <= tol and a + tol < y < b - tol


def _caixa_rotulo(c, f, pos):
    x, y, ancora = pos
    texto = f['rotulo'] + (f' ({f["percentual"]:.0f}%)' if f['percentual'] is not None else '')
    w = 6.2 * len(texto)
    x0 = x if ancora == 'start' else x - w if ancora == 'end' else x - w / 2
    return x0, y - 10, x0 + w, y + 3


def _corta(caixa, a, b):
    x0, y0, x1, y1 = caixa
    (ax, ay), (bx, by) = a, b
    if abs(ay - by) < 0.5:
        return y0 < ay < y1 and min(ax, bx) < x1 and max(ax, bx) > x0
    return x0 < ax < x1 and min(ay, by) < y1 and max(ay, by) > y0


def _afastar_rotulos(c, lay):
    """Rótulo de saída ("Sim (80%)") cortado por outra linha fica ilegível: tenta posições perto (acima,
    abaixo, do outro lado) e fica com a primeira em que nenhuma outra linha nem caixa passa por cima."""
    caixas = [(n['x'], n['y'], n['x'] + n['w'], n['y'] + n['h']) for n in lay.nos.values()]

    def ruim(f, pos):
        cx = _caixa_rotulo(c, f, pos)
        for g in c.fluxos:
            if g['id'] == f['id'] or g['id'] not in lay.arestas:
                continue
            pts = lay.arestas[g['id']]
            if any(_corta(cx, a, b) for a, b in zip(pts, pts[1:])):
                return True
        return any(cx[0] < k[2] and cx[2] > k[0] and cx[1] < k[3] and cx[3] > k[1] for k in caixas)
    for f in c.fluxos:
        if not (f['rotulo'] or f['percentual'] is not None) or f['id'] not in lay.rotulos:
            continue
        pos = lay.rotulos[f['id']]
        if not ruim(f, pos):
            continue
        x, y, ancora = pos
        outro = {'start': 'end', 'end': 'start', 'middle': 'middle'}[ancora]
        dx = -8 if ancora == 'start' else 8
        for cand in ((x, y - 14, ancora), (x, y + 14, ancora), (x + dx, y, outro), (x, y - 28, ancora),
                     (x, y + 28, ancora), (x + dx, y - 14, outro), (x + dx, y + 14, outro)):
            if not ruim(f, cand):
                lay.rotulos[f['id']] = cand
                break


def _separar(lay, fluxos):
    """Duas linhas no mesmo trecho parecem uma só (ou parecem ligar o que não está ligado). Para cada
    sobreposição, desloca um trecho de uma das linhas dentro do corredor (o próprio trecho, se for do meio;
    o trecho vertical vizinho, se for a ponta que sai ou que chega numa caixa) e fica com a mudança só se ela
    diminuir as sobreposições sem encostar em caixa."""
    caixas = [(n['x'] - 2, n['y'] - 2, n['x'] + n['w'] + 2, n['y'] + n['h'] + 2) for n in lay.nos.values()]
    de = {f['id']: f['de'] for f in fluxos}
    para = {f['id']: f['para'] for f in fluxos}

    def trechos(fid):
        pts = lay.arestas[fid]
        out = []
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            if abs(y1 - y2) < 0.5:
                out.append((i, 'h', y1, min(x1, x2), max(x1, x2)))
            elif abs(x1 - x2) < 0.5:
                out.append((i, 'v', x1, min(y1, y2), max(y1, y2)))
        return out

    def legitimo(a, b, ta, tb, na, nb):
        """Mesma origem saindo junto, ou mesmo destino chegando junto: é o desenho de uma porta, não erro."""
        if de[a] == de[b] and ta[0] == 0 and tb[0] == 0:
            return True
        if para[a] == para[b] and ta[0] == na - 2 and tb[0] == nb - 2:
            return True
        return de[a] == de[b] or para[a] == para[b]

    def conflitos_de(fid, todos):
        n = 3 * len(cruza_bordas(fid))                     # passar por cima de uma borda pesa mais
        ta_lista = trechos(fid)
        na = len(lay.arestas[fid])
        for outro, tb_lista in todos.items():
            if outro == fid:
                continue
            nb = len(lay.arestas[outro])
            for ta in ta_lista:
                for tb in tb_lista:
                    if ta[1] != tb[1] or abs(ta[2] - tb[2]) >= 4:
                        continue
                    if min(ta[4], tb[4]) - max(ta[3], tb[3]) <= 2:
                        continue
                    if legitimo(fid, outro, ta, tb, na, nb):
                        continue
                    n += 1
            # "T": um canto de uma linha encostado no meio da outra parece uma ligação que não existe
            if de[fid] != de[outro] and para[fid] != para[outro]:
                for p in lay.arestas[fid][1:-1]:
                    if any(_toca(p, tb) for tb in tb_lista):
                        n += 1
                for p in lay.arestas[outro][1:-1]:
                    if any(_toca(p, ta) for ta in ta_lista):
                        n += 1
        return n

    bordas = [(n['x'] - 1, n['y'] - 1, n['x'] + n['w'] + 1, n['y'] + n['h'] + 1, eid)
              for eid, n in lay.nos.items() if n['tipo'] == 'borda']

    def cruza_bordas(fid):
        out = []
        for _, o, k, a, b in trechos(fid):
            for x0, y0, x1, y1, eid in bordas:
                if eid in (de[fid], para[fid]):
                    continue
                if (o == 'h' and y0 < k < y1 and a < x1 and b > x0) or (o == 'v' and x0 < k < x1 and a < y1
                                                                         and b > y0):
                    out.append(eid)
        return out

    def cruza_caixa(fid):
        for _, o, k, a, b in trechos(fid)[1:-1]:
            for x0, y0, x1, y1 in caixas:
                if o == 'h' and y0 < k < y1 and a < x1 and b > x0:
                    return True
                if o == 'v' and x0 < k < x1 and a < y1 and b > y0:
                    return True
        return False

    def mover(fid, i, d):
        pts = lay.arestas[fid]
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        if abs(y1 - y2) < 0.5:
            pts[i], pts[i + 1] = (x1, y1 + d), (x2, y2 + d)
        else:
            pts[i], pts[i + 1] = (x1 + d, y1), (x2 + d, y2)

    for _ in range(4):                                  # algumas passadas: um ajuste pode abrir espaço para outro
        todos = {fid: trechos(fid) for fid in lay.arestas}
        mudou = False
        for fid in list(lay.arestas):
            atual = conflitos_de(fid, todos)
            if not atual:
                continue
            n = len(lay.arestas[fid])
            candidatos = [i for i in range(1, n - 2)]   # só trechos do meio (as pontas ficam presas nas caixas)
            melhor = (atual, None)
            for i in candidatos:
                for d in (7, -7, 14, -14, 21, -21, 28, -28, 35, -35, 42, -42):
                    mover(fid, i, d)
                    todos[fid] = trechos(fid)
                    if not cruza_caixa(fid):
                        nota = conflitos_de(fid, todos)
                        if nota < melhor[0]:
                            melhor = (nota, (i, d))
                    mover(fid, i, -d)
                    todos[fid] = trechos(fid)
            if melhor[1]:
                mover(fid, *melhor[1])
                todos[fid] = trechos(fid)
                mudou = True
        if not mudou:
            break


def numerar(c, lay):
    """Número de cada atividade (01, 02...) na ordem em que acontece: primeiro o fluxo normal (tudo que leva a
    um fim bom sem retrabalho e sem borda), pela coluna do desenho, que segue o tempo (ramos de paralelo e
    caminhos alternativos se intercalam onde acontecem; no empate, o caminho feliz vem antes); depois as
    exceções e correções, na ordem de leitura do desenho (coluna, raia, linha). É a sequência do POP."""
    from .analise import _chega_bem, caminho_feliz
    ordem_raia = {r['id']: i for i, r in enumerate(lay.raias)}
    caminho, paralelos = caminho_feliz(c)
    posicao = {x: i for i, x in enumerate(caminho + paralelos)}
    volta = c.arestas_de_volta()
    bem = _chega_bem(c, volta)
    # alcançáveis do início sem passar por borda nem retrabalho
    normal, pilha = set(), [e['id'] for e in c.de_tipo('inicio')]
    while pilha:
        x = pilha.pop()
        if x in normal or x not in c.elementos:
            continue
        normal.add(x)
        pilha.extend(f['para'] for f in c.saidas[x] if not f['borda'] and f['id'] not in volta)
    trabalho = [eid for eid, n in lay.nos.items() if n['tipo'] in NOS_DE_TRABALHO]

    def chave(e):
        n = lay.nos[e]
        if e in posicao or (e in normal and e in bem):
            return (0, n['coluna'], posicao.get(e, len(posicao)), ordem_raia[n['raia']], n['linha'])
        return (1, n['coluna'], 0, ordem_raia[n['raia']], n['linha'])
    trabalho.sort(key=chave)
    largura = max(2, len(str(len(trabalho))))
    return {eid: str(i).zfill(largura) for i, eid in enumerate(trabalho, 1)}
