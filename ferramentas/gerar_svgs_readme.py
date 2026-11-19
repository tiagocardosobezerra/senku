"""
Gera as imagens animadas do topo do README e da seção da simulação (pt-BR e inglês).

    python ferramentas/gerar_site.py          # primeiro: o fluxograma escuro e os dados da página
    python ferramentas/gerar_svgs_readme.py   # depois: assets/readme/*.svg

Cada SVG é autossuficiente: fontes embutidas (Inter, Poppins e JetBrains Mono, licença OFL, de
`animacoes_fontes.css`), sem script. As fichas andam pelas setas reais do exemplo de compras com
`animateMotion`; com movimento reduzido, somem e fica o quadro parado. Os números vêm de `docs/dados.js`.
"""
import json
import os
import re
from html import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'animacoes_fontes.css')
FLUXO = os.path.join(RAIZ, 'docs', 'img', 'fluxo-compras.svg')
DADOS = os.path.join(RAIZ, 'docs', 'dados.js')
SAIDA = os.path.join(RAIZ, 'assets', 'readme')

LIMA, VERDE, AMBAR, TINTA, MUDO, APAGADO, FUNDO, PAINEL, LINHA, LINHA2 = (
    '#A3E635', '#34D399', '#F59E0B', '#F1F5F9', '#A3B1C6', '#64748B', '#0B1220', '#111C30', '#1E2A44', '#2A3B5C')

TEXTOS = {
    'pt': {
        'alt': 'Senku: antes de desenhar o processo, prove que ele anda. Fichas percorrem o fluxograma em raias do '
               'exemplo de compras; o validar diz "Nenhum problema" e a simulação de 4.000 casos mostra que 80% das '
               'compras levam até 17,2 dias úteis, com prazo combinado de 10.',
        'kicker': '// skill de código aberto para o Claude Code',
        'h1': ['Antes de desenhar', 'o processo, {prove}', 'que ele anda.'], 'prove': 'prove',
        'sub': ['Conte como o trabalho anda. Receba o fluxograma', 'em raias BPMN 2.0 e o mapeamento completo,',
                'provados e prontos para o dono aprovar.'],
        'chips': ['73 verificações', '4.000 casos simulados', '0 dependências'],
        # onde o "prove" começa e quanto mede, em Poppins 800 de 54 px (medido no navegador com getStartPositionOfChar)
        'pv_x': (376, 157),
        'janela': 'SUP-01 · Compra de materiais indiretos', 'fichas': 'fichas',
        'ok': '✓ Nenhum problema.', 'ok_meta': '20 elementos · 22 fluxos · 6 raias',
        'sim': 'simulação · 4.000 casos', 'dias': 'dias úteis',
        'sim_txt': ['para 80% das compras terminarem.', 'O prazo combinado é 10.'],
        'rodape': 'senku · não desenha no chute. prova.',
        # simulação
        's_alt': 'Histograma de 4.000 casos simulados do exemplo de compras. 78% terminam em 14 dias úteis, 12% em '
                 '17, 6% em 18 e o resto entre 20 e 27. Metade termina em até 14,1 dias úteis, 80% em até 17,2 e '
                 '90% em até 18,4. O prazo combinado é de 10 dias úteis e nenhum caso fica dentro dele.',
        's_titulo': 'Quanto tempo uma compra leva, do pedido à entrega',
        's_sub': 'Exemplo SUP-01 · 4.000 casos simulados com os tempos da entrevista · dias úteis',
        's_prazo': ['prazo combinado: 10 dias', '{n} de 4.000 casos dentro dele'],
        's_ate': '{p} até {v}',
        's_kpis': [('{p50} d', 'metade das compras', 'termina em até isso'),
                   ('{ef}%', 'eficiência: {ex} h de', 'trabalho em {lt} dias'),
                   ('{esp} d', 'parados esperando,', 'no caso típico'),
                   ('{pas}', 'passagens de bastão', 'entre áreas')],
        's_nota': 'Os tempos são estimativas da entrevista, não medição: o Senku avisa para confirmar antes de decidir.',
    },
    'en': {
        'alt': 'Senku: before you draw the process, prove that it flows. Tokens run through the swimlane flowchart '
               'of the purchasing example; validate says "No problems" and a 4,000-case simulation shows 80% of '
               'purchases take up to 17.2 business days, against an agreed deadline of 10.',
        'kicker': '// open-source skill for Claude Code',
        'h1': ['Before you draw', 'the process, {prove}', 'that it flows.'], 'prove': 'prove',
        'sub': ['Describe how the work flows. Get a BPMN 2.0', 'swimlane flowchart and the full process map,',
                'proven and ready for the owner to sign off.'],
        'chips': ['73 checks', '4,000 simulated cases', '0 dependencies'],
        'pv_x': (399, 157),
        'janela': 'SUP-01 · Indirect materials purchasing', 'fichas': 'tokens',
        'ok': '✓ No problems.', 'ok_meta': '20 elements · 22 flows · 6 lanes',
        'sim': 'simulation · 4,000 cases', 'dias': 'business days',
        'sim_txt': ['for 80% of purchases to finish.', 'The agreed deadline is 10.'],
        'rodape': 'senku · no guesswork. proof.',
        's_alt': 'Histogram of 4,000 simulated cases of the purchasing example. 78% finish in 14 business days, 12% '
                 'in 17, 6% in 18 and the rest between 20 and 27. Half finish within 14.1 business days, 80% within '
                 '17.2 and 90% within 18.4. The agreed deadline is 10 business days and no case meets it.',
        's_titulo': 'How long a purchase takes, from request to delivery',
        's_sub': 'Example SUP-01 · 4,000 cases simulated with the interview times · business days',
        's_prazo': ['agreed deadline: 10 days', '{n} of 4,000 cases within it'],
        's_ate': '{p} within {v}',
        's_kpis': [('{p50} d', 'half of purchases', 'finish within this'),
                   ('{ef}%', 'efficiency: {ex} h of', 'work in {lt} days'),
                   ('{esp} d', 'waiting in queues,', 'in the typical case'),
                   ('{pas}', 'hand-offs', 'between teams')],
        's_nota': 'Times are interview estimates, not measurements: Senku says to confirm them before deciding.',
    },
}

# caminhos das fichas no hero: setas reais do fluxograma, na ordem (de, para)
ROTA_FELIZ = [('inicio', 'a1'), ('a1', 'a2'), ('a2', 'd1'), ('d1', 'a3'), ('a3', 'f_cot'), ('f_cot', 'a4'),
              ('a4', 'a5')]
ROTA_VOLTA = [('inicio', 'a1'), ('a1', 'a2'), ('a2', 'd1'), ('d1', 'a1b'), ('a1b', 'a2'), ('a2', 'd1'),
              ('d1', 'a3'), ('a3', 'f_cot'), ('f_cot', 'a4'), ('a4', 'a5')]
CORTE = (204, 66, 900, 440)   # viewBox do trecho do fluxograma no hero


def _num(v, lingua):
    s = f'{v:,}' if isinstance(v, int) else f'{v}'
    if lingua == 'pt':
        s = s.replace(',', '.') if isinstance(v, int) else s.replace('.', ',')
    return s


def _fontes():
    with open(FONTES, encoding='utf-8') as f:
        return f.read()


def _dados():
    with open(DADOS, encoding='utf-8') as f:
        txt = f.read()
    return json.loads(txt[txt.index('{'):txt.rindex('}') + 1])


def _fluxo():
    with open(FLUXO, encoding='utf-8') as f:
        s = f.read()
    corpo = s[s.index('>', s.index('<svg')) + 1:s.rindex('</svg>')]
    corpo = re.sub(r'<title>.*?</title>', '', corpo, flags=re.S)
    setas = {}
    for m in re.finditer(r'<path class="seta" data-de="([^"]+)" data-para="([^"]+)" d="([^"]+)"', corpo):
        setas[(m.group(1), m.group(2))] = m.group(3)
    corpo = corpo.replace('<marker id="seta"', '<marker id="seta-h"').replace('url(#seta)', 'url(#seta-h)')
    return corpo, setas


def _rota(setas, rota):
    partes = []
    for i, k in enumerate(rota):
        d = setas[k]
        partes.append(d if i == 0 else 'L' + d[1:])
    return ' '.join(partes)


def _texto(x, y, txt, tam, cor, fam='i', peso=400, ancora='start', extra=''):
    return (f'<text x="{x}" y="{y}" class="{fam}" font-size="{tam}" font-weight="{peso}" fill="{cor}" '
            f'text-anchor="{ancora}"{extra}>{escape(txt)}</text>')


CSS_BASE = """
.i{font-family:Inter,system-ui,sans-serif}.p{font-family:Poppins,Inter,sans-serif}.m{font-family:'JetBrains Mono',ui-monospace,monospace}
.sub{transform-origin:0 0;animation:sub 1.2s .4s cubic-bezier(.2,.8,.2,1) both}
@keyframes sub{from{transform:scaleX(0)}}
.pisca{animation:pisca 1.6s infinite}@keyframes pisca{50%{opacity:.25}}
.entra{animation:entra .8s cubic-bezier(.2,.8,.2,1) both}.e2{animation-delay:.9s}.e3{animation-delay:1.4s}
@keyframes entra{from{opacity:0;transform:translateY(12px)}}
@media (prefers-reduced-motion:reduce){.tok{display:none}*{animation:none!important}}
"""


def _logo(x, y, s):
    k = s / 32
    return (f'<g transform="translate({x} {y}) scale({k})"><rect x=".5" y=".5" width="31" height="31" rx="8" fill="#0E1729" '
            f'stroke="{LINHA2}"/><path d="M22.5 9.5H11.5a3 3 0 0 0-3 3v.5a3 3 0 0 0 3 3h9a3 3 0 0 1 3 3v.5a3 3 0 0 1-3 3H9.5" '
            f'fill="none" stroke="{LIMA}" stroke-width="2.4" stroke-linecap="round"/><path d="M12.5 19.5 9.5 22.5l3 3" '
            f'fill="none" stroke="{LIMA}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="22.5" cy="9.5" r="2.8" fill="{LIMA}"/></g>')


def hero(lingua, d, fontes, corpo, setas):
    t = TEXTOS[lingua]
    W, H = 1280, 640
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{escape(t["alt"])}">',
         f'<title>{escape(t["alt"])}</title>',
         f'<defs><style>{fontes}{CSS_BASE}</style>',
         f'<pattern id="grade" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" '
         f'stroke="{LINHA}" stroke-width="1" opacity=".55"/></pattern>',
         '<radialGradient id="luz" cx="78%" cy="35%" r="55%"><stop offset="0" stop-color="#A3E635" stop-opacity=".10"/>'
         '<stop offset="1" stop-color="#A3E635" stop-opacity="0"/></radialGradient>',
         '<filter id="brilho" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/>'
         '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
         '<clipPath id="janela"><rect x="0" y="0" width="556" height="272" /></clipPath>',
         '</defs>',
         f'<rect width="{W}" height="{H}" fill="{FUNDO}"/><rect width="{W}" height="{H}" fill="url(#grade)"/>',
         f'<rect width="{W}" height="{H}" fill="url(#luz)"/>']
    # marca
    o.append(_logo(64, 52, 44))
    o.append(_texto(120, 86, 'senku', 34, TINTA, 'p', 800, extra=' letter-spacing="-0.6"'))
    o.append(_texto(64, 152, t['kicker'], 15, LIMA, 'm', 500))
    # título
    y = 214
    for linha in t['h1']:
        if '{prove}' in linha:
            antes = linha.split('{prove}')[0]
            o.append(f'<text x="64" y="{y}" class="p" font-size="54" font-weight="800" fill="{TINTA}" letter-spacing="-1.4">'
                     f'{escape(antes)}<tspan fill="{LIMA}" id="pv">{escape(t["prove"])}</tspan></text>')
            px, pw = t['pv_x']
            o.append(f'<rect class="sub" x="{px}" y="{y + 9}" width="{pw}" height="5" rx="2.5" fill="{LIMA}" '
                     f'style="transform-origin:{px}px 0"/>')
        else:
            o.append(_texto(64, y, linha, 54, TINTA, 'p', 800, extra=' letter-spacing="-1.4"'))
        y += 62
    y = 412
    for linha in t['sub']:
        o.append(_texto(64, y, linha, 19.5, MUDO, 'i', 400))
        y += 30
    # selos
    x = 64
    for chip in t['chips']:
        w = len(chip) * 8.1 + 42   # JetBrains Mono: 0,6 em por letra
        o.append(f'<g><rect x="{x}" y="522" width="{w:.0f}" height="34" rx="17" fill="{PAINEL}" stroke="{LINHA2}"/>'
                 f'<circle cx="{x + 15}" cy="539" r="3.5" fill="{VERDE}"/>'
                 + _texto(x + 26, 544, chip, 13.5, '#E2E8F0', 'm', 500) + '</g>')
        x += w + 10
    o.append(_texto(64, 604, t['rodape'], 13.5, APAGADO, 'm', 500))
    # janela com o fluxograma
    fx, fy, fw = 660, 96, 556
    fh = 272
    o.append(f'<g class="entra"><rect x="{fx}" y="{fy}" width="{fw}" height="{fh + 36}" rx="14" fill="#0E1729" stroke="{LINHA2}"/>')
    o.append(f'<line x1="{fx}" x2="{fx + fw}" y1="{fy + 36}" y2="{fy + 36}" stroke="{LINHA}"/>')
    for i in range(3):
        o.append(f'<circle cx="{fx + 20 + i * 16}" cy="{fy + 18}" r="5" fill="{LINHA2}"/>')
    o.append(_texto(fx + 76, fy + 22, t['janela'], 12.5, APAGADO, 'm', 500))
    o.append(f'<circle class="pisca" cx="{fx + fw - 72}" cy="{fy + 18}" r="4" fill="{LIMA}"/>')
    o.append(_texto(fx + fw - 62, fy + 22, t['fichas'], 12.5, LIMA, 'm', 700))
    cx, cy, cw, ch = CORTE
    o.append(f'<g transform="translate({fx} {fy + 36})" clip-path="url(#janela)">'
             f'<svg x="0" y="0" width="{fw}" height="{fh}" viewBox="{cx} {cy} {cw} {ch}" preserveAspectRatio="xMidYMid slice" '
             f'font-family="Inter, system-ui, sans-serif">'
             f'{corpo}')
    for k, (rota, dur, inicio, cor) in enumerate([
            (ROTA_FELIZ, 9, 0, LIMA), (ROTA_FELIZ, 9, 3, LIMA), (ROTA_VOLTA, 13.5, 5.5, LIMA), (ROTA_FELIZ, 9, 6, LIMA)]):
        o.append(f'<path id="r{k}" d="{_rota(setas, rota)}" fill="none" stroke="none"/>')
        o.append(f'<circle class="tok" r="10" fill="{cor}" filter="url(#brilho)" opacity="0">'
                 f'<animateMotion dur="{dur}s" begin="{inicio}s" repeatCount="indefinite" calcMode="linear"><mpath href="#r{k}"/></animateMotion>'
                 f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.04;.94;1" dur="{dur}s" begin="{inicio}s" repeatCount="indefinite"/>'
                 f'</circle>')
    o.append('</svg></g></g>')
    # cartões
    cy0 = fy + fh + 36 + 18
    o.append(f'<g class="entra e2"><rect x="{fx}" y="{cy0}" width="268" height="118" rx="12" fill="{PAINEL}" stroke="{LINHA2}"/>'
             + _texto(fx + 18, cy0 + 30, 'python senku.py validar', 12, APAGADO, 'm', 600)
             + _texto(fx + 18, cy0 + 62, t['ok'], 18, VERDE, 'm', 700)
             + _texto(fx + 18, cy0 + 92, t['ok_meta'], 12, MUDO, 'm', 500) + '</g>')
    p80 = _num(d['tempos_dias']['p80'], lingua)
    o.append(f'<g class="entra e3"><rect x="{fx + 288}" y="{cy0}" width="268" height="118" rx="12" fill="{PAINEL}" stroke="{LINHA2}"/>'
             + _texto(fx + 306, cy0 + 30, t['sim'], 12, APAGADO, 'm', 600)
             + f'<text x="{fx + 306}" y="{cy0 + 66}" class="p" font-size="32" font-weight="800" fill="{TINTA}">{p80}'
               f'<tspan class="i" font-size="14" font-weight="500" fill="{MUDO}" dx="6">{escape(t["dias"])}</tspan></text>'
             + _texto(fx + 306, cy0 + 88, t['sim_txt'][0], 13, MUDO, 'i', 400)
             + _texto(fx + 306, cy0 + 106, t['sim_txt'][1], 13, AMBAR, 'i', 700) + '</g>')
    o.append('</svg>')
    return '\n'.join(o)


def simulacao(lingua, d, fontes):
    t = TEXTOS[lingua]
    T, Hs = d['tempos_dias'], d['histograma']
    total = sum(n for _, n in Hs)
    dentro = sum(n for dia, n in Hs if dia < 10)
    W, H = 1280, 570
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{escape(t["s_alt"])}">', f'<title>{escape(t["s_alt"])}</title>',
         f'<defs><style>{fontes}{CSS_BASE}'
         '.bar{transform-box:fill-box;transform-origin:50% 100%;animation:cresce 1.1s cubic-bezier(.2,.8,.2,1) both}'
         '@keyframes cresce{from{transform:scaleY(0)}}</style></defs>',
         f'<rect width="{W}" height="{H}" rx="18" fill="{FUNDO}"/>',
         f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{LINHA2}"/>']
    o.append(_texto(48, 62, t['s_titulo'], 26, TINTA, 'p', 700))
    o.append(_texto(48, 92, t['s_sub'], 15, APAGADO, 'm', 500))
    # gráfico
    gx, gy, gw, gh = 92, 140, 720, 270
    d0, d1 = 9, 28

    def x(v):
        return gx + (v - d0) / (d1 - d0) * gw

    def y(p):
        return gy + (1 - p / 100) * gh
    for p in (0, 25, 50, 75, 100):
        o.append(f'<line x1="{gx}" x2="{gx + gw}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="{LINHA}"/>')
        o.append(_texto(gx - 10, y(p) + 5, f'{p}%', 13, APAGADO, 'm', 500, 'end'))
    o.append(f'<rect x="{x(d0):.1f}" y="{gy - 10}" width="{x(10.5) - x(d0):.1f}" height="{gh + 10}" fill="{AMBAR}" fill-opacity=".08"/>')
    o.append(f'<line x1="{x(10.5):.1f}" x2="{x(10.5):.1f}" y1="{gy - 10}" y2="{y(0):.1f}" stroke="{AMBAR}" stroke-width="2"/>')
    o.append(_texto(x(10.5) + 10, gy + 8, t['s_prazo'][0], 14, AMBAR, 'm', 700))
    o.append(_texto(x(10.5) + 10, gy + 28, t['s_prazo'][1].format(n=dentro), 14, AMBAR, 'm', 500))
    for dia in range(10, d1 + 1, 2):
        o.append(_texto(x(dia + .5), y(0) + 24, str(dia), 13, APAGADO, 'm', 500, 'middle'))
    bw = (x(1) - x(0)) * .78
    for k, (dia, n) in enumerate(Hs):
        p = n / total * 100
        h = max(2.0, y(0) - y(p))
        o.append(f'<rect class="bar" style="animation-delay:{.3 + k * .08:.2f}s" x="{x(dia + .5) - bw / 2:.1f}" y="{y(0) - h:.1f}" '
                 f'width="{bw:.1f}" height="{h:.1f}" rx="4" fill="{LIMA}"/>')
        if p >= 2:
            o.append(_texto(x(dia + .5), y(0) - h - 9, f'{p:.0f}%', 14, TINTA, 'm', 700, 'middle'))
    o.append(f'<line x1="{gx}" x2="{gx + gw}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{LINHA2}"/>')
    for v, rotulo, fila in ((T['p50'], '50%', 0), (T['p80'], '80%', 1), (T['p90'], '90%', 0)):
        xv = x(v)
        yy = y(0) + 56 + fila * 24
        o.append(f'<line x1="{xv:.1f}" x2="{xv:.1f}" y1="{y(0) + 32:.1f}" y2="{yy - 14:.1f}" stroke="#E2E8F0" stroke-dasharray="2 3"/>')
        o.append(_texto(xv, yy, t['s_ate'].format(p=rotulo, v=_num(v, lingua)), 14, '#E2E8F0', 'm', 700, 'middle'))
    # números
    kx, ky = 868, 140
    vals = {'p50': _num(T['p50'], lingua), 'ef': T['eficiencia_pct'], 'ex': _num(T['execucao_h'], lingua),
            'esp': _num(T['espera'], lingua), 'pas': d['passagens_caso'], 'lt': _num(T['lead_time'], lingua)}
    for i, (grande, l1, l2) in enumerate(t['s_kpis']):
        cx = kx + (i % 2) * 196
        cy = ky + (i // 2) * 136
        cor = AMBAR if i in (1, 2) else TINTA
        o.append(f'<g class="entra" style="animation-delay:{.6 + i * .15:.2f}s"><rect x="{cx}" y="{cy}" width="184" height="122" rx="12" fill="{PAINEL}" stroke="{LINHA2}"/>'
                 + _texto(cx + 16, cy + 50, grande.format(**vals), 32, cor, 'p', 800)
                 + _texto(cx + 16, cy + 80, l1.format(**vals), 13.5, MUDO, 'i', 400)
                 + _texto(cx + 16, cy + 100, l2.format(**vals), 13.5, MUDO, 'i', 400) + '</g>')
    o.append(_texto(48, H - 30, t['s_nota'], 13.5, APAGADO, 'm', 500))
    o.append('</svg>')
    return '\n'.join(o)


def main():
    os.makedirs(SAIDA, exist_ok=True)
    fontes, d = _fontes(), _dados()
    corpo, setas = _fluxo()
    for lingua, suf in (('pt', ''), ('en', '-en')):
        for nome, svg in (('hero', hero(lingua, d, fontes, corpo, setas)), ('simulacao', simulacao(lingua, d, fontes))):
            caminho = os.path.join(SAIDA, f'{nome}{suf}.svg')
            with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
                f.write(svg)
            print(f'✓ {os.path.relpath(caminho, RAIZ)} ({len(svg.encode("utf-8")) // 1024} KB)')


if __name__ == '__main__':
    main()
