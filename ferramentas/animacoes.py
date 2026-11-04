"""
Gera as duas animações do README (pt-BR e inglês) a partir dos roteiros de `roteiros/`.

    python ferramentas/animacoes.py            # grava os quatro SVGs em assets/

Cada animação é um SVG 1280 x 640 com um `<foreignObject>` de HTML e CSS: um laço só, sem JavaScript,
fontes embutidas (Inter, Poppins e JetBrains Mono, licença OFL, em `animacoes_fontes.css`). Os tempos
daqui são os mesmos dos roteiros, em segundos; o CSS sai em porcentagem do laço.

Para revisar um quadro: no navegador, ponha `--ps: paused; --d: -12s` no `div` raiz (fica parado no
segundo 12). Com movimento reduzido, o SVG fica parado no quadro final.
"""
import os
from html import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'animacoes_fontes.css')

AZUL, AMBAR, VERDE, VERMELHO, LIMA = '#60A5FA', '#F59E0B', '#34D399', '#F87171', '#A3E635'

BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
.ab{position:absolute}
.i{font-family:Inter,system-ui,sans-serif}
.p{font-family:Poppins,Inter,sans-serif;font-weight:800}
.m{font-family:'JetBrains Mono',ui-monospace,monospace}
.a{animation-duration:%(dur)ss;animation-iteration-count:infinite;animation-delay:var(--d,0s);animation-play-state:var(--ps,running);animation-fill-mode:both;animation-timing-function:ease}
.blink{animation:blink 1s steps(1,end) infinite;animation-play-state:var(--ps,running)}
@keyframes blink{0%%{opacity:1}50%%{opacity:0}}
.bolha{animation:bolha 2.4s ease-in infinite;animation-play-state:var(--ps,running)}
@keyframes bolha{0%%{transform:translateY(0);opacity:0}20%%{opacity:.9}100%%{transform:translateY(-34px);opacity:0}}
.gridbg{background-image:linear-gradient(#1E2A44 1px,transparent 1px),linear-gradient(90deg,#1E2A44 1px,transparent 1px);background-size:32px 32px;background-position:-1px -1px}
.card{background:#111A2E;border:1px solid #1E2A44;border-radius:16px;overflow:hidden}
.hd{height:44px;display:flex;align-items:center;gap:10px;padding:0 18px;border-bottom:1px solid #1E2A44;font-size:14px;font-weight:600;color:#94A3B8}
.dot{width:9px;height:9px;border-radius:50%%;display:inline-block}
.cap{left:0;width:1280px;text-align:center;font-size:22px;color:#CBD5E1;font-weight:500}
.cap b{color:#F1F5F9;font-weight:700}
.chip{height:46px;width:420px;display:flex;align-items:center;justify-content:center;border-radius:999px;font-size:15px;font-weight:500;white-space:nowrap;transform-origin:0 0}
.chip b{font-weight:700;margin-right:6px}
.pill{padding:10px 20px;border-radius:999px;background:#0F1A0A;border:1px solid rgba(163,230,53,.55);color:#D9F99D;font-size:16px;font-weight:600;white-space:nowrap}
.err{display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border-radius:8px;background:#3A1420;border:1px solid #F87171;color:#FECACA;font-size:14px;font-weight:500;white-space:nowrap}
.ok{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;background:rgba(52,211,153,.12);border:1px solid #34D399;color:#A7F3D0;font-size:14px;font-weight:600;white-space:nowrap}
.bub{background:#1B2540;border:1px solid #334155;border-radius:16px;padding:16px 22px;color:#F1F5F9;font-size:21px;font-weight:500;line-height:1.5}
.kw{border-radius:6px;padding:1px 4px;margin:0 -4px}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.06em;padding:3px 8px;border-radius:6px}
.fic{font-size:14px;padding:7px 12px;border-radius:8px;background:#0F1E36;border:1px solid #1E3A5F;color:#BFDBFE;white-space:nowrap}
.cnt::after{content:counter(c)}
.stamp{font-family:Poppins,Inter,sans-serif;font-weight:800;font-size:40px;letter-spacing:.06em;padding:6px 22px;border:5px solid;border-radius:12px;white-space:nowrap}
svg text{font-family:Inter,system-ui,sans-serif}
"""


class Linha:
    """Linha do tempo de uma animação: cada chamada vira um @keyframes em porcentagem do laço."""

    def __init__(self, dur):
        self.dur = dur
        self.css = []
        self.n = 0
        self.props = []

    def pct(self, t):
        return ('%.3f' % (t / self.dur * 100)).rstrip('0').rstrip('.')

    def kf(self, quadros):
        """quadros: [(segundo, css)]. Antes do primeiro e depois do último, fica parado."""
        self.n += 1
        nome = 'k%d' % self.n
        quadros = sorted(quadros, key=lambda q: q[0])
        partes = []
        for i, (t, css) in enumerate(quadros):
            sel = self.pct(t) + '%'
            if i == 0 and t > 0:
                sel = '0%,' + sel
            if i == len(quadros) - 1 and t < self.dur:
                sel += ',100%'
            partes.append('%s{%s}' % (sel, css))
        self.css.append('@keyframes %s{%s}\n.%s{animation-name:%s}' % (nome, ''.join(partes), nome, nome))
        return 'a ' + nome

    def vis(self, ent, sai=None, de='translateY(10px)', para=None, f=0.35, fs=0.4, op=1):
        """Entra em `ent` (vindo de `de`), fica, e some até `sai` (indo para `para`)."""
        q = [(ent, 'opacity:0;transform:%s' % de), (ent + f, 'opacity:%s;transform:none' % op)]
        if sai is not None:
            q += [(sai - fs, 'opacity:%s;transform:none' % op), (sai, 'opacity:0;transform:%s' % (para or 'none'))]
        return self.kf(q)

    def contador(self, valor, ent, dur=1.6, de=0):
        self.n += 1
        prop = '--c%d' % self.n
        self.props.append('@property %s{syntax:\'<integer>\';initial-value:0;inherits:false}' % prop)
        cls = self.kf([(ent, '%s:%d;animation-timing-function:cubic-bezier(.15,.7,.3,1)' % (prop, de)),
                       (ent + dur, '%s:%d' % (prop, valor))])
        return cls, 'counter-reset:c var(%s)' % prop


def el(html, x, y, cls='', style='', w=None, h=None):
    tam = ('width:%spx;' % w if w is not None else '') + ('height:%spx;' % h if h is not None else '')
    return '<div class="ab %s" style="left:%spx;top:%spx;%s%s">%s</div>' % (cls, x, y, tam, style, html)


def frasco(cor=LIMA, tam=1.0):
    """O símbolo do Senku: um frasco de laboratório com bolhas. Desenho original, não o personagem."""
    w, h = 84 * tam, 104 * tam
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" viewBox="0 0 84 104">'
            '<path d="M18 74h48l9 17a6 6 0 0 1-5 9H14a6 6 0 0 1-5-9z" fill="%s" opacity=".35"/>'
            '<circle class="bolha" cx="36" cy="80" r="3.5" fill="%s"/>'
            '<circle class="bolha" style="animation-delay:-.8s" cx="48" cy="86" r="2.5" fill="%s"/>'
            '<circle class="bolha" style="animation-delay:-1.6s" cx="42" cy="90" r="3" fill="%s"/>'
            '<path d="M29 4h26M33 4v28L8 90a8 8 0 0 0 7 12h54a8 8 0 0 0 7-12L51 32V4" fill="none" stroke="%s" '
            'stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>'
            '<path d="M44 40l-6 11h8l-6 11" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round" '
            'stroke-linejoin="round"/></svg>') % (w, h, cor, cor, cor, cor, cor, cor)


def cadeado(cor):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="22" height="26" viewBox="0 0 22 26">'
            '<path d="M5 11V8a6 6 0 0 1 12 0v3" fill="none" stroke="%s" stroke-width="2.5"/>'
            '<rect x="2" y="11" width="18" height="13" rx="3" fill="%s"/></svg>') % (cor, cor)


def svg_doc(conteudo, w, h, dur, linha_css, fontes, rotulo, raiz_extra=''):
    css = (fontes + BASE_CSS % {'dur': dur} + '\n'.join(linha_css.props) + '\n' + linha_css.comentario + '\n'
           + '\n'.join(linha_css.css) + '\n' + linha_css.reduzido)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
            'aria-label="%s"><style><![CDATA[\n%s\n]]></style>'
            '<rect width="%d" height="%d" fill="#0B1220"/>'
            '<foreignObject width="%d" height="%d"><div xmlns="http://www.w3.org/1999/xhtml" class="i" '
            'style="position:relative;width:%dpx;height:%dpx;overflow:hidden;background:#0B1220;color:#E2E8F0%s">'
            '%s</div></foreignObject></svg>\n') % (
        w, h, w, h, escape(rotulo), css, w, h, w, h, w, h, raiz_extra, conteudo)


# ------------------------------------------------------------------ desenho de raias (fluxograma)

def linha_animada(L, d, t, cor, larg, dur=0.35):
    """Linha que se desenha de `t` a `t + dur` e ganha a ponta de seta quando chega. Só comandos M, H e V."""
    import re
    x = y = px = py = 0.0
    for cmd, num in re.findall(r'([MHV])\s*([-\d.]+(?:\s+[-\d.]+)?)', d):
        px, py = x, y
        v = [float(n) for n in num.split()]
        if cmd == 'M':
            x, y = v
        elif cmd == 'H':
            x = v[0]
        else:
            y = v[0]
    ang = 0 if x > px else 180 if x < px else 90 if y > py else -90
    linha = L.kf([(t, 'stroke-dashoffset:1;opacity:0'), (t + 0.02, 'stroke-dashoffset:1;opacity:1'),
                  (t + dur, 'stroke-dashoffset:0;opacity:1')])
    ponta = L.kf([(t + dur - 0.05, 'opacity:0'), (t + dur, 'opacity:1')])
    return ('<path class="%s" d="%s" pathLength="1" stroke-dasharray="1" fill="none" stroke="%s" stroke-width="%s"/>'
            '<path class="%s" d="M-9 -5L0 0L-9 5z" fill="%s" transform="translate(%s %s) rotate(%s)"/>'
            % (linha, d, cor, larg, ponta, cor, x, y, ang))


def raias_svg(L, T, t0, largura=1040, altura=330, so_desenho=False, verde_no_fim=None):
    """Fluxograma em raias do exemplo de compras, desenhado peça por peça a partir de `t0`."""
    raias = [T('Solicitante', 'Requester'), T('Comprador', 'Buyer'), T('Gerente', 'Manager')]
    c = []
    a = c.append
    a('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 1040 330">' % (largura, altura))
    a('<defs><marker id="pt" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
      'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#94A3B8"/></marker></defs>')
    cls_raias = L.vis(t0, None, de='none')
    a('<g class="%s">' % cls_raias)
    for i, nome in enumerate(raias):
        y = i * 110
        a('<rect x="0.5" y="%s" width="1039" height="110" fill="%s" stroke="#1E2A44"/>'
          % (y + 0.5, '#0E1729' if i % 2 else '#101B30'))
        a('<rect x="0.5" y="%s" width="120" height="110" fill="#14213A" stroke="#1E2A44"/>' % (y + 0.5))
        a('<text x="60" y="%s" text-anchor="middle" font-size="15" font-weight="600" fill="#CBD5E1">%s</text>'
          % (y + 60, escape(nome)))
    a('</g>')

    def caixa(x, y, w, texto, t, cor='#1B2A47', borda=AZUL):
        cls = L.vis(t, None, de='scale(.8)', f=0.3)
        linhas = texto.split('|')
        ys = [y + 27] if len(linhas) == 1 else [y + 19, y + 36]
        tx = ''.join('<text x="%s" y="%s" text-anchor="middle" font-size="14" font-weight="500" fill="#E2E8F0">%s'
                     '</text>' % (x + w / 2, yy, escape(li)) for li, yy in zip(linhas, ys))
        a('<g class="%s" style="transform-origin:%spx %spx"><rect x="%s" y="%s" width="%s" height="44" rx="9" '
          'fill="%s" stroke="%s" stroke-width="1.6"/>%s</g>' % (cls, x + w / 2, y + 22, x, y, w, cor, borda, tx))

    def seta(d, t, rot=None, rx=0, ry=0):
        a(linha_animada(L, d, t, '#94A3B8', 2))
        if rot:
            cr = L.vis(t + 0.25, None, de='none', f=0.25)
            a('<text class="%s" x="%s" y="%s" font-size="13" font-weight="600" fill="#CBD5E1">%s</text>'
              % (cr, rx, ry, escape(rot)))

    def circulo(x, y, t, fim=False):
        cls = L.vis(t, None, de='scale(.5)', f=0.3)
        a('<circle class="%s" style="transform-origin:%spx %spx" cx="%s" cy="%s" r="14" fill="%s" stroke="%s" '
          'stroke-width="%s"/>' % (cls, x, y, x, y, '#0B1220', VERDE if not fim else VERMELHO, 4 if fim else 2))

    circulo(170, 55, t0 + 0.4)
    seta('M184 55H232', t0 + 0.6)
    caixa(236, 33, 150, T('Pedir material', 'Request material'), t0 + 0.8)
    seta('M386 55H505V139', t0 + 1.1)
    caixa(420, 143, 170, T('Cotar com|3 fornecedores', 'Get quotes from|3 suppliers'), t0 + 1.4)
    seta('M590 165H620', t0 + 1.7)
    cls = L.vis(t0 + 1.9, None, de='scale(.6)', f=0.3)
    a('<g class="%s" style="transform-origin:650px 165px"><polygon points="650,137 678,165 650,193 622,165" '
      'fill="#2A2410" stroke="%s" stroke-width="1.8"/><text x="650" y="128" text-anchor="middle" font-size="13" '
      'font-weight="600" fill="#FCD9A8">%s</text></g>' % (cls, AMBAR, escape(T('Acima de R$ 5 mil?', 'Above $5k?'))))
    seta('M678 165H852', t0 + 2.2, T('Não', 'No'), 700, 156)
    seta('M650 193V275H696', t0 + 2.2, T('Sim', 'Yes'), 658, 236)
    caixa(856, 143, 130, T('Emitir pedido', 'Issue PO'), t0 + 2.5)
    caixa(700, 253, 140, T('Aprovar compra', 'Approve purchase'), t0 + 2.5)
    seta('M840 275H921V191', t0 + 2.8)
    seta('M986 165H1004', t0 + 2.9)
    circulo(1018, 165, t0 + 3.1, fim=True)
    a('</svg>')
    return ''.join(c)


# ------------------------------------------------------------------ banner (48 s, 6 cenas)

def banner(lang, fontes):
    T = (lambda pt, en: pt) if lang == 'pt' else (lambda pt, en: en)
    L = Linha(48)
    L.comentario = ('/* Linha do tempo: 48 s. Cena 1 0–7 · Cena 2 7–13 · Cena 3 13–23 · Cena 4 23–35 · '
                    'Cena 5 35–43 · Cena 6 43–48 */')
    L.reduzido = ('@media (prefers-reduced-motion: reduce){.raiz{--d:-46s!important;--ps:paused!important}'
                  '.bolha{animation:none}}')
    h = []
    a = h.append

    # fundo: grade (7–47,5 s) e brilho verde
    a(el('', 0, 0, 'gridbg ' + L.kf([(7.0, 'opacity:0'), (7.8, 'opacity:.5'), (47.5, 'opacity:.5'),
                                      (48, 'opacity:0')]), w=1280, h=640))
    a(el('', 340, 120, '', 'border-radius:50%;background:radial-gradient(closest-side,rgba(163,230,53,.10),'
         'transparent);', w=600, h=400))

    # ---------------- Cena 1 · Os dois erros (0–7 s)
    sai_e = L.kf([(0, 'opacity:1;transform:none'), (6.6, 'opacity:1;transform:none'),
                  (7.0, 'opacity:0;transform:translateX(160px) scale(.9)')])
    sai_d = L.kf([(0, 'opacity:1;transform:none'), (6.6, 'opacity:1;transform:none'),
                  (7.0, 'opacity:0;transform:translateX(-160px) scale(.9)')])
    a(el('', 0, 0, sai_e, 'background:rgba(96,165,250,.04);border-right:1px solid #1E2A44', w=640, h=640))
    a(el('', 640, 0, sai_d, 'background:rgba(245,158,11,.05)', w=640, h=640))
    # esquerda: fluxograma rabiscado, decisão sem o "Não"
    s = []
    s.append('<svg xmlns="http://www.w3.org/2000/svg" width="548" height="250" viewBox="0 0 548 250">'
             '<defs><marker id="p1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
             'orient="auto"><path d="M0 0L10 5L0 10z" fill="#64748B"/></marker></defs>')
    pecas = [
        (0.3, '<circle cx="34" cy="120" r="12" fill="none" stroke="#94A3B8" stroke-width="2"/>'),
        (0.5, '<path d="M46 120H76" stroke="#64748B" stroke-width="2" marker-end="url(#p1)" stroke-dasharray="6 4"/>'),
        (0.7, '<rect x="80" y="100" width="112" height="40" rx="6" fill="none" stroke="#94A3B8" stroke-width="2" '
              'stroke-dasharray="7 3"/><text x="136" y="125" text-anchor="middle" font-size="14" fill="#CBD5E1">%s'
              '</text>' % escape(T('Pedir', 'Request'))),
        (0.9, '<path d="M192 120H220" stroke="#64748B" stroke-width="2" marker-end="url(#p1)" stroke-dasharray="6 4"/>'),
        (1.1, '<rect x="224" y="100" width="112" height="40" rx="6" fill="none" stroke="#94A3B8" stroke-width="2" '
              'stroke-dasharray="7 3"/><text x="280" y="125" text-anchor="middle" font-size="14" fill="#CBD5E1">%s'
              '</text>' % escape(T('Aprovar?', 'Approve?'))),
        (1.3, '<path d="M336 120H360" stroke="#64748B" stroke-width="2" marker-end="url(#p1)" stroke-dasharray="6 4"/>'),
        (1.5, '<path d="M440 120H470" stroke="#64748B" stroke-width="2" marker-end="url(#p1)" stroke-dasharray="6 4"/>'
              '<text x="444" y="110" font-size="12" fill="#94A3B8">%s</text>'
              '<rect x="472" y="100" width="66" height="40" rx="6" fill="none" stroke="#94A3B8" stroke-width="2" '
              'stroke-dasharray="7 3"/><text x="505" y="125" text-anchor="middle" font-size="14" fill="#CBD5E1">%s'
              '</text>' % (escape(T('Sim', 'Yes')), escape(T('Comprar', 'Buy')))),
    ]
    for t, frag in pecas:
        s.append('<g class="%s">%s</g>' % (L.vis(t, None, de='none', f=0.25), frag))
    ruim = L.kf([(0, 'opacity:0'), (1.3, 'opacity:0'), (1.5, 'opacity:1;stroke:#94A3B8'),
                 (1.8, 'stroke:%s;transform:translateX(0)' % VERMELHO), (1.9, 'stroke:%s;transform:translateX(-4px)' % VERMELHO),
                 (2.0, 'stroke:%s;transform:translateX(4px)' % VERMELHO), (2.1, 'stroke:%s;transform:translateX(-3px)' % VERMELHO),
                 (2.3, 'opacity:1;stroke:%s;transform:none' % VERMELHO)])
    s.append('<g class="%s"><polygon points="400,92 432,120 400,148 368,120" fill="none" stroke-width="2.4"/>'
             '<text x="400" y="80" text-anchor="middle" font-size="13" fill="#CBD5E1">%s</text></g>'
             % (ruim, escape(T('Valor alto?', 'High value?'))))
    s.append('</svg>')
    a(el('<div class="hd"><span class="dot" style="background:%s"></span>%s</div>%s' % (
        AZUL, escape(T('Fluxograma · desenho à mão', 'Flowchart · hand-drawn')), ''.join(s)),
        46, 110, 'card ' + sai_e, w=548, h=310))
    a(el('<span class="err">⚠ %s</span>' % escape(T('decisão sem o caminho do “Não”', 'decision with no “No” path')),
         150, 360, L.kf([(0, 'opacity:0;transform:translateY(8px)'), (1.9, 'opacity:0;transform:translateY(8px)'),
                         (2.25, 'opacity:1;transform:none'), (6.6, 'opacity:1;transform:none'),
                         (7.0, 'opacity:0;transform:translateX(160px) scale(.9)')])))
    # direita: documento sem dono, sem tempo, sem aceite
    campos = [(T('Responsável', 'Owner'), T('a definir', 'TBD')), (T('Tempo de ciclo', 'Cycle time'), '???'),
              (T('Última revisão', 'Last review'), '2019'), (T('Aprovado por', 'Approved by'), '—')]
    doc = ['<div class="hd"><span class="dot" style="background:%s"></span>%s</div>'
           % (AMBAR, escape(T('Mapeamento.docx', 'Process_map.docx')))]
    doc.append('<div style="padding:22px 28px">'
               '<div style="height:12px;width:62%;background:#334155;border-radius:4px;margin-bottom:10px"></div>'
               '<div style="height:8px;width:88%;background:#1E293B;border-radius:4px;margin-bottom:6px"></div>'
               '<div style="height:8px;width:80%;background:#1E293B;border-radius:4px;margin-bottom:18px"></div>')
    for i, (k, v) in enumerate(campos):
        doc.append('<div class="%s" style="display:flex;justify-content:space-between;padding:7px 0;'
                   'border-bottom:1px dashed #1E2A44;font-size:16px"><span style="color:#94A3B8">%s</span>'
                   '<span style="color:#FCA5A5;font-weight:600">%s</span></div>'
                   % (L.vis(2.4 + i * 0.3, None, de='translateX(-10px)', f=0.3), escape(k), escape(v)))
    doc.append('</div>')
    a(el(''.join(doc), 686, 110, 'card ' + sai_d, w=548, h=310))
    a(el('<div class="stamp" style="color:%s;border-color:%s;background:rgba(58,20,32,.85);font-size:34px">%s</div>' % (
        VERMELHO, VERMELHO, escape(T('NINGUÉM APROVOU', 'NOBODY SIGNED OFF'))), T(770, 738), 232,
        L.kf([(0, 'opacity:0;transform:rotate(-10deg) scale(1.6)'), (3.9, 'opacity:0;transform:rotate(-10deg) scale(1.6)'),
              (4.2, 'opacity:1;transform:rotate(-10deg) scale(1)'), (6.6, 'opacity:1;transform:rotate(-10deg) scale(1)'),
              (7.0, 'opacity:0;transform:translateX(-160px) rotate(-10deg) scale(.9)')])))
    a(el(T('Desenhar sem <b>perguntar</b>. Documentar sem <b>medir</b>.',
           'Draw without <b>asking</b>. Document without <b>measuring</b>.'), 0, 480, 'cap ' + L.vis(5.5, 6.9)))

    # ---------------- Cena 2 · A conversa (7–13 s)
    a(el(frasco(), 1150, 506, L.kf([(7.4, 'opacity:0;transform:translateX(160px)'),
                                    (8.2, 'opacity:1;transform:none;animation-timing-function:ease'),
                                    (47.5, 'opacity:1'), (48, 'opacity:0')])))
    pal = [T('e-mail', 'email'), T('comprador', 'buyer'), T('três fornecedores', 'three quotes'),
           T('acima de R$ 5 mil', 'above $5k'), T('gerente aprova', 'manager approves')]
    kws = []
    for i, p in enumerate(pal):
        t = 7.9 + i * 0.3
        kws.append('<span class="kw %s">%s</span>' % (
            L.kf([(t, 'background:transparent'), (t + 0.25, 'background:rgba(163,230,53,.22)')]), escape(p)))
    if lang == 'pt':
        frase = ('O pedido chega por %s, o %s cota com %s e, %s, o %s.' % tuple(kws))
    else:
        frase = ('Requests arrive by %s, the %s gets %s and, %s, the %s.' % tuple(kws))
    bolha_cls = L.kf([(7.3, 'opacity:0;transform:scale(.92)'), (7.65, 'opacity:1;transform:none'),
                      (9.9, 'opacity:1;transform:none'), (10.2, 'opacity:0;transform:scale(.96)')])
    a(el('<div style="font-size:14px;font-weight:600;color:#94A3B8;margin:0 0 8px 6px">%s</div>'
         '<div class="bub">%s</div>' % (escape(T('você', 'you')), frase), 150, 210, bolha_cls, w=980))
    a(el(T('Uma conversa, duas entregas. O Senku faz <b>as duas</b>.',
           'One conversation, two deliverables. Senku makes <b>both</b>.'), 0, 480, 'cap ' + L.vis(10.5, 12.9)))

    # chips que atravessam o banner
    def chip(texto, cor, fundo, pos):
        (xc, xs, xk, xa), ativo = pos
        q = [(10.0, 'opacity:0;transform:translate(%dpx,300px) scale(.9)' % xc),
             (10.4, 'opacity:1;transform:translate(%dpx,300px)' % xc),
             (11.0, 'opacity:1;transform:translate(%dpx,300px)' % xs),
             (13.0, 'opacity:1;transform:translate(%dpx,300px)' % xs),
             (13.4, 'opacity:%s;transform:translate(%dpx,30px) scale(.8)' % (1 if ativo[0] == 13.4 else .35, xk))]
        ent, sai = ativo
        if ent > 13.4:
            q += [(ent - 0.3, 'opacity:.35;transform:translate(%dpx,30px) scale(.8)' % xk),
                  (ent, 'opacity:1;transform:translate(%dpx,30px) scale(.8)' % xk)]
        q += [(sai - 0.4, 'opacity:1;transform:translate(%dpx,30px) scale(.8)' % xk),
              (sai, 'opacity:.35;transform:translate(%dpx,30px) scale(.8)' % xk),
              (43.0, 'opacity:.35;transform:translate(%dpx,30px) scale(.8);'
                     'animation-timing-function:cubic-bezier(.3,1.4,.5,1)' % xk),
              (43.6, 'opacity:1;transform:translate(%dpx,118px)' % xa),
              (47.5, 'opacity:1;transform:translate(%dpx,118px)' % xa), (48, 'opacity:0;transform:translate(%dpx,118px)' % xa)]
        a(el(texto, 0, 0, 'chip ' + L.kf(q), 'border:1px solid %s;background:%s;color:#E2E8F0' % (cor, fundo)))
    chip(T('<b>fluxograma</b> quem faz o quê, em que ordem', '<b>flowchart</b> who does what, in which order'),
         AZUL, '#0F1E36', ((220, 196, 40, 220), (13.4, 22.6)))
    chip(T('<b>mapeamento</b> tempos, regras, RACI, riscos', '<b>process map</b> times, rules, RACI, risks'),
         AMBAR, '#1F1708', ((640, 664, 870, 640), (23.0, 34.6)))

    # ---------------- Cena 3 · O fluxograma (13–23 s)
    cena3 = L.kf([(13.2, 'opacity:0;transform:none'), (13.3, 'opacity:1;transform:none'), (22.6, 'opacity:1;transform:none'),
                  (23.0, 'opacity:0;transform:translateY(-16px)')])
    a(el(raias_svg(L, T, 13.4), 120, 92, cena3))
    a(el('<div style="display:flex;gap:12px;align-items:flex-start"><span class="tag" style="background:#3A2A08;'
         'color:#FCD34D">%s</span><div><div style="font-size:13px;color:#94A3B8;margin-bottom:2px">%s</div>'
         '<div style="font-size:17px;font-weight:600;color:#F1F5F9">%s</div></div></div>'
         % (escape(T('LACUNA', 'GAP')), escape(T('o Senku pergunta antes de desenhar', 'Senku asks before drawing')),
            escape(T('Quem aprova quando o gerente está de férias?', 'Who approves when the manager is on leave?'))),
         120, 440, L.vis(16.9, 19.6, de='translateY(10px)')))
    a(el('<span class="ok">✓ %s</span>' % escape(T('7PMG e BPMN Method & Style', '7PMG and BPMN Method & Style')),
         760, 432, L.vis(17.8, 22.6, de='translateY(8px) scale(.9)')))
    a(el('<span class="ok">✓ %s</span>' % escape(T('todo caminho chega ao fim', 'every path reaches the end')),
         760, 470, L.vis(18.2, 22.6, de='translateY(8px) scale(.9)')))
    fmts = ['BPMN 2.0', 'Bizagi', 'Camunda', 'draw.io', 'Visio', 'Mermaid', 'SVG']
    for i, f in enumerate(fmts):
        a(el('<span class="fic m">%s</span>' % f, 120 + i * 120, 516,
             L.vis(19.0 + i * 0.12, 22.6, de='translateY(8px)', f=0.25)))
    a(el(T('Ele pergunta o que falta e <b>prova</b> que o fluxo termina.',
           'It asks what is missing and <b>proves</b> the flow ends.'), 0, 566, 'cap ' + L.vis(19.6, 22.8)))

    # ---------------- Cena 4 · O mapeamento (23–35 s)
    saida4 = L.kf([(23.0, 'opacity:0;transform:translateY(16px)'), (23.4, 'opacity:1;transform:none'),
                   (34.4, 'opacity:1;transform:none'), (35.0, 'opacity:0;transform:translateY(-16px)')])
    secoes = [T('Ficha e escopo', 'Profile and scope'), 'SIPOC', T('Atividades e regras', 'Activities and rules'),
              T('Matriz RACI', 'RACI matrix'), T('Indicadores e tempos', 'KPIs and times'),
              T('Riscos e controles', 'Risks and controls'), T('Oportunidades Lean', 'Lean opportunities')]
    linhas = ''.join('<div class="%s" style="display:flex;align-items:center;gap:12px;padding:9px 0;'
                     'border-bottom:1px solid #1E2A44;font-size:17px"><span style="color:%s;font-weight:700">✓</span>'
                     '<span>%s</span></div>' % (L.vis(23.6 + i * 0.28, None, de='translateX(-12px)', f=0.3), VERDE,
                                                  escape(sx)) for i, sx in enumerate(secoes))
    a(el('<div class="hd"><span class="dot" style="background:%s"></span><span class="m" style="color:#FCD9A8">'
         'SUP-01</span> · %s</div><div style="padding:8px 24px">%s</div>'
         % (AMBAR, escape(T('Compra de materiais indiretos', 'Compra de materiais indiretos')), linhas),
         110, 92, 'card ' + saida4, w=480, h=440))
    metr = [(T('14,1 d úteis', '14.1 bus. days'), T('lead time típico', 'typical lead time')),
            (T('17,2 d úteis', '17.2 bus. days'), T('80% dos casos até', '80% of cases within')),
            ('4%', T('eficiência do ciclo', 'cycle efficiency')),
            ('7', T('passagens de bastão', 'handoffs'))]
    for i, (v, r) in enumerate(metr):
        x, y = 640 + (i % 2) * 270, 92 + (i // 2) * 112
        a(el('<div style="font-family:Poppins,Inter,sans-serif;font-weight:800;font-size:30px;color:#FCD9A8">%s</div>'
             '<div style="font-size:14px;color:#94A3B8;margin-top:4px">%s</div>' % (escape(v), escape(r)),
             x, y, 'card ' + L.kf([(25.0 + i * 0.3, 'opacity:0;transform:translateY(-24px)'),
                                    (25.4 + i * 0.3, 'opacity:1;transform:none'), (28.6, 'opacity:1;transform:none'),
                                    (29.0, 'opacity:0;transform:none')]), 'padding:18px 22px', w=250, h=96))
    a(el('<span class="tag" style="background:#3A2A08;color:#FCD34D">%s</span>'
         '<div style="font-size:17px;font-weight:500;margin-top:8px;color:#F1F5F9">%s</div>'
         % (escape(T('OPORTUNIDADE 1 · ESPERA', 'OPPORTUNITY 1 · WAITING')),
            escape(T('3 dias úteis antes de “Cotar com fornecedores”: o que segura?',
                     '3 business days before “Cotar com fornecedores”: what is holding it?'))),
         640, 318, 'card ' + L.vis(26.6, 29.0), 'padding:16px 22px', w=520))
    a(el('<div class="bub" style="font-size:19px"><span style="color:#94A3B8;font-size:14px;display:block">%s</span>'
         '%s</div>' % (escape(T('dono do processo', 'process owner')), escape(T('Aprovo.', 'Approved.'))),
         700, 140, L.kf([(29.2, 'opacity:0;transform:scale(.92)'), (29.55, 'opacity:1;transform:none'),
                         (34.4, 'opacity:1;transform:none'), (35.0, 'opacity:0')])))
    a(el('<div class="stamp" style="color:%s;border-color:%s;background:rgba(6,40,30,.88)">%s</div>' % (
        VERDE, VERDE, escape(T('APROVADO', 'APPROVED'))), 200, 236,
        L.kf([(29.6, 'opacity:0;transform:rotate(-10deg) scale(1.6)'), (29.95, 'opacity:1;transform:rotate(-10deg) scale(1)'),
              (34.4, 'opacity:1;transform:rotate(-10deg) scale(1)'), (35.0, 'opacity:0;transform:rotate(-10deg) scale(1)')])))
    trava = L.kf([(30.0, 'opacity:0'), (30.3, 'opacity:1;transform:none'), (32.4, 'transform:translateX(0)'),
                  (32.5, 'transform:translateX(-4px)'), (32.6, 'transform:translateX(4px)'),
                  (32.7, 'transform:translateX(-3px)'), (32.85, 'opacity:1;transform:none'), (34.4, 'opacity:1'),
                  (35.0, 'opacity:0')])
    a(el('<div style="display:flex;align-items:center;gap:10px">%s<span class="m" style="font-size:15px;'
         'color:#A7F3D0">%s</span></div>' % (cadeado(VERDE), escape(T('aceite 9C41E07B · v0.3', 'sign-off 9C41E07B · v0.3'))),
         136, 470, trava))
    a(el('<span class="m" style="font-size:15px;padding:8px 14px;border-radius:8px;border:1px dashed %s;'
         'color:#FECACA;background:rgba(58,20,32,.6)">%s</span>' % (VERMELHO, escape(
             T('“Aprovar compra” · espera 1d → 3d', '“Aprovar compra” · wait 1d → 3d'))),
         640, 300, L.kf([(32.0, 'opacity:0;transform:translateX(120px)'), (32.4, 'opacity:1;transform:none'),
                         (32.6, 'filter:grayscale(0)'), (33.0, 'filter:grayscale(1);opacity:.7'),
                         (33.6, 'opacity:.7;transform:none'), (34.0, 'opacity:0;transform:translateX(120px)')])))
    a(el('<span class="err">%s</span>' % escape(T('situacao: mudou depois do aceite. Precisa de novo “sim”.',
                                                  'situacao: changed after sign-off. Needs a new “yes”.')),
         640, 352, L.vis(32.5, 34.4, de='translateY(8px)')))
    a(el(T('Mapeamento completo, com o <b>aceite</b> do dono do processo.',
           'A full process map, with the process owner’s <b>sign-off</b>.'), 0, 566, 'cap ' + L.vis(31.0, 34.8)))

    # ---------------- Cena 5 · O que sai e os números (35–43 s)
    blur_out = L.kf([(35.8, 'opacity:0;filter:none'), (36.1, 'opacity:1;filter:none'), (38.2, 'opacity:1;filter:none'),
                     (38.6, 'opacity:0;filter:blur(8px)')])
    cmd = 'python senku.py documentar carta.json'
    a(el('<span class="m" style="font-size:20px;color:#D9F99D">$ </span><span class="m %s" style="display:inline-block;'
         'overflow:hidden;white-space:nowrap;vertical-align:bottom;font-size:20px;color:#E2E8F0">%s</span>'
         '<span class="blink m" style="font-size:20px;color:%s">▌</span>' % (
             L.kf([(35.0, 'width:0;animation-timing-function:steps(%d,end)' % len(cmd)),
                   (35.9, 'width:%dch' % len(cmd))]), cmd, LIMA),
         330, 110, L.kf([(34.9, 'opacity:0'), (35.0, 'opacity:1'), (38.2, 'opacity:1;filter:none'),
                         (38.6, 'opacity:0;filter:blur(8px)')])))
    a(el('<div class="card m" style="padding:16px 22px;font-size:18px;color:#D9F99D;border-color:%s;'
         'box-shadow:0 0 28px rgba(163,230,53,.25)">carta.json</div>' % LIMA, 556, 300,
         L.kf([(35.6, 'opacity:0;transform:scale(.6)'), (35.95, 'opacity:1;transform:none'),
               (38.2, 'opacity:1;filter:none'), (38.6, 'opacity:0;filter:blur(8px)')])))
    esq = ['fluxograma.svg', 'fluxograma.png', 'processo.bpmn', 'processo.drawio', 'processo.mmd']
    dir_ = ['mapeamento.html', 'mapeamento.docx', 'mapeamento.md', 'atividades.csv']
    a(el('<span class="tag" style="background:#0F1E36;color:#BFDBFE">%s</span>' % escape(T('FLUXOGRAMA', 'FLOWCHART')),
         180, 176, blur_out))
    a(el('<span class="tag" style="background:#2A1E08;color:#FCD34D">%s</span>' % escape(T('MAPEAMENTO', 'PROCESS MAP')),
         880, 176, blur_out))
    for i, f in enumerate(esq):
        a(el('<span class="fic m">%s</span>' % f, 180, 210 + i * 52,
             L.kf([(36.0 + i * 0.2, 'opacity:0;transform:translateX(120px)'), (36.35 + i * 0.2, 'opacity:1;transform:none'),
                   (38.2, 'opacity:1;filter:none'), (38.6, 'opacity:0;filter:blur(8px)')])))
    for i, f in enumerate(dir_):
        a(el('<span class="fic m" style="background:#1F1708;border-color:#4A3510;color:#FCD9A8">%s</span>' % f,
             880, 210 + i * 52,
             L.kf([(36.1 + i * 0.2, 'opacity:0;transform:translateX(-120px)'), (36.45 + i * 0.2, 'opacity:1;transform:none'),
                   (38.2, 'opacity:1;filter:none'), (38.6, 'opacity:0;filter:blur(8px)')])))
    paineis = [(206, T('testes automatizados', 'automated tests'), None),
               (73, T('verificações de boa modelagem', 'modeling checks'), None),
               (None, T('casos simulados a cada análise', 'cases simulated per analysis'), T('4.000', '4,000')),
               (0, T('dependências para instalar', 'dependencies to install'), None)]
    for i, (v, r, fixo) in enumerate(paineis):
        t = 38.6 + i * 0.3
        caixa = L.kf([(t, 'opacity:0;transform:translateY(40px)'), (t + 0.45, 'opacity:1;transform:none'),
                      (42.4, 'opacity:1;filter:none'), (43.0, 'opacity:0;filter:blur(8px)')])
        if fixo:
            num = escape(fixo)
        else:
            cls, st = L.contador(v, t + 0.3, de=(14 if v == 0 else 0))
            num = '<span class="cnt %s" style="%s"></span>' % (cls, st)
        barra = L.kf([(t + 1.9, 'transform:scaleX(0)'), (t + 2.4, 'transform:scaleX(1)')])
        a(el('<div style="font-family:Poppins,Inter,sans-serif;font-weight:800;font-size:56px;color:#ECFCCB;'
             'line-height:1.1">%s</div><div style="font-size:16px;color:#CBD5E1;margin-top:10px">%s</div>'
             '<div class="%s" style="height:3px;background:%s;margin-top:18px;transform-origin:0 0;border-radius:2px">'
             '</div>' % (num, escape(r), barra, LIMA), 92 + i * 280, 200, 'card ' + caixa, 'padding:28px 26px',
             w=256, h=200))
    a(el(T('Medido na versão 1.13.0, com os exemplos do repositório.',
           'Measured on version 1.13.0, with the repository examples.'), 0, 470,
         'cap ' + L.kf([(40.6, 'opacity:0'), (41.0, 'opacity:1'), (42.4, 'opacity:1'), (43.0, 'opacity:0')]),
         'font-size:18px;color:#94A3B8'))

    # ---------------- Cena 6 · Assinatura (43–48 s)
    fim = lambda t: L.kf([(t, 'opacity:0;transform:translateY(10px)'), (t + 0.4, 'opacity:1;transform:none'),
                          (47.5, 'opacity:1;transform:none'), (48, 'opacity:0')])
    a(el('SENKU', 0, 196, 'p ' + L.kf([(43.6, 'opacity:0;transform:scale(.92);letter-spacing:.18em'),
                                       (44.1, 'opacity:1;transform:none;letter-spacing:.06em'),
                                       (47.5, 'opacity:1;transform:none;letter-spacing:.06em'), (48, 'opacity:0')]),
         'text-align:center;font-size:118px;color:#F1F5F9;line-height:1', w=1280))
    a(el(T('não desenha no chute. prova.', 'doesn’t guess the flow. proves it.'), 0, 344, fim(44.0),
         'text-align:center;font-size:28px;color:%s;font-weight:500' % LIMA, w=1280))
    pills = [T('Fluxograma em raias BPMN 2.0', 'Swimlane flowchart in BPMN 2.0'),
             T('Mapeamento completo', 'Full process map'), T('Aceite do dono do processo', 'Process owner sign-off')]
    a(el(''.join('<span class="pill %s">%s</span>' % (fim(44.3 + i * 0.15), escape(p)) for i, p in enumerate(pills)),
         0, 412, '', 'display:flex;gap:16px;justify-content:center', w=1280))
    a(el('Claude Code · BPMN 2.0 · Bizagi · Camunda · draw.io · Word · MIT', 0, 500, fim(44.6),
         'text-align:center;font-size:16px;color:#94A3B8', w=1280))

    rot = T('Senku: da conversa ao fluxograma e ao mapeamento do processo, com prova',
            'Senku: from conversation to flowchart and process map, with proof')
    corpo = '<div class="raiz" style="position:absolute;inset:0">%s</div>' % ''.join(h)
    return svg_doc(corpo, 1280, 640, 48, L, fontes, rot)


# ------------------------------------------------------------------ fluxo (36 s, 5 passos)

def fluxo(lang, fontes):
    T = (lambda pt, en: pt) if lang == 'pt' else (lambda pt, en: en)
    L = Linha(36)
    L.comentario = ('/* Linha do tempo: 36 s. 1 Você conta 0–5 · 2 A carta 5–12 · 3 A prova 12–21 · '
                    '4 Desenho e mapeamento 21–29 · 5 Aceite e TO-BE 29–36 */')
    L.reduzido = ('@media (prefers-reduced-motion: reduce){.raiz{--d:-34s!important;--ps:paused!important}'
                  '.bolha{animation:none}}')
    h = []
    a = h.append
    a(el('', 0, 0, 'gridbg', 'opacity:.45', w=1280, h=640))
    a(el(frasco(tam=0.7), 1180, 556))

    passos = [(0, 5, T('1 · Você conta', '1 · You tell')), (5, 12, T('2 · A carta', '2 · The charter')),
              (12, 21, T('3 · A prova', '3 · The proof')),
              (21, 29, T('4 · Desenho e mapeamento', '4 · Flowchart and process map')),
              (29, 36, T('5 · Aceite e TO-BE', '5 · Sign-off and TO-BE'))]
    # faixa de progresso
    for i, (t0, t1, nome) in enumerate(passos):
        x = 120 + i * 212
        enche = L.kf([(0, 'transform:scaleX(0)'), (max(t0, 0.01), 'transform:scaleX(0)'),
                      (t1 - 0.05, 'transform:scaleX(1)'), (35.6, 'transform:scaleX(1)'), (36, 'transform:scaleX(0)')])
        a(el('<div class="%s" style="height:4px;background:#F1F5F9;transform-origin:0 0;border-radius:2px"></div>' % enche,
             x, 70, '', 'background:#334155;border-radius:2px', w=200, h=4))
        a(el(escape(nome.split(' · ')[0]), x, 82, '', 'font-size:12px;color:#64748B;font-weight:600'))
        q = [(t0, 'opacity:0;transform:translateY(8px)'), (t0 + 0.3, 'opacity:1;transform:none')]
        if t1 < 36:
            q += [(t1 - 0.3, 'opacity:1;transform:none'), (t1, 'opacity:0;transform:translateY(-8px)')]
        else:
            q += [(35.6, 'opacity:1;transform:none'), (36, 'opacity:0')]
        a(el(escape(nome), 0, 24, L.kf(q), 'text-align:center;font-size:24px;font-weight:700;color:#F1F5F9', w=1280))

    def cap(texto, ent, sai):
        a(el(texto, 0, 586, 'cap ' + L.vis(ent, sai), 'font-size:20px'))

    # ---------------- Passo 1 · Você conta (0–5 s)
    falas = [(0.3, 'senku', T('Quando o pedido chega, quem dá o primeiro passo?', 'When a request arrives, who takes the first step?')),
             (1.1, 'voce', T('O comprador cota com três fornecedores.', 'The buyer gets quotes from three suppliers.')),
             (1.9, 'senku', T('E quando passa de R$ 5 mil?', 'And when it is above $5k?')),
             (2.7, 'voce', T('Aí o gerente aprova.', 'Then the manager approves.'))]
    for i, (t, quem, txt) in enumerate(falas):
        y = 128 + i * 98
        sai = L.kf([(t, 'opacity:0;transform:translateY(12px)'), (t + 0.35, 'opacity:1;transform:none'),
                    (4.4, 'opacity:1;transform:none;animation-timing-function:cubic-bezier(.5,0,.7,1)'),
                    (4.9, 'opacity:0;transform:translate(%dpx,%dpx) scale(.3)' % ((560 - 160) if quem == 'senku' else -200,
                                                                                  300 - y))])
        if quem == 'senku':
            a(el('<div style="display:flex;gap:14px;align-items:center">%s<div class="bub" style="font-size:19px;'
                 'border-color:rgba(163,230,53,.5)">%s</div></div>' % (frasco(tam=0.45), escape(txt)), 160, y, sai))
        else:
            a(el('<div style="display:flex;justify-content:flex-end"><div class="bub" style="font-size:19px;'
                 'background:#14213A">%s</div></div>' % escape(txt), 520, y, sai, w=600))
    cap(T('O Senku conduz a <b>entrevista</b>, um bloco por vez.', 'Senku runs the <b>interview</b>, one block at a time.'),
        1.4, 4.7)

    # ---------------- Passo 2 · A carta (5–12 s)
    sai2 = L.kf([(5.0, 'opacity:0;transform:scale(.7)'), (5.4, 'opacity:1;transform:none'),
                 (11.5, 'opacity:1;transform:none'), (12.0, 'opacity:0;transform:translateY(-16px)')])
    js = [('{', '#94A3B8'),
          ('  "processo": {"nome": "Compra de materiais"},', '#E2E8F0'),
          ('  "papeis": ["Solicitante", "Comprador", "Gerente"],', '#BFDBFE'),
          ('  "elementos": [', '#E2E8F0'),
          ('    {"id": "a2", "nome": "Cotar com 3 fornecedores"},', '#BFDBFE'),
          ('    {"id": "d1", "tipo": "decisao",', '#FCD9A8'),
          ('     "nome": "Acima de R$ 5 mil?"}', '#FCD9A8'),
          ('  ],', '#E2E8F0'),
          ('  "regras": ["Acima de R$ 5 mil, o gerente aprova"]', '#D9F99D'),
          ('}', '#94A3B8')]
    linhas = ''.join('<div class="%s" style="color:%s;white-space:pre">%s</div>' % (
        L.vis(5.5 + i * 0.18, None, de='translateX(-8px)', f=0.25), cor, escape(t)) for i, (t, cor) in enumerate(js))
    a(el('<div class="hd"><span class="dot" style="background:%s"></span><span class="m">carta.json</span></div>'
         '<div class="m" style="padding:16px 20px;font-size:14px;line-height:1.75">%s</div>' % (LIMA, linhas),
         100, 120, 'card ' + sai2, 'border-color:rgba(163,230,53,.45)', w=540, h=400))
    lac = [('ALTA', 'HIGH', '#7F1D1D', '#FECACA', T('Quem aprova quando o gerente está de férias?', 'Who approves when the manager is on leave?')),
           ('MÉDIA', 'MEDIUM', '#3A2A08', '#FCD34D', T('Quanto tempo o pedido espera antes da cotação?', 'How long does a request wait before quoting?')),
           ('BAIXA', 'LOW', '#1E293B', '#CBD5E1', T('Em que sistema a cotação fica registrada?', 'Which system records the quote?'))]
    itens = []
    for i, (pt, en, fundo, cor, txt) in enumerate(lac):
        t = 7.6 + i * 0.4
        itens.append('<div class="%s" style="display:flex;gap:12px;align-items:flex-start;padding:12px 0;'
                     'border-bottom:1px solid #1E2A44"><span class="tag" style="background:%s;color:%s;min-width:64px;'
                     'text-align:center">%s</span><span style="font-size:16px;line-height:1.35">%s</span></div>'
                     % (L.vis(t, None, de='translateX(16px)', f=0.3), fundo, cor, T(pt, en), escape(txt)))
    a(el('<div class="hd"><span class="m" style="color:#CBD5E1">python senku.py lacunas</span></div>'
         '<div style="padding:4px 22px">%s</div><div class="%s" style="padding:10px 22px"><span class="ok">✓ %s</span>'
         '</div>' % (''.join(itens), L.vis(9.6, None, de='scale(.9)'),
                     escape(T('respondida: nas férias, aprova o diretor', 'answered: on leave, the director approves'))),
         680, 120, 'card ' + L.kf([(7.2, 'opacity:0;transform:translateX(30px)'), (7.5, 'opacity:1;transform:none'),
                                   (11.5, 'opacity:1;transform:none'), (12.0, 'opacity:0;transform:translateY(-16px)')]),
         w=500))
    cap(T('Tudo o que você conta vira a <b>carta do processo</b>.', 'Everything you say goes into the <b>process charter</b>.'),
        5.6, 8.6)
    cap(T('O que falta vira <b>pergunta</b>, da mais importante para a menos.',
          'What is missing becomes a <b>question</b>, most important first.'), 8.8, 11.7)

    # ---------------- Passo 3 · A prova (12–21 s)
    sai3 = L.kf([(12.0, 'opacity:0;transform:translateY(16px)'), (12.3, 'opacity:1;transform:none'),
                 (20.5, 'opacity:1;transform:none'), (21.0, 'opacity:0;transform:translateY(-16px)')])
    g = ['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="320" viewBox="0 0 540 320">'
         '<defs><marker id="q" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
         '<path d="M0 0L10 5L0 10z" fill="#94A3B8"/></marker></defs>'
         '<circle cx="30" cy="120" r="13" fill="none" stroke="%s" stroke-width="2"/>'
         '<path d="M43 120H76" fill="none" stroke="#94A3B8" stroke-width="2" marker-end="url(#q)"/>'
         '<rect x="80" y="98" width="110" height="44" rx="9" fill="#1B2A47" stroke="%s" stroke-width="1.6"/>'
         '<text x="135" y="125" text-anchor="middle" font-size="14" fill="#E2E8F0">%s</text>'
         '<path d="M190 120H224" fill="none" stroke="#94A3B8" stroke-width="2" marker-end="url(#q)"/>'
         '<polygon points="252,92 280,120 252,148 224,120" fill="#2A2410" stroke="%s" stroke-width="1.8"/>'
         '<path d="M252 92V46H316" fill="none" stroke="#94A3B8" stroke-width="2" marker-end="url(#q)"/>'
         '<text x="262" y="66" font-size="12" fill="#CBD5E1">%s</text>'
         '<rect x="320" y="24" width="120" height="44" rx="9" fill="#1B2A47" stroke="%s" stroke-width="1.6"/>'
         '<text x="380" y="51" text-anchor="middle" font-size="14" fill="#E2E8F0">%s</text>'
         '<path d="M440 46H492" fill="none" stroke="#94A3B8" stroke-width="2" marker-end="url(#q)"/>'
         '<circle cx="508" cy="46" r="13" fill="none" stroke="%s" stroke-width="4"/>'
         '<path d="M252 148V214H316" fill="none" stroke="#94A3B8" stroke-width="2" marker-end="url(#q)"/>'
         '<text x="262" y="196" font-size="12" fill="#CBD5E1">%s</text>'
         % (VERDE, AZUL, escape(T('Pedir', 'Request')), AMBAR, escape(T('Sim', 'Yes')), AZUL,
            escape(T('Cotar', 'Quote')), VERMELHO, escape(T('Não', 'No')))]
    ruim = L.kf([(14.2, 'stroke:%s' % AZUL), (14.5, 'stroke:%s' % VERMELHO), (15.6, 'stroke:%s' % VERMELHO),
                 (15.9, 'stroke:%s' % AZUL)])
    g.append('<rect class="%s" x="320" y="192" width="120" height="44" rx="9" fill="#1B2A47" stroke-width="2"/>'
             '<text x="380" y="219" text-anchor="middle" font-size="14" fill="#E2E8F0">%s</text>'
             % (ruim, escape(T('Corrigir', 'Fix'))))
    g.append(linha_animada(L, 'M380 236V290H135V146', 15.4, VERDE, 2.4, dur=0.5))
    # fichas (tokens)
    f1 = L.kf([(12.6, 'opacity:0;transform:translate(30px,120px)'), (12.8, 'opacity:1;transform:translate(30px,120px)'),
               (13.1, 'transform:translate(135px,120px)'), (13.4, 'transform:translate(252px,120px)'),
               (13.7, 'transform:translate(252px,46px)'), (14.0, 'transform:translate(380px,46px)'),
               (14.3, 'opacity:1;transform:translate(508px,46px)'), (14.5, 'opacity:0;transform:translate(508px,46px)')])
    f2 = L.kf([(13.0, 'opacity:0;transform:translate(30px,120px)'), (13.2, 'opacity:1;transform:translate(30px,120px)'),
               (13.5, 'transform:translate(135px,120px)'), (13.8, 'transform:translate(252px,120px)'),
               (14.0, 'transform:translate(252px,214px)'), (14.3, 'transform:translate(380px,214px)'),
               (15.9, 'opacity:1;transform:translate(380px,214px)'), (16.2, 'transform:translate(380px,290px)'),
               (16.5, 'transform:translate(135px,290px)'), (16.8, 'transform:translate(135px,120px)'),
               (17.1, 'transform:translate(252px,120px)'), (17.4, 'transform:translate(252px,46px)'),
               (17.7, 'transform:translate(380px,46px)'), (18.0, 'opacity:1;transform:translate(508px,46px)'),
               (18.2, 'opacity:0;transform:translate(508px,46px)')])
    for cls in (f1, f2):
        g.append('<circle class="%s" cx="0" cy="0" r="8" fill="%s" stroke="#ECFCCB" stroke-width="2"/>' % (cls, LIMA))
    g.append('</svg>')
    a(el(''.join(g), 90, 130, sai3))
    a(el('<span class="err">⚠ %s</span>' % escape(T('“Corrigir” não chega ao fim', '“Fix” never reaches the end')),
         400, 400, L.kf([(14.4, 'opacity:0;transform:translateY(8px)'), (14.7, 'opacity:1;transform:none'),
                         (15.8, 'opacity:1;transform:none'), (16.0, 'opacity:0')])))
    a(el('<span class="ok">✓ %s</span>' % escape(T('todo caminho chega ao fim · nada trava', 'every path ends · nothing deadlocks')),
         240, 440, L.vis(16.0, 20.6, de='translateY(8px) scale(.9)')))
    # simulação
    alturas = [6, 14, 30, 52, 78, 100, 92, 74, 54, 38, 24, 14, 8, 4]
    barras = ''.join('<div class="%s" style="width:22px;height:%dpx;background:%s;border-radius:3px 3px 0 0;'
                     'transform-origin:50%% 100%%"></div>' % (
                         L.kf([(16.4 + i * 0.09, 'transform:scaleY(0)'), (16.8 + i * 0.09, 'transform:scaleY(1)')]),
                         int(v * 1.7), '#475569' if i < 5 else (AMBAR if i > 7 else '#94A3B8'))
                     for i, v in enumerate(alturas))
    def marc(x, t, txt, cor, lado):
        rot = ('<div class="ab" style="top:0;%s:6px;font-size:13px;font-weight:600;color:%s;white-space:nowrap">%s</div>'
               % ('right' if lado < 0 else 'left', cor, escape(txt)))
        return el('%s<div class="ab" style="left:0;top:22px;width:2px;height:178px;background:%s"></div>' % (rot, cor),
                  x, 52, L.vis(t, None, de='translateY(-6px)', f=0.3), w=2, h=200)
    a(el('<div class="hd"><span class="m" style="color:#CBD5E1">%s</span></div>'
         '<div style="position:relative;height:320px"><div class="ab" style="left:24px;bottom:60px;display:flex;'
         'gap:4px;align-items:flex-end">%s</div>%s%s<div class="ab" style="left:24px;bottom:30px;font-size:13px;'
         'color:#94A3B8">%s</div></div>' % (
             escape(T('simulação · 4.000 casos', 'simulation · 4,000 cases')), barras,
             marc(24 + 5 * 26 + 11, 18.0, T('50% até 14,1 d', '50% within 14.1 d'), '#E2E8F0', -1),
             marc(24 + 8 * 26 + 11, 18.4, T('80% até 17,2 d', '80% within 17.2 d'), AMBAR, 1),
             escape(T('dias úteis, do pedido ao material entregue', 'business days, from request to delivery'))),
         700, 120, 'card ' + L.kf([(16.0, 'opacity:0;transform:translateX(30px)'), (16.3, 'opacity:1;transform:none'),
                                   (20.5, 'opacity:1;transform:none'), (21.0, 'opacity:0;transform:translateY(-16px)')]),
         w=440, h=364))
    cap(T('Fichas percorrem <b>todos os caminhos</b>: nada trava, tudo termina.',
          'Tokens run down <b>every path</b>: nothing deadlocks, everything ends.'), 12.6, 15.9)
    cap(T('E <b>4.000 casos simulados</b> dão o prazo real, não só a média.',
          'And <b>4,000 simulated cases</b> give the real lead time, not just the average.'), 16.2, 20.7)

    # ---------------- Passo 4 · Desenho e mapeamento (21–29 s)
    sai4 = L.kf([(21.0, 'opacity:0;transform:translateY(16px)'), (21.3, 'opacity:1;transform:none'),
                 (28.5, 'opacity:1;transform:none'), (29.0, 'opacity:0;transform:translateY(-16px)')])
    a(el(raias_svg(L, T, 21.3, largura=600, altura=190), 80, 130, sai4))
    for i, f in enumerate(['SVG', 'PNG', 'BPMN 2.0', 'draw.io', 'Mermaid']):
        a(el('<span class="fic m">%s</span>' % f, 80 + i * 112, 344, L.vis(24.6 + i * 0.12, 28.6, de='translateY(8px)', f=0.25)))
    raci = [(T('Pedir material', 'Pedir material'), 'R', 'I', ''),
            (T('Cotar', 'Cotar'), '', 'R', 'I'),
            (T('Aprovar compra', 'Aprovar compra'), 'I', 'C', 'A'),
            (T('Emitir pedido', 'Emitir pedido'), 'I', 'R', '')]
    cores = {'R': AZUL, 'A': VERDE, 'C': AMBAR, 'I': '#94A3B8', '': '#1E2A44'}
    tab = ['<div style="display:grid;grid-template-columns:170px 70px 70px 70px;gap:6px;font-size:14px">',
           '<div></div>'] + ['<div style="color:#94A3B8;font-size:12px;text-align:center">%s</div>' % escape(x)
                             for x in (T('Solic.', 'Req.'), T('Compr.', 'Buyer'), T('Gerente', 'Mgr.'))]
    for i, (nome, *cel) in enumerate(raci):
        tab.append('<div style="color:#E2E8F0;padding:6px 0">%s</div>' % escape(nome))
        for j, v in enumerate(cel):
            tab.append('<div class="%s" style="text-align:center;padding:6px 0;border-radius:6px;font-weight:700;'
                       'background:%s22;color:%s">%s</div>' % (
                           L.vis(23.2 + i * 0.25 + j * 0.08, None, de='scale(.6)', f=0.25), cores[v], cores[v], v))
    tab.append('</div>')
    a(el('<div class="hd"><span class="dot" style="background:%s"></span>%s</div><div style="padding:18px 22px">%s'
         '</div>' % (AMBAR, escape(T('Matriz RACI · do mapeamento', 'RACI matrix · from the process map')), ''.join(tab)),
         730, 120, 'card ' + L.kf([(22.6, 'opacity:0;transform:translateX(30px)'), (22.9, 'opacity:1;transform:none'),
                                   (28.5, 'opacity:1;transform:none'), (29.0, 'opacity:0;transform:translateY(-16px)')]),
         w=460))
    for i, f in enumerate(['HTML', 'Word', 'Markdown', 'CSV']):
        a(el('<span class="fic m" style="background:#1F1708;border-color:#4A3510;color:#FCD9A8">%s</span>' % f,
             730 + i * 112, 400, L.vis(25.2 + i * 0.12, 28.6, de='translateY(8px)', f=0.25)))
    cap(T('Do <b>mesmo arquivo</b> saem o fluxograma e o mapeamento completo.',
          'The flowchart and the full process map come from the <b>same file</b>.'), 23.6, 28.6)

    # ---------------- Passo 5 · Aceite e TO-BE (29–36 s)
    fim5 = lambda t, de='translateY(12px)': L.kf([(t, 'opacity:0;transform:%s' % de), (t + 0.35, 'opacity:1;transform:none'),
                                                  (35.6, 'opacity:1;transform:none'), (36, 'opacity:0')])
    cmd = T('aprovar carta.json --por "Gerente de Suprimentos"', 'aprovar carta.json --por "Supply manager"')
    a(el('<span class="m" style="font-size:16px;color:#D9F99D">$ </span><span class="m %s" style="display:inline-block;'
         'overflow:hidden;white-space:nowrap;vertical-align:bottom;font-size:16px;color:#E2E8F0">%s</span>' % (
             L.kf([(29.3, 'width:0;animation-timing-function:steps(%d,end)' % len(cmd)), (30.2, 'width:%dch' % len(cmd))]),
             escape(cmd)), 100, 140, fim5(29.2, 'none')))
    a(el('<div class="stamp" style="color:%s;border-color:%s;background:rgba(6,40,30,.88)">%s</div>' % (
        VERDE, VERDE, escape(T('APROVADO', 'APPROVED'))), 170, 230,
        L.kf([(30.4, 'opacity:0;transform:rotate(-8deg) scale(1.6)'), (30.75, 'opacity:1;transform:rotate(-8deg) scale(1)'),
              (35.6, 'opacity:1;transform:rotate(-8deg) scale(1)'), (36, 'opacity:0;transform:rotate(-8deg) scale(1)')])))
    a(el('<div style="display:flex;align-items:center;gap:10px">%s<span class="m" style="font-size:15px;color:#A7F3D0">'
         '%s</span></div>' % (cadeado(VERDE), escape(T('hash 9C41E07B · por seção', 'hash 9C41E07B · per section'))),
         176, 330, fim5(30.9)))
    difs = [('−', VERMELHO, T('Lançar cotação no ERP', 'Lançar cotação no ERP')),
            ('+', VERDE, T('Aprovação automática até R$ 5 mil', 'Aprovação automática até R$ 5 mil')),
            ('~', AMBAR, T('espera antes de cotar: 3d → 1d', 'wait before quoting: 3d → 1d'))]
    linhas = ''.join('<div class="%s" style="display:flex;gap:14px;padding:10px 0;border-bottom:1px solid #1E2A44;'
                     'font-size:17px"><span class="m" style="color:%s;font-weight:700;width:14px">%s</span>'
                     '<span>%s</span></div>' % (fim5(31.8 + i * 0.4, 'translateX(16px)'), cor, s, escape(t))
                     for i, (s, cor, t) in enumerate(difs))
    a(el('<div class="hd"><span class="m" style="color:#CBD5E1">comparar --contra to-be/carta.json</span></div>'
         '<div style="padding:8px 22px 14px">%s</div>' % linhas, 640, 150, 'card ' + fim5(31.3, 'translateX(30px)'), w=540))
    a(el('<span class="tag" style="background:#1E293B;color:#94A3B8">AS-IS</span> <span style="color:#64748B">→</span> '
         '<span class="tag" style="background:#0F2A1E;color:#A7F3D0">TO-BE</span>', 660, 108, fim5(31.3)))
    cap(T('O dono <b>aprova</b>. O TO-BE nasce comparado com o AS-IS.',
          'The owner <b>signs off</b>. The TO-BE is born compared with the AS-IS.'), 31.0, 35.6)

    rot = T('Como o Senku funciona: entrevista, carta, prova, desenho, mapeamento e aceite',
            'How Senku works: interview, charter, proof, flowchart, process map and sign-off')
    corpo = '<div class="raiz" style="position:absolute;inset:0">%s</div>' % ''.join(h)
    return svg_doc(corpo, 1280, 640, 36, L, fontes, rot)


def main():
    with open(FONTES, encoding='utf-8') as f:
        fontes = f.read()
    destino = os.path.join(RAIZ, 'assets')
    os.makedirs(destino, exist_ok=True)
    for nome, func in (('senku-banner', banner), ('senku-fluxo', fluxo)):
        for lang, suf in (('pt', ''), ('en', '-en')):
            caminho = os.path.join(destino, '%s%s.svg' % (nome, suf))
            with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
                f.write(func(lang, fontes))
            print('%-28s %7d bytes' % (os.path.basename(caminho), os.path.getsize(caminho)))


if __name__ == '__main__':
    main()
