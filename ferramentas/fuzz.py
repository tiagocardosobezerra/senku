"""
Fuzz: troca campos do exemplo de compras por valores de tipo errado e roda todos os comandos; nenhum pode
levantar exceção (só ErroDeUso). Uso: python ferramentas/fuzz.py [SEMENTE] [ITERACOES]
"""
import sys, os, json, random, io, copy, traceback, tempfile  # noqa: E401
SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SK)
import senku
from carta.util import ErroDeUso
from contextlib import redirect_stdout, redirect_stderr
base = json.load(open(os.path.join(SK, 'exemplos', 'compras', 'carta.json'), encoding='utf-8'))
VALS = [None, 0, -1, 1.5, True, '', 'x', [], [None], ['a', 1], {}, {'a': 1}, [{}], '∞☃', 1e308, [[1]], {'para': None}]
def paths(o, p=()):
    yield p
    if isinstance(o, dict):
        for k, v in o.items(): yield from paths(v, p + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]): yield from paths(v, p + (i,))
allp = [p for p in paths(base) if p]
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
fails = {}
tmp = tempfile.mkdtemp()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
for it in range(N):
    d = copy.deepcopy(base)
    for _ in range(random.randint(1, 3)):
        p = random.choice(allp)
        o = d
        try:
            for k in p[:-1]: o = o[k]
            o[p[-1]] = copy.deepcopy(random.choice(VALS))
        except Exception:
            pass
    cp = os.path.join(tmp, 'carta.json')
    json.dump(d, open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
    for f in ('carta.aprovacao.json',):
        if os.path.exists(os.path.join(tmp, f)): os.remove(os.path.join(tmp, f))
    for cmd in (['validar', cp], ['lacunas', cp, '--todas'], ['analisar', cp], ['analisar', cp, '--json'],
                ['documentar', cp, '-o', os.path.join(tmp, 's')], ['situacao', cp], ['aprovar', cp, '--por', 'A (B)'],
                ['comparar', cp]):
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                senku.main(cmd)
        except (ErroDeUso, SystemExit):
            pass
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)[-1]
            key = (cmd[0], type(e).__name__, f'{os.path.basename(tb.filename)}:{tb.lineno}')
            if key not in fails:
                fails[key] = (str(e)[:100], [x for x in d.items()][:0], it)
                saida = os.path.join(tempfile.gettempdir(), 'senku-fuzz')
                os.makedirs(saida, exist_ok=True)
                with open(os.path.join(saida, f'fuzz_{key[0]}_{tb.lineno}.json'), 'w', encoding='utf-8') as arq:
                    json.dump(d, arq, ensure_ascii=False, indent=1)
for k, v in fails.items(): print(k, v[0], 'iter', v[2])
print('done', len(fails))
