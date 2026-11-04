"""
O fluxograma em raias, em SVG puro (sem biblioteca, abre em qualquer navegador e entra no documento).

Notação: a mesma do BPMN, para quem lê os dois não estranhar (referencias/notacao.md):
    círculo fino = início · círculo grosso = fim · círculo duplo = evento no meio (espera, mensagem)
    retângulo arredondado = atividade (com o número) · com [+] = subprocesso
    losango vazio = decisão (a pergunta ao lado) · losango com + = paralelo · com o = inclusivo
"""

from xml.sax.saxutils import escape

from carta.layout import COLUNA, calcular, numerar
from carta.util import quebrar

CAB = 150               # largura do cabeçalho da raia
TOPO = 46               # faixa do título
MARGEM = 16
CORES = {
    'texto': '#1d2733', 'suave': '#5b6878', 'linha': '#44546a', 'borda': '#2f4a6d', 'atividade': '#ffffff',
    'raia_par': '#f6f8fb', 'raia_impar': '#ffffff', 'raia_externa': '#eef0f3', 'cab': '#e3e9f2',
    'inicio': '#2e7d32', 'fim': '#b3261e', 'evento': '#a86b00', 'porta': '#fff8e1', 'porta_borda': '#a86b00',
    'VA': '#2e7d32', 'NAV-N': '#a86b00', 'NAV': '#b3261e',
}


def _t(x):
    return escape(str(x), {'"': '&quot;'})


def _texto_multilinha(linhas, cx, cy, tamanho=12, cor=None, peso='normal', ancora='middle'):
    cor = cor or CORES['texto']
    alto = tamanho * 1.2
    y0 = cy - (len(linhas) - 1) * alto / 2 + tamanho * 0.35
    spans = ''.join(f'<tspan x="{cx:.1f}" y="{y0 + i * alto:.1f}">{_t(l)}</tspan>' for i, l in enumerate(linhas))
    # contorno branco por baixo: a linha que passa atrás do rótulo não corta o texto
    return (f'<text font-size="{tamanho}" fill="{cor}" font-weight="{peso}" text-anchor="{ancora}" '
            'stroke="#ffffff" stroke-width="3" paint-order="stroke">'
            f'{spans}</text>')


def colunas_total(lay):
    return round(lay.largura / COLUNA)


def faixas_impressao(c, lay):
    """(cortes, retratos): como o mapa vai para o papel. Word e HTML usam o mesmo corte, então "parte 2 de 5" é
    a mesma figura nos dois. Cada parte tem 5 colunas em página deitada; a parte com tantas raias que a letra
    ficaria abaixo de ~6 pt vira duas ou mais partes de 3 colunas em página em pé. `retratos` diz, parte a
    parte, se a página é em pé."""
    def escala(f, larg, alt):
        t = desenhar(c, lay, faixa=f, parte=(1, 2))
        w = float(t.split('width="', 1)[1].split('"', 1)[0])
        h = float(t.split('height="', 1)[1].split('"', 1)[0])
        return min(1.0, larg * 96 / w, alt * 96 / h)
    paisagem = faixas(lay, por_faixa=5)
    if len(paisagem) == 1:
        return paisagem, [False]
    cortes, retratos = [], []
    for ini, fim in paisagem:
        deitada = escala((ini, fim), 9.9, 6.2)
        if deitada < 0.7 and fim - ini > 3:              # 0,7 da letra de 11,5 px dá ~6 pt no papel
            sub, k = [], ini
            while k < fim - 1:
                sub.append((k, min(fim, k + 3)))
                if k + 3 >= fim:
                    break
                k += 2                                   # repete uma coluna, como entre as partes
            if min(escala(f, 6.5, 9.2) for f in sub) > deitada * 1.15:
                cortes += sub
                retratos += [True] * len(sub)
                continue
        cortes.append((ini, fim))
        retratos.append(False)
    return cortes, retratos


def faixas(lay, por_faixa=6):
    """Cortes de colunas para caber na página: [(0, 6), (5, 11), ...] (uma coluna repete para dar contexto)."""
    n = colunas_total(lay)
    if n <= por_faixa + 2:
        return [(0, n)]
    out, ini = [], 0
    while ini < n - 1:
        fim = min(n, ini + por_faixa)
        out.append((ini, fim))
        if fim == n:
            break
        ini = fim - 1
    return out


RAIA_FINA = 30          # altura da raia sem nada numa parte do mapa


def _comprimir(lay, ini, fim):
    """Cópia do desenho em que as raias sem nenhum elemento nas colunas [ini, fim) ficam finas: num mapa de
    10 raias, cada parte só tem 2 ou 3 com trabalho, e o resto encolheria a página inteira. As linhas que
    atravessam a raia fina só ficam mais curtas (a escala vertical dentro de cada raia é linear)."""
    import copy
    from carta.layout import LINHA
    usadas = {n['raia'] for n in lay.nos.values() if ini <= n['coluna'] < fim}
    # dentro de uma raia com trabalho, a linha da grade sem nada nesta parte também encolhe
    linhas_usadas = {(n['raia'], int(round((n['cy'] - next(r['y'] for r in lay.raias if r['id'] == n['raia']))
                                           // LINHA)))
                     for n in lay.nos.values() if ini <= n['coluna'] < fim}
    faixas_y, por_raia, y_novo = [], [], 0.0
    for r in lay.raias:
        y_ini = y_novo
        if r['id'] not in usadas:
            h = min(r['h'], RAIA_FINA)
            faixas_y.append((r['y'], r['h'], y_novo, h))
            y_novo += h
        else:
            n = max(1, int(round(r['h'] / LINHA)))
            for k in range(n):
                h0 = r['h'] / n
                h = h0 if (r['id'], k) in linhas_usadas else min(h0, RAIA_FINA + 6)
                faixas_y.append((r['y'] + k * h0, h0, y_novo, h))
                y_novo += h
        por_raia.append((y_ini, y_novo - y_ini))
    if all(abs(a[1] - a[3]) < 0.01 for a in faixas_y):
        return lay

    def my(y):
        for y0, h0, y1, h1 in faixas_y:
            if y <= y0 + h0 or (y0, h0, y1, h1) == faixas_y[-1]:
                return y1 + (max(0.0, y - y0) * h1 / h0 if h0 else 0)
        return y
    novo = copy.copy(lay)
    novo.nos = {}
    for eid, n in lay.nos.items():
        m = dict(n)
        m['cy'] = my(n['cy'])
        m['y'] = m['cy'] - n['h'] / 2
        novo.nos[eid] = m
    novo.arestas = {k: [(x, my(y)) for x, y in pts] for k, pts in lay.arestas.items()}
    novo.rotulos = {k: (x, my(y), a) for k, (x, y, a) in lay.rotulos.items()}
    novo.raias = []
    for r, (y1, h1) in zip(lay.raias, por_raia):
        novo.raias.append(dict(r, y=y1, h=h1, fina=r['id'] not in usadas))
    novo.altura = y_novo + max(0.0, lay.altura - sum(a[1] for a in faixas_y))
    return novo


def desenhar(c, lay=None, cores_valor=False, titulo=True, faixa=None, parte=None):
    """O fluxograma inteiro, ou só as colunas de `faixa` (ini, fim) com o cabeçalho das raias repetido: o mapa
    longo vira partes que cabem numa página."""
    lay = lay or calcular(c)
    nums = numerar(c, lay)
    ini, fim = faixa or (0, colunas_total(lay))
    if faixa:
        lay = _comprimir(lay, ini, fim)
    ox, oy = MARGEM + CAB - ini * COLUNA, MARGEM + (TOPO if titulo else 0)
    largura_conteudo = (fim - ini) * COLUNA
    largura = MARGEM + CAB + largura_conteudo + MARGEM
    altura = oy + lay.altura + MARGEM + (34 if cores_valor else 0)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura:.0f} {altura:.0f}" '
         f'width="{largura:.0f}" height="{altura:.0f}" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" '
         f'role="img" aria-label="{_t("Fluxograma: " + c.titulo())}">',
         '<defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{CORES["linha"]}"/></marker></defs>',
         '<rect width="100%" height="100%" fill="#ffffff"/>']
    if titulo:
        cen = c.cenario().upper()
        p.append(f'<text x="{MARGEM}" y="{MARGEM + 20}" font-size="17" font-weight="600" fill="{CORES["texto"]}">'
                 f'{_t(c.titulo())}</text>')
        p.append(f'<text x="{MARGEM}" y="{MARGEM + 37}" font-size="11.5" fill="{CORES["suave"]}">'
                 f'{_t(cen)} · versão {_t(c.processo.get("versao", "—"))} · dono: '
                 f'{_t(c.processo.get("dono") or "a definir")}'
                 + (f' · parte {parte[0]} de {parte[1]}' if parte else '')
                 + (' · ← continua da parte anterior' if parte and parte[0] > 1 else '')
                 + (' · continua na próxima →' if parte and parte[0] < parte[1] else '') + '</text>')
    # raias (o fundo; o cabeçalho vem por cima de tudo, no fim)
    for i, r in enumerate(lay.raias):
        y = oy + r['y']
        fundo = CORES['raia_externa'] if r['tipo'] == 'externo' else (CORES['raia_par'] if i % 2 == 0
                                                                      else CORES['raia_impar'])
        p.append(f'<rect x="{MARGEM + CAB}" y="{y:.1f}" width="{largura_conteudo:.1f}" height="{r["h"]:.1f}" '
                 f'fill="{fundo}" stroke="#c5cfdc" stroke-width="1"/>')
    # numa parte (faixa), só entra o que aparece nela: o arquivo de cada parte fica pequeno
    x_min, x_max = ini * COLUNA - COLUNA, fim * COLUNA + COLUNA

    def visivel(x0, x1):
        return not faixa or (x1 >= x_min and x0 <= x_max)

    # fluxos
    for f in c.fluxos:
        pts = lay.arestas.get(f['id'])
        if not pts or not visivel(min(x for x, _ in pts), max(x for x, _ in pts)):
            continue
        d = 'M' + ' L'.join(f'{x + ox:.1f},{y + oy:.1f}' for x, y in pts)
        tracejado = ' stroke-dasharray="5 4"' if f['id'] in lay.volta else ''
        p.append(f'<path d="{d}" fill="none" stroke="{CORES["linha"]}" stroke-width="1.4"{tracejado} '
                 'marker-end="url(#seta)"/>')
        rot = f['rotulo'] + (f' ({f["percentual"]:.0f}%)' if f['percentual'] is not None else '')
        if rot:
            x, y, ancora = lay.rotulos[f['id']]
            p.append(f'<text x="{x + ox:.1f}" y="{y + oy:.1f}" font-size="11" fill="{CORES["suave"]}" '
                     f'text-anchor="{ancora}" stroke="#ffffff" stroke-width="3" paint-order="stroke">{_t(rot)}</text>')
    # eventos em que uma seta chega por baixo (o nome deles vai para cima)
    por_baixo = set()
    for f in c.fluxos:
        pts = lay.arestas.get(f['id'])
        alvo = lay.nos.get(f['para'])
        if pts and alvo and alvo['tipo'] in ('inicio', 'fim', 'evento') and pts[-1][1] > alvo['cy'] + 1:
            por_baixo.add(f['para'])
    # elementos
    for eid, n in lay.nos.items():
        if not visivel(n['x'] - 200, n['x'] + n['w']):
            continue
        if faixa and not (ini <= n['coluna'] < fim):
            # numa parte, só os elementos das colunas dela: o vizinho de fora, numa raia encolhida, sairia por
            # cima da faixa
            continue
        e = c.elementos[eid]
        x, y, w, h = n['x'] + ox, n['y'] + oy, n['w'], n['h']
        cx, cy = n['cx'] + ox, n['cy'] + oy
        t = e['tipo']
        p.append(f'<g data-id="{_t(eid)}"><title>{_t(_dica(c, e))}</title>')
        if t in ('atividade', 'subprocesso'):
            borda = CORES[e['valor']] if cores_valor and e['valor'] else CORES['borda']
            p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" rx="9" fill="{CORES["atividade"]}" '
                     f'stroke="{borda}" stroke-width="{2 if cores_valor and e["valor"] else 1.5}"/>')
            linhas = _resumir(e['nome'] or eid, 19, 3)
            p.append(_texto_multilinha(linhas, cx, cy + (0 if e['sistema'] else 4), 11.5))
            p.append(f'<text x="{x + 6:.1f}" y="{y + 13:.1f}" font-size="10" font-weight="700" '
                     f'fill="{CORES["suave"]}">{nums.get(eid, "")}</text>')
            if e['sistema']:
                sis = ', '.join(c.nome_sistema(s) for s in e['sistema'])
                sis = sis if len(sis) <= 26 else sis[:25] + '…'
                tem_borda = any(x2.get('anexo') == eid for x2 in c.elementos.values())
                # no subprocesso, acima do [+]; com borda, acima dos círculos que ficam na base da caixa
                ys = y + h - (19 if t == 'subprocesso' else 17 if tem_borda else 5)
                p.append(f'<text x="{cx:.1f}" y="{ys:.1f}" font-size="9" text-anchor="middle" '
                         f'fill="{CORES["suave"]}">{_t(sis)}</text>')
            if t == 'subprocesso':
                p.append(f'<rect x="{cx - 7:.1f}" y="{y + h - 15:.1f}" width="14" height="12" fill="none" '
                         f'stroke="{CORES["borda"]}"/><path d="M{cx - 4:.1f},{y + h - 9:.1f} h8 M{cx:.1f},'
                         f'{y + h - 13:.1f} v8" stroke="{CORES["borda"]}"/>')
        elif t in ('decisao', 'paralelo', 'inclusivo', 'corrida'):
            p.append(f'<path d="M{cx:.1f},{y:.1f} L{x + w:.1f},{cy:.1f} L{cx:.1f},{y + h:.1f} L{x:.1f},{cy:.1f} z" '
                     f'fill="{CORES["porta"]}" stroke="{CORES["porta_borda"]}" stroke-width="1.5"/>')
            if t == 'paralelo':
                p.append(f'<path d="M{cx - 10:.1f},{cy:.1f} h20 M{cx:.1f},{cy - 10:.1f} v20" '
                         f'stroke="{CORES["porta_borda"]}" stroke-width="3"/>')
            elif t == 'corrida':
                # porta por evento: círculo duplo com um pentágono dentro
                p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="12" fill="none" stroke="{CORES["porta_borda"]}" '
                         'stroke-width="1.3"/>'
                         f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9.5" fill="none" stroke="{CORES["porta_borda"]}" '
                         'stroke-width="1.3"/>'
                         f'<path d="M{cx:.1f},{cy - 6:.1f} L{cx + 5.7:.1f},{cy - 1.9:.1f} L{cx + 3.5:.1f},'
                         f'{cy + 4.9:.1f} L{cx - 3.5:.1f},{cy + 4.9:.1f} L{cx - 5.7:.1f},{cy - 1.9:.1f} z" '
                         f'fill="none" stroke="{CORES["porta_borda"]}" stroke-width="1.3"/>')
            elif t == 'inclusivo':
                p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10" fill="none" '
                         f'stroke="{CORES["porta_borda"]}" stroke-width="2.5"/>')
            if e['nome']:
                # a pergunta fica acima e à esquerda (a saída de cima e o rótulo dela ficam livres); se não
                # cabe acima, dentro da raia, vai para baixo e à esquerda. Texto cortado ganha "…" e o "?" fica.
                linhas = _resumir(e['nome'], 18, 3)
                alto = len(linhas) * 13.2
                topo_raia = oy + next(r['y'] for r in lay.raias if r['id'] == n['raia'])
                if y - 8 - alto >= topo_raia + 2:
                    cy_txt = y - 8 - alto / 2 + 6.6
                else:
                    cy_txt = y + h + 6 + alto / 2 - 6.6
                p.append(_texto_multilinha(linhas, cx - 10, cy_txt, 11, CORES['texto'], ancora='end'))
        else:
            r = w / 2
            cor = CORES['inicio'] if t == 'inicio' else CORES['fim'] if t == 'fim' else CORES['evento']
            esp = 1.8 if t == 'inicio' else 4 if t == 'fim' else 1.5
            # borda que não interrompe a atividade: tracejada (como no BPMN)
            traco = ' stroke-dasharray="3 2"' if t == 'borda' and not e['interrompe'] else ''
            p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r - esp / 2:.1f}" fill="#ffffff" stroke="{cor}" '
                     f'stroke-width="{esp}"{traco}/>')
            if t == 'fim' and e['encerra']:
                # fim terminal (encerra tudo): disco cheio dentro, como no BPMN
                p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r - 7:.1f}" fill="{cor}"/>')
            if t in ('evento', 'borda'):
                p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r - (3.5 if t == "borda" else 5):.1f}" '
                         f'fill="none" stroke="{cor}" stroke-width="1.2"{traco}/>')
            if t == 'borda':
                p.append(f'<g transform="translate({cx:.1f},{cy:.1f}) scale(0.62) translate({-cx:.1f},{-cy:.1f})">'
                         f'{_icone(e["gatilho"], cx, cy, cor)}</g>')
                if e['nome']:
                    # rótulos das bordas empilhados embaixo da atividade, um por linha, a partir da esquerda: a
                    # coluna seguinte (pergunta da decisão, rótulos das saídas) fica livre
                    host = lay.nos[e['anexo']]
                    # na mesma ordem dos círculos, da esquerda para a direita (o primeiro círculo fica à direita)
                    irmas = [x2 for x2 in c.elementos if c.elementos[x2].get('anexo') == e['anexo']]
                    k = len(irmas) - 1 - irmas.index(eid)
                    marca = f'{k + 1}' if len(irmas) > 1 else ''
                    if marca:
                        # número junto do círculo e no rótulo: cada rótulo diz de qual borda é
                        p.append(f'<text x="{cx:.1f}" y="{cy - r - 2:.1f}" font-size="8.5" font-weight="700" '
                                 f'text-anchor="middle" fill="{CORES["evento"]}" stroke="#ffffff" stroke-width="2.5" '
                                 f'paint-order="stroke">{marca}</text>')
                    p.append(f'<text x="{host["x"] + ox + 2:.1f}" y="{host["y"] + host["h"] + oy + 22 + 11 * k:.1f}" '
                             f'font-size="9.5" fill="{CORES["evento"]}" stroke="#ffffff" stroke-width="4" '
                             f'paint-order="stroke">{_t((marca + " " if marca else "") + _resumir(e["nome"], 26, 1)[0])}'
                             '</text>')
            else:
                p.append(_icone(e['gatilho'], cx, cy, cor))
            if e['nome'] and t != 'borda' and eid in por_baixo:
                # a seta chega por baixo: o nome vai para cima, para a seta não cortar o texto
                linhas = _resumir(e['nome'], 20, 3)
                p.append(_texto_multilinha(linhas, cx, y - 8 - (len(linhas) - 1) * 6.5, 11, CORES['texto']))
            elif e['nome'] and t != 'borda':
                linhas = _resumir(e['nome'], 20, 3)
                p.append(_texto_multilinha(linhas, cx, y + h + 10 + (len(linhas) - 1) * 6.5, 11, CORES['texto']))
        p.append('</g>')
    # cabeçalho das raias por cima: no corte de uma faixa, o que vem antes some atrás dele
    p.append(f'<rect x="0" y="{oy - 1:.1f}" width="{MARGEM}" height="{lay.altura + 2:.1f}" fill="#ffffff"/>')
    p.append(f'<rect x="{largura - MARGEM:.1f}" y="{oy - 1:.1f}" width="{MARGEM}" height="{lay.altura + 2:.1f}" '
             'fill="#ffffff"/>')
    for i, r in enumerate(lay.raias):
        y = oy + r['y']
        p.append(f'<rect x="{MARGEM}" y="{y:.1f}" width="{CAB:.1f}" height="{r["h"]:.1f}" fill="{CORES["cab"]}" '
                 'stroke="#c5cfdc" stroke-width="1"/>')
        if r.get('fina'):
            # raia sem nada nesta parte: só o nome, numa linha
            p.append(_texto_multilinha(_resumir(r['nome'], 24, 1), MARGEM + CAB / 2, y + r['h'] / 2, 10,
                                       CORES['suave']))
            continue
        nome = quebrar(r['nome'], 18)[:4]
        if r['tipo'] == 'externo':
            nome.append('(externo)')
        p.append(_texto_multilinha(nome, MARGEM + CAB / 2, y + r['h'] / 2, 12.5, peso='600'))
    if cores_valor:
        y = oy + lay.altura + 22
        x = MARGEM + CAB
        for chave, rot in (('VA', 'agrega valor'), ('NAV-N', 'necessária, não agrega'), ('NAV', 'desperdício')):
            p.append(f'<rect x="{x}" y="{y - 10}" width="14" height="12" rx="3" fill="none" stroke="{CORES[chave]}" '
                     f'stroke-width="2"/><text x="{x + 20}" y="{y}" font-size="11" fill="{CORES["suave"]}">'
                     f'{chave}: {rot}</text>')
            x += 210
    p.append('</svg>')
    return '\n'.join(p)


def _icone(gatilho, cx, cy, cor):
    if gatilho == 'tempo':
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" fill="none" stroke="{cor}" stroke-width="1.3"/>'
                f'<path d="M{cx:.1f},{cy - 6:.1f} V{cy:.1f} H{cx + 4:.1f}" fill="none" stroke="{cor}"/>')
    if gatilho == 'mensagem':
        return (f'<rect x="{cx - 8:.1f}" y="{cy - 5:.1f}" width="16" height="11" fill="none" stroke="{cor}"/>'
                f'<path d="M{cx - 8:.1f},{cy - 5:.1f} L{cx:.1f},{cy + 1:.1f} L{cx + 8:.1f},{cy - 5:.1f}" '
                f'fill="none" stroke="{cor}"/>')
    if gatilho == 'condicao':
        return ''.join(f'<path d="M{cx - 6:.1f},{cy - 5 + i * 5:.1f} h12" stroke="{cor}"/>' for i in range(3))
    if gatilho == 'sinal':
        return f'<path d="M{cx:.1f},{cy - 7:.1f} L{cx + 7:.1f},{cy + 5:.1f} L{cx - 7:.1f},{cy + 5:.1f} z" ' \
               f'fill="none" stroke="{cor}"/>'
    if gatilho == 'erro':
        return f'<path d="M{cx - 6:.1f},{cy + 6:.1f} L{cx - 2:.1f},{cy - 6:.1f} L{cx + 2:.1f},{cy + 2:.1f} ' \
               f'L{cx + 6:.1f},{cy - 6:.1f}" fill="none" stroke="{cor}" stroke-width="1.5"/>'
    return ''


def _resumir(texto, largura, max_linhas):
    """Quebra em linhas; se não couber, corta a última com "…" (e mantém o "?" de uma pergunta)."""
    linhas = quebrar(texto, largura)
    if len(linhas) <= max_linhas:
        return linhas
    linhas = linhas[:max_linhas]
    fim = '…?' if str(texto).rstrip().endswith('?') else '…'
    linhas[-1] = linhas[-1][:largura - len(fim)].rstrip() + fim
    return linhas


def _dica(c, e):
    partes = [f'{c.nome(e["id"])}  [id: {e["id"]}]']
    if e['papel']:
        partes.append(f'Responsável: {c.nome_papel(e["papel"])}')
    if e['sistema']:
        partes.append('Sistema: ' + ', '.join(c.nome_sistema(s) for s in e['sistema']))
    if e['descricao']:
        partes.append(e['descricao'])
    if e['tempo_texto']:
        partes.append('Tempo: ' + ', '.join(f'{k} {v}' for k, v in e['tempo_texto'].items()))
    for r in e['regras']:
        if r in c.regras:
            partes.append(f'{r}: {c.regras[r].get("texto", "")}')
    return '\n'.join(partes)
