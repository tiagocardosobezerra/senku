"""
Gera os dados e as imagens da página do projeto (`docs/`, publicada no GitHub Pages).

    python ferramentas/gerar_site.py

Tudo sai do exemplo de compras (`exemplos/compras/carta.json`) e do próprio Senku, sem número digitado à mão:

* `docs/img/fluxo-compras.svg`: o fluxograma real do exemplo, nas cores escuras da página, com cada seta marcada
  com `data-de` e `data-para` para a demonstração da prova de fichas;
* `docs/dados.js`: a análise (tempos, percentis, carga, oportunidades), o histograma da simulação de 4.000 casos e
  a saída real do `validar` para a carta certa e para uma cópia quebrada de propósito;
* `docs/img/mapa-*.png`: a vitrine do mapeamento, copiada de `assets/vitrine/`.

Rode de novo quando o exemplo ou o motor mudar, e confira a página.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from carta import VERSAO  # noqa: E402
from carta import analise  # noqa: E402
from carta.modelo import carregar  # noqa: E402
from carta.simulacao import simular  # noqa: E402

CARTA = os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json')
SVG = os.path.join(RAIZ, 'exemplos', 'compras', 'saida', 'sup-01-compra-de-materiais-indiretos-as-is.svg')
DOCS = os.path.join(RAIZ, 'docs')
MIN_DIA = 480  # minutos úteis num dia útil, como na análise

# cor clara do SVG gerado -> cor da página escura
NOS = '#111C30'
CORES = [
    ('stroke="#ffffff" stroke-width="3" paint-order="stroke"', 'stroke="#0B1220" stroke-width="3" paint-order="stroke"'),
    ('fill="#1d2733"', 'fill="#E2E8F0"'),
    ('fill="#5b6878"', 'fill="#94A3B8"'),
    ('fill="#44546a"', 'fill="#64748B"'),
    ('stroke="#44546a"', 'stroke="#64748B"'),
    ('fill="#e3e9f2"', 'fill="#12233D"'),
    ('fill="#f6f8fb"', 'fill="#0E1729"'),
    ('fill="#eef0f3"', 'fill="#131D33"'),
    ('stroke="#c5cfdc"', 'stroke="#1E2A44"'),
    ('fill="#fff8e1"', 'fill="#2A2412"'),
    ('#2e7d32', '#34D399'),
    ('#a86b00', '#F59E0B'),
    ('#b3261e', '#F87171'),
]


def _caixa(corpo):
    xs, ys = [], []
    for r in re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', corpo):
        x, y, w, h = map(float, r.groups())
        xs += [x, x + w]
        ys += [y, y + h]
    for c in re.finditer(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"', corpo):
        x, y, rr = map(float, c.groups())
        xs += [x - rr, x + rr]
        ys += [y - rr, y + rr]
    for p in re.finditer(r'<path d="M([\d.]+),([\d.]+) L([\d.]+),([\d.]+) L([\d.]+),([\d.]+) L([\d.]+),([\d.]+) z"', corpo):
        v = list(map(float, p.groups()))
        xs += v[0::2]
        ys += v[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _dist(pt, b):
    x, y = pt
    dx = max(b[0] - x, 0, x - b[2])
    dy = max(b[1] - y, 0, y - b[3])
    return (dx * dx + dy * dy) ** .5


def fluxo_escuro():
    with open(SVG, encoding='utf-8') as f:
        s = f.read()
    nos = {m.group(1): _caixa(m.group(2)) for m in re.finditer(r'<g data-id="([^"]+)">(.*?)</g>', s, re.S)}

    def marcar(m):
        pts = re.findall(r'([\d.]+),([\d.]+)', m.group(1))
        a, b = tuple(map(float, pts[0])), tuple(map(float, pts[-1]))
        de = min(nos, key=lambda n: _dist(a, nos[n]))
        para = min(nos, key=lambda n: _dist(b, nos[n]))
        return m.group(0).replace('<path ', f'<path class="seta" data-de="{de}" data-para="{para}" ', 1)
    s = re.sub(r'<path d="([^"]+)"[^>]*marker-end[^>]*>', marcar, s)
    # fundo e raias brancos ficam escuros; caixas das atividades um tom acima
    s = s.replace('<rect width="100%" height="100%" fill="#ffffff"/>', '<rect width="100%" height="100%" fill="#0B1220"/>')
    s = re.sub(r'(<rect [^>]*rx="[\d.]+" )fill="#ffffff"', r'\1fill="' + NOS + '"', s)
    s = re.sub(r'(<circle [^>]*)fill="#ffffff"', r'\1fill="' + NOS + '"', s)
    s = s.replace('fill="#ffffff"', 'fill="#0B1220"')
    for velho, novo in CORES:
        s = s.replace(velho, novo)
    s = s.replace('font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif"',
                  'font-family="Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif"')
    s = s.replace('<g data-id=', '<g class="no" data-id=')
    with open(os.path.join(DOCS, 'img', 'fluxo-compras.svg'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(s)
    return sorted(nos)


def _validar(caminho):
    r = subprocess.run([sys.executable, os.path.join(RAIZ, 'senku.py'), 'validar', caminho],
                       capture_output=True, cwd=RAIZ, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    texto = r.stdout.decode('utf-8').replace('\r\n', '\n').strip()
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.replace(caminho, 'carta.json')


def validacoes():
    certo = _validar(CARTA)
    with open(CARTA, encoding='utf-8') as f:
        dados = json.load(f)
    quebrada = copy.deepcopy(dados)
    for e in quebrada['elementos']:
        if e['id'] == 'a1b':     # "Corrigir requisição" perde a saída: depois dela, o que acontece?
            e.pop('segue', None)
    pasta = tempfile.mkdtemp()
    try:
        caminho = os.path.join(pasta, 'carta.json')
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(quebrada, f, ensure_ascii=False)
        errado = _validar(caminho)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    return certo, errado


def dados():
    c = carregar(CARTA)
    r = analise.analisar(c)
    sim = simular(c, duracoes=analise._duracoes_do_detalhe(c), com_tempos=True)
    hist = sorted(Counter(int(t // MIN_DIA) for t in sim['tempos']).items())
    papeis = {p['id']: p['nome'] for p in c.dados.get('papeis', [])}
    certo, errado = validacoes()
    t = r['tempos']
    return {
        'versao': VERSAO,
        'processo': {k: c.processo.get(k) for k in ('codigo', 'nome', 'dono', 'volume', 'prazo_informado')},
        'contagem': r['contagem'],
        'tempos_dias': {
            'execucao_h': round(t['execucao'] / 60, 1),
            'espera': round(t['espera'] / MIN_DIA, 1),
            'lead_time': round(t['lead_time'] / MIN_DIA, 1),
            'esperado': round(t['lead_time_esperado'] / MIN_DIA, 1),
            'eficiencia_pct': round(t['eficiencia'] * 100),
            'p50': round(sim['p50'] / MIN_DIA, 1), 'p80': round(sim['p80'] / MIN_DIA, 1),
            'p90': round(sim['p90'] / MIN_DIA, 1),
        },
        'casos': sim['casos'],
        'histograma': hist,
        'passagens_caso': len(r['passagens_caminho']),
        'retrabalho': r['retrabalho'],
        'valor': {k: v['atividades'] for k, v in r['valor'].items() if k != 'sem'},
        'carga': {
            'casos_mes': r['carga']['casos_mes'],
            'horas_mes': round(r['carga']['horas_mes']),
            'pessoas': round(r['carga']['pessoas'], 1),
            'por_papel': [[papeis.get(p, p), round(h), round(n, 1)] for p, h, n in r['carga']['por_papel']],
        },
        'oportunidades': [{'desperdicio': o['desperdicio'], 'texto': o['texto']} for o in r['oportunidades'][:5]],
        'validar_ok': certo,
        'validar_quebrado': errado,
    }


def main():
    os.makedirs(os.path.join(DOCS, 'img'), exist_ok=True)
    nos = fluxo_escuro()
    d = dados()
    d['nos'] = nos
    with open(os.path.join(DOCS, 'dados.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('/* Gerado por ferramentas/gerar_site.py a partir de exemplos/compras/carta.json. Não edite à mão. */\n')
        f.write('window.SENKU = ' + json.dumps(d, ensure_ascii=False, indent=1) + ';\n')
    for nome in sorted(os.listdir(os.path.join(RAIZ, 'assets', 'vitrine'))):
        shutil.copyfile(os.path.join(RAIZ, 'assets', 'vitrine', nome), os.path.join(DOCS, 'img', nome))
    print('✓ docs/img/fluxo-compras.svg · docs/dados.js · docs/img/mapa-*.png')


if __name__ == '__main__':
    main()
