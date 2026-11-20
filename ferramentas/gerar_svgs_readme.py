"""
Gera as imagens animadas do README (pt-BR e inglês) na identidade do laboratório: quadro-negro, giz e verde-limão.

    python ferramentas/gerar_site.py          # primeiro: o fluxograma escuro e os dados da página
    python ferramentas/gerar_svgs_readme.py   # depois: assets/readme/*.svg

Cada SVG é autossuficiente, sem script: fontes embutidas (Inter e JetBrains Mono de `animacoes_fontes.css`;
Bricolage Grotesque e Caveat de `lab_fontes.css`; todas da licença OFL). As fichas andam pelas setas reais do
exemplo de compras com `animateMotion`; com movimento reduzido, somem e fica o quadro parado. Os números vêm de
`docs/dados.js`.
"""
import json
import os
import re
from html import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = [os.path.join(AQUI, 'animacoes_fontes.css'), os.path.join(AQUI, 'lab_fontes.css')]
FLUXO = os.path.join(RAIZ, 'docs', 'img', 'fluxo-compras.svg')
DADOS = os.path.join(RAIZ, 'docs', 'dados.js')
SAIDA = os.path.join(RAIZ, 'assets', 'readme')

QUADRO, QUADRO2, GIZ, GIZ2, PO, LIMA, AMBAR, VERMELHO, CEU = (
    '#0E1512', '#121C17', '#EDEDE4', '#C9CCBF', '#8E978C', '#B6F23A', '#FFB547', '#FF6B5E', '#7FD3FF')
LINHA = 'rgba(237,237,228,.14)'

TEXTOS = {
    'pt': {
        'alt': 'Senku: não desenha no chute. Prova. Num quadro-negro, fichas luminosas percorrem o fluxograma em raias '
               'do exemplo de compras; anotação em giz: aqui ninguém chuta o Não. Fórmula: relato mais perguntas mais '
               'fichas mais 4.000 casos igual a processo provado.',
        'exp': 'EXPERIMENTO Nº 001 · MAPEAMENTO DE PROCESSOS',
        'h1': ['Não desenha', 'no chute.', 'Prova.'],
        # largura do "Prova." em Bricolage 800 de 96 px, medida no navegador (getComputedTextLength)
        'h1_larg': 290,
        'nota': ['aqui ninguém', 'chuta o “Não”'],
        'formula': ['relato + perguntas', '+ fichas + {4000}', '= processo {provado}'],
        'mil': '4.000 casos', 'prov': 'provado',
        'rodape': '73 verificações · 4.000 casos simulados · 9 formatos · 0 dependências',
        's_alt': 'Histograma de 4.000 casos simulados do exemplo de compras. 78% terminam em 14 dias úteis, 12% em '
                 '17, 6% em 18 e o resto entre 20 e 27. Metade termina em até 14,1 dias úteis, 80% em até 17,2 e '
                 '90% em até 18,4. O prazo combinado é de 10 dias úteis e nenhum caso fica dentro dele.',
        's_titulo': ['4.000 casos.', 'Zero no prazo.'],
        's_sub': 'SUP-01 · simulação com os tempos da entrevista · dias úteis',
        's_prazo': ['← prazo: 10 dias', '{n} de 4.000 chegam aqui'],
        's_ate': '{p} até {v}',
        's_kpis': [('{p50} d', 'metade das compras', 'termina em até isso'),
                   ('{ef}%', 'eficiência: {ex} h de', 'trabalho em {lt} dias'),
                   ('{esp} d', 'parados esperando,', 'no caso típico'),
                   ('{pas}', 'passagens de bastão', 'entre áreas')],
        's_nota': 'tempos estimados na entrevista, não medidos: confirme antes de decidir',
    },
    'en': {
        'alt': 'Senku: don’t guess the flow. Prove it. On a chalkboard, glowing tokens run through the swimlane '
               'flowchart of the purchasing example; chalk note: nobody guesses the No here. Formula: description '
               'plus questions plus tokens plus 4,000 cases equals a proven process.',
        'exp': 'EXPERIMENT Nº 001 · PROCESS MAPPING',
        'h1': ['Don’t guess', 'the flow.', 'Prove it.'],
        'h1_larg': 368,
        'nota': ['nobody guesses', 'the “No” here'],
        'formula': ['description + questions', '+ tokens + {4000}', '= {provado} process'],
        'mil': '4,000 cases', 'prov': 'proven',
        'rodape': '73 checks · 4,000 simulated cases · 9 formats · 0 dependencies',
        's_alt': 'Histogram of 4,000 simulated cases of the purchasing example. 78% finish in 14 business days, 12% '
                 'in 17, 6% in 18 and the rest between 20 and 27. Half finish within 14.1 business days, 80% within '
                 '17.2 and 90% within 18.4. The agreed deadline is 10 business days and no case meets it.',
        's_titulo': ['4,000 cases.', 'Zero on time.'],
        's_sub': 'SUP-01 · simulated with the interview times · business days',
        's_prazo': ['← deadline: 10 days', '{n} of 4,000 make it'],
        's_ate': '{p} within {v}',
        's_kpis': [('{p50} d', 'half of purchases', 'finish within this'),
                   ('{ef}%', 'efficiency: {ex} h of', 'work in {lt} days'),
                   ('{esp} d', 'waiting in queues,', 'in the typical case'),
                   ('{pas}', 'hand-offs', 'between teams')],
        's_nota': 'times are interview estimates, not measurements: confirm before deciding',
    },
}

ROTA_FELIZ = [('inicio', 'a1'), ('a1', 'a2'), ('a2', 'd1'), ('d1', 'a3'), ('a3', 'f_cot'), ('f_cot', 'a4'),
              ('a4', 'a5'), ('a5', 'a6'), ('a6', 'a7')]
ROTA_VOLTA = [('inicio', 'a1'), ('a1', 'a2'), ('a2', 'd1'), ('d1', 'a1b'), ('a1b', 'a2'), ('a2', 'd1'),
              ('d1', 'a3'), ('a3', 'f_cot'), ('f_cot', 'a4'), ('a4', 'a5'), ('a5', 'a6'), ('a6', 'a7')]
CORTE = (300, 60, 1220, 520)   # viewBox do trecho do fluxograma no hero


def _num(v, lingua):
    s = f'{v:,}' if isinstance(v, int) else f'{v}'
    if lingua == 'pt':
        s = s.replace(',', '.') if isinstance(v, int) else s.replace('.', ',')
    return s


def _fontes():
    css = []
    for f in FONTES:
        with open(f, encoding='utf-8') as fh:
            css.append(fh.read())
    return '\n'.join(css)


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
    corpo = corpo.replace('<rect width="100%" height="100%" fill="#0B1220"/>', '', 1)
    return corpo, setas


def _rota(setas, rota):
    return ' '.join(setas[k] if i == 0 else 'L' + setas[k][1:] for i, k in enumerate(rota))


def _t(x, y, txt, tam, cor, fam='i', peso=400, ancora='start', extra=''):
    return (f'<text x="{x}" y="{y}" class="{fam}" font-size="{tam}" font-weight="{peso}" fill="{cor}" '
            f'text-anchor="{ancora}"{extra}>{escape(txt)}</text>')


CSS_BASE = """
.i{font-family:Inter,system-ui,sans-serif}.b{font-family:'Bricolage Grotesque',Inter,sans-serif}
.m{font-family:'JetBrains Mono',ui-monospace,monospace}.h{font-family:Caveat,cursive}
.giz>rect{fill:rgba(237,237,228,.02)!important;stroke:rgba(237,237,228,.13)!important}
.giz .seta{stroke:#C9CCBF!important}.giz marker path{fill:#C9CCBF}
.giz .no rect,.giz .no circle,.giz .no path{fill:#0E1512!important}.giz text{fill:#EDEDE4}
.risca{stroke-dasharray:700;stroke-dashoffset:700;animation:risca 1.1s .6s cubic-bezier(.6,0,.2,1) forwards}
@keyframes risca{to{stroke-dashoffset:0}}
.sobe{animation:sobe .9s cubic-bezier(.2,.9,.1,1) both}.s2{animation-delay:.1s}.s3{animation-delay:.2s}
@keyframes sobe{from{opacity:0;transform:translateY(30px)}}
.pisca{animation:pisca 1.4s infinite}@keyframes pisca{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.tok{display:none}*{animation:none!important}.risca{stroke-dashoffset:0}}
"""


def _logo(x, y, s):
    k = s / 32
    return (f'<g transform="translate({x} {y}) scale({k})"><rect x=".75" y=".75" width="30.5" height="30.5" rx="8" '
            f'fill="{QUADRO2}" stroke="rgba(237,237,228,.25)" stroke-width="1.5"/><path d="M22.5 9.5H11.5a3 3 0 0 0-3 3v.5a3 3 0 0 0 3 3h9a3 3 0 0 1 3 3v.5a3 3 0 0 1-3 3H9.5" '
            f'fill="none" stroke="{LIMA}" stroke-width="2.4" stroke-linecap="round"/><path d="M12.5 19.5 9.5 22.5l3 3" '
            f'fill="none" stroke="{LIMA}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="22.5" cy="9.5" r="2.8" fill="{LIMA}"/></g>')


def _fundo(W, H):
    return (f'<rect width="{W}" height="{H}" fill="{QUADRO}"/>'
            f'<rect width="{W}" height="{H}" fill="url(#grade)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#luz)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#luz2)"/>')


def _defs(fontes, extra=''):
    return ('<defs><style>' + fontes + CSS_BASE + extra + '</style>'
            f'<pattern id="grade" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" '
            f'stroke="{LINHA}" stroke-width="1" opacity=".45"/></pattern>'
            '<radialGradient id="luz" cx="12%" cy="0%" r="70%"><stop offset="0" stop-color="#B6F23A" stop-opacity=".09"/>'
            '<stop offset="1" stop-color="#B6F23A" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="luz2" cx="95%" cy="40%" r="50%"><stop offset="0" stop-color="#7FD3FF" stop-opacity=".06"/>'
            '<stop offset="1" stop-color="#7FD3FF" stop-opacity="0"/></radialGradient>'
            '<filter id="brilho" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="4" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            '<radialGradient id="vinheta" cx="50%" cy="50%" r="50%"><stop offset=".55" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
            '<mask id="some" maskUnits="userSpaceOnUse" x="600" y="70" width="700" height="298">'
            '<rect x="600" y="70" width="700" height="298" fill="url(#vinheta)"/></mask>'
            '</defs>')


def hero(lingua, d, fontes, corpo, setas):
    t = TEXTOS[lingua]
    W, H = 1280, 640
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{escape(t["alt"])}">', f'<title>{escape(t["alt"])}</title>', _defs(fontes), _fundo(W, H)]
    # fluxograma em giz, à direita, sumindo nas bordas
    cx, cy, cw, ch = CORTE
    o.append(f'<g mask="url(#some)" opacity=".95"><svg x="600" y="70" width="700" height="{700 * ch / cw:.0f}" '
             f'viewBox="{cx} {cy} {cw} {ch}" class="giz" font-family="Inter, system-ui, sans-serif">{corpo}')
    for k, (rota, dur, ini) in enumerate([(ROTA_FELIZ, 11, 0), (ROTA_FELIZ, 11, 3.5), (ROTA_VOLTA, 15, 5.5),
                                          (ROTA_FELIZ, 11, 7.5)]):
        o.append(f'<path id="r{k}" d="{_rota(setas, rota)}" fill="none" stroke="none"/>')
        o.append(f'<circle class="tok" r="11" fill="{LIMA}" filter="url(#brilho)" opacity="0">'
                 f'<animateMotion dur="{dur}s" begin="{ini}s" repeatCount="indefinite" calcMode="linear"><mpath href="#r{k}"/></animateMotion>'
                 f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.03;.95;1" dur="{dur}s" begin="{ini}s" repeatCount="indefinite"/></circle>')
    o.append('</svg></g>')
    # marca e experimento
    o.append(_logo(64, 48, 40))
    o.append(_t(116, 80, 'senku', 32, GIZ, 'b', 800, extra=' letter-spacing="-1.2"'))
    o.append(f'<circle class="pisca" cx="70" cy="128" r="4.5" fill="{LIMA}"/>')
    o.append(_t(84, 133, t['exp'], 13, PO, 'm', 500, extra=' letter-spacing="1.2"'))
    # título
    y = 252
    for k, linha in enumerate(t['h1']):
        cor = LIMA if k == 2 else GIZ
        o.append(f'<g class="sobe s{k + 1}">' + _t(60, y, linha, 96, cor, 'b', 800, extra=' letter-spacing="-5"') + '</g>')
        y += 92
    larg = t['h1_larg']
    o.append(f'<path class="risca" d="M58 {y - 72} C {58 + larg * .2} {y - 84}, {58 + larg * .4} {y - 62}, {58 + larg * .6} {y - 74} '
             f'S {58 + larg * .9} {y - 80}, {58 + larg + 8} {y - 70}" stroke="{LIMA}" stroke-width="7" fill="none" stroke-linecap="round"/>')
    # anotação em giz
    o.append('<g transform="rotate(-8 830 360)">' + _t(780, 350, t['nota'][0], 30, AMBAR, 'h', 700)
             + _t(780, 380, t['nota'][1], 30, AMBAR, 'h', 700) + '</g>')
    o.append(f'<path class="risca" d="M880 318 C 905 285, 915 250, 908 206 M898 218 L908 204 L918 217" stroke="{AMBAR}" '
             f'stroke-width="2.6" fill="none" stroke-linecap="round" style="animation-delay:1.4s"/>')
    # fórmula
    f1, f2, f3 = t['formula']
    o.append('<g transform="rotate(-2 1216 540)">' + _t(1216, 500, f1, 33, GIZ, 'h', 700, 'end'))
    a, b = f2.split('{4000}')
    o.append(f'<text x="1216" y="536" class="h" font-size="33" font-weight="700" fill="{GIZ}" text-anchor="end">{escape(a)}'
             f'<tspan fill="{LIMA}">{escape(t["mil"])}</tspan>{escape(b)}</text>')
    a, b = f3.split('{provado}')
    o.append(f'<text x="1216" y="572" class="h" font-size="33" font-weight="700" fill="{GIZ}" text-anchor="end">{escape(a)}'
             f'<tspan fill="{LIMA}">{escape(t["prov"])}</tspan>{escape(b)}</text></g>')
    o.append(f'<line x1="64" x2="1216" y1="600" y2="600" stroke="{LINHA}"/>')
    o.append(_t(64, 624, t['rodape'], 13.5, PO, 'm', 500, extra=' letter-spacing=".5"'))
    o.append(_t(1216, 624, 'senku.py validar → ✓', 13.5, LIMA, 'm', 500, 'end'))
    o.append('</svg>')
    return '\n'.join(o)


def simulacao(lingua, d, fontes):
    t = TEXTOS[lingua]
    T, Hs = d['tempos_dias'], d['histograma']
    total = sum(n for _, n in Hs)
    dentro = sum(n for dia, n in Hs if dia < 10)
    W, H = 1280, 600
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{escape(t["s_alt"])}">', f'<title>{escape(t["s_alt"])}</title>',
         _defs(fontes, '.bar{transform-box:fill-box;transform-origin:50% 100%;animation:cresce 1.1s cubic-bezier(.2,.8,.2,1) both}'
                       '@keyframes cresce{from{transform:scaleY(0)}}'),
         _fundo(W, H)]
    o.append(_t(56, 92, t['s_titulo'][0], 58, GIZ, 'b', 800, extra=' letter-spacing="-2.5"'))
    o.append(_t(56, 150, t['s_titulo'][1], 58, LIMA, 'b', 800, extra=' letter-spacing="-2.5"'))
    o.append(_t(58, 184, t['s_sub'], 14, PO, 'm', 500))
    gx, gy, gw, gh = 96, 262, 700, 216
    d0, d1 = 9, 28

    def x(v):
        return gx + (v - d0) / (d1 - d0) * gw

    def y(p):
        return gy + (1 - p / 100) * gh
    for p in (0, 25, 50, 75, 100):
        o.append(f'<line x1="{gx}" x2="{gx + gw}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="{LINHA}"/>')
        o.append(_t(gx - 10, y(p) + 5, f'{p}%', 13, PO, 'm', 500, 'end'))
    o.append(f'<rect x="{x(d0):.1f}" y="{gy - 50}" width="{x(10.5) - x(d0):.1f}" height="{gh + 50}" fill="{AMBAR}" fill-opacity=".08"/>')
    o.append(f'<path d="M{x(10.5):.1f} {gy - 50} q 3 {gh / 2:.0f} 0 {gh + 50}" stroke="{AMBAR}" stroke-width="2.6" fill="none" stroke-linecap="round"/>')
    o.append(_t(x(10.5) + 12, gy - 26, t['s_prazo'][0], 30, AMBAR, 'h', 700))
    o.append(_t(x(10.5) + 14, gy + 2, t['s_prazo'][1].format(n=dentro), 26, AMBAR, 'h', 700))
    for dia in range(10, d1 + 1, 2):
        o.append(_t(x(dia + .5), y(0) + 24, str(dia), 13, PO, 'm', 500, 'middle'))
    bw = (x(1) - x(0)) * .74
    for k, (dia, n) in enumerate(Hs):
        p = n / total * 100
        h = max(2.0, y(0) - y(p))
        o.append(f'<rect class="bar" style="animation-delay:{.3 + k * .08:.2f}s" x="{x(dia + .5) - bw / 2:.1f}" y="{y(0) - h:.1f}" '
                 f'width="{bw:.1f}" height="{h:.1f}" rx="4" fill="{LIMA}"/>')
        if p >= 2:
            o.append(_t(x(dia + .5), y(0) - h - 9, f'{p:.0f}%', 14, GIZ, 'm', 700, 'middle'))
    o.append(f'<line x1="{gx}" x2="{gx + gw}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="rgba(237,237,228,.3)"/>')
    for v, rotulo, fila in ((T['p50'], '50%', 0), (T['p80'], '80%', 1), (T['p90'], '90%', 0)):
        xv = x(v)
        yy = y(0) + 56 + fila * 24
        o.append(f'<line x1="{xv:.1f}" x2="{xv:.1f}" y1="{y(0) + 32:.1f}" y2="{yy - 14:.1f}" stroke="{GIZ}" stroke-dasharray="2 3"/>')
        o.append(_t(xv, yy, t['s_ate'].format(p=rotulo, v=_num(v, lingua)), 14, GIZ, 'm', 700, 'middle'))
    kx, ky = 868, 236
    vals = {'p50': _num(T['p50'], lingua), 'ef': T['eficiencia_pct'], 'ex': _num(T['execucao_h'], lingua),
            'esp': _num(T['espera'], lingua), 'pas': d['passagens_caso'], 'lt': _num(T['lead_time'], lingua)}
    for i, (grande, l1, l2) in enumerate(t['s_kpis']):
        cx = kx + (i % 2) * 182
        cy = ky + (i // 2) * 130
        cor = AMBAR if i in (1, 2) else GIZ
        o.append(f'<g class="sobe" style="animation-delay:{.5 + i * .12:.2f}s"><rect x="{cx}" y="{cy}" width="170" height="118" rx="14" fill="{QUADRO2}" stroke="{LINHA}"/>'
                 + _t(cx + 16, cy + 50, grande.format(**vals), 36, cor, 'b', 800, extra=' letter-spacing="-1.5"')
                 + _t(cx + 16, cy + 80, l1.format(**vals), 13, GIZ2, 'i', 400)
                 + _t(cx + 16, cy + 99, l2.format(**vals), 13, GIZ2, 'i', 400) + '</g>')
    o.append(_t(56, H - 28, t['s_nota'], 13.5, PO, 'm', 500))
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
