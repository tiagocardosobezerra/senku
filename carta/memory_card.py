"""
Memory Card: o cartão de memória dos processos mapeados.

Como o memory card de um videogame, cada processo aprovado fica salvo (um "save"), com versão e histórico,
para ser carregado de novo quando precisar. É o mesmo cartão do Vegapunk: um repositório git do usuário no
GitHub, privado por padrão, com uma pasta por solução. A do Senku é `saves/senku/`:

    saves/senku/<categoria>/<secao>/<artigo>/
        README.md                 o artigo (o GitHub mostra ao abrir a pasta), com o fluxograma
        ficha.json                versão, status, processo, aceite, números, relacionados, histórico
        carta.json                a carta aprovada (a fonte de tudo)
        carta.aprovacao.json      o aceite do dono do processo
        <base>.svg/.bpmn/...      o fluxograma e o mapeamento, gerados pelo `documentar`
    CATALOGO.md                   gerado a cada envio: por solução, categoria e seção (o mesmo do Vegapunk)

O Senku só grava a própria pasta (`saves/senku/`) e o `CATALOGO.md`: nunca toca nos saves de outras
soluções. A ficha segue o formato do Vegapunk (solução, categoria, seção, artigo, versão, status,
relacionados, histórico), para os dois lerem o mesmo catálogo. Qual é o cartão fica só nesta instalação
(`local/memory_card.json`, fora do git e do pacote). Guia: referencias/memory-card.md.
"""

import datetime
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVES = 'saves'
SOLUCAO = 'Senku'
PASTA_SOLUCAO = 'senku'
INSTANCIA = 'senku'           # o `conferir` do Vegapunk pula os saves de instância que ele não tem
STATUS = ('rascunho', 'em-uso')
CORPO_INI, CORPO_FIM = '<!-- corpo -->', '<!-- /corpo -->'
_REPO = re.compile(r'^[\w.-]+/[\w.-]+$')

README_DO_CARTAO = """# Memory Card

Cartão de memória das soluções: cada entrega pronta fica salva aqui, com versão e histórico.

Cada save fica em `saves/<solucao>/<categoria>/<secao>/<artigo>/`. A solução é a ferramenta que gerou a
entrega (o Vegapunk, o Senku ou outra). Em cada pasta, o `README.md` é o artigo e o `ficha.json` guarda
versão, status, relacionados e histórico.

O [CATALOGO.md](CATALOGO.md) lista os saves por solução, categoria e seção. É gerado a cada envio: não
edite à mão. Cada mudança num save sobe a versão e exige um motivo, que entra no histórico e no commit.
"""

ONDE_FUNCIONA = ('o Memory Card só funciona onde há o `git`, o GitHub CLI (`gh`) autenticado e a pasta do '
                 'cartão: o Claude Code (ou um terminal) na máquina do usuário. Numa sandbox, como a do '
                 'claude.ai, ele não está disponível.')
OUTRA_MAQUINA = ('este Memory Card foi configurado em outra máquina (a pasta do cartão, {pasta}, não existe aqui). '
                 'Daqui não dá para ler nem enviar: entregue os arquivos do processo e diga que salvar é pelo '
                 'Claude Code na máquina do cartão. Não rode `iniciar` para "consertar": isso criaria outro cartão.')


class CartaoRecusado(RuntimeError):
    """O comando do cartão não pode seguir."""


# ------------------------------------------------------------------ configuração

def caminho_config():
    return os.path.join(RAIZ, 'local', 'memory_card.json')


def _ler(caminho):
    if not caminho or not os.path.exists(caminho):
        return None
    with open(caminho, encoding='utf-8-sig') as f:
        return f.read()


def _gravar(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto if texto.endswith('\n') else texto + '\n')


def configurado():
    """True quando esta instalação tem um cartão (não confere a pasta nem a rede)."""
    if os.environ.get('SENKU_MEMORY_CARD_DIR') == '-':
        return False
    return bool(os.environ.get('SENKU_MEMORY_CARD_REPO') or os.environ.get('SENKU_MEMORY_CARD_DIR')
                or os.path.exists(caminho_config()))


def config():
    """{'repo', 'pasta', 'publico'} do cartão. `repo` None: cartão só local (git sem remoto)."""
    if not configurado():
        raise CartaoRecusado('nenhum Memory Card configurado nesta instalação. Ligue ao cartão que já existe com: '
                             'python senku.py cartao iniciar --repo SEU_USUARIO/memory-card')
    c = json.loads(_ler(caminho_config()) or '{}')
    repo = os.environ.get('SENKU_MEMORY_CARD_REPO') or c.get('repo')
    if repo == '-':                                  # SENKU_MEMORY_CARD_REPO=-: cartão só local (os testes usam)
        repo = None
    pasta = os.environ.get('SENKU_MEMORY_CARD_DIR') or c.get('pasta')
    if not pasta:
        if not repo:
            raise CartaoRecusado(f'configuração do cartão sem repositório nem pasta: {caminho_config()}')
        pasta = os.path.join(os.path.expanduser('~'), repo.split('/')[1])
    return {'repo': repo, 'pasta': os.path.abspath(pasta), 'publico': bool(c.get('publico'))}


def _pasta_e_desta_maquina(pasta):
    if re.match(r'^[A-Za-z]:[\\/]', pasta or '') and os.name != 'nt':
        return False
    return os.path.isdir(os.path.dirname(os.path.abspath(pasta)))


def disponivel():
    """(True, '') se o cartão funciona aqui; senão (False, motivo). Não usa a rede."""
    try:
        c = config()
    except CartaoRecusado as e:
        return False, str(e)
    if not os.path.isdir(os.path.join(c['pasta'], '.git')):
        if not _pasta_e_desta_maquina(c['pasta']):
            return False, OUTRA_MAQUINA.format(pasta=c['pasta'])
        return False, f'a pasta do cartão ainda não foi clonada nesta máquina ({c["pasta"]})'
    if shutil.which('git') is None:
        return False, '`git` não encontrado. ' + ONDE_FUNCIONA
    if c['repo'] and shutil.which('gh') is None:
        return False, 'GitHub CLI (`gh`) não encontrado. ' + ONDE_FUNCIONA
    return True, ''


def _rodar(args, cwd=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except FileNotFoundError:
        raise CartaoRecusado(f'`{args[0]}` não encontrado. ' + ONDE_FUNCIONA)
    if r.returncode != 0:
        raise CartaoRecusado(f'{" ".join(args[:3])} falhou: {(r.stderr or r.stdout).strip()}')
    return r.stdout


def _exigir_gh():
    if shutil.which('gh') is None:
        raise CartaoRecusado('GitHub CLI (`gh`) não encontrado. ' + ONDE_FUNCIONA)
    if subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode != 0:
        raise CartaoRecusado('o `gh` não está autenticado (rode `gh auth login`). ' + ONDE_FUNCIONA)


def _visibilidade(repo):
    return json.loads(_rodar(['gh', 'repo', 'view', repo, '--json', 'visibility']))['visibility']


def conferir_privado():
    """Recusa se o cartão não for privado no GitHub (a não ser que tenha sido ligado com --publico)."""
    c = config()
    if not c['repo']:
        return
    _exigir_gh()
    vis = _visibilidade(c['repo'])
    if vis != 'PRIVATE' and not c['publico']:
        raise CartaoRecusado(f'{c["repo"]} está {vis}: o Memory Card só aceita envio com o repositório PRIVATE')


def _remoto_de(pasta):
    try:
        return _rodar(['git', 'remote', 'get-url', 'origin'], cwd=pasta).strip()
    except CartaoRecusado:
        return ''


def iniciar(repo=None, pasta=None, publico=False, substituir=False):
    """Liga esta instalação ao cartão (o mesmo do Vegapunk): usa o repositório se ele existe (recusa se
    público), cria privado se não existe, e reaproveita um clone que já está na máquina. Sem `repo`, cria
    um cartão só local em `pasta` (git sem remoto). Só com o pedido do usuário."""
    if os.path.exists(caminho_config()) and not substituir:
        atual = json.loads(_ler(caminho_config()) or '{}')
        raise CartaoRecusado(f'esta instalação já tem um Memory Card ({atual.get("repo") or "local"}, pasta '
                             f'{atual.get("pasta")}). Para trocar, só com o pedido do usuário: iniciar ... --substituir')
    if repo:
        if not _REPO.match(repo):
            raise CartaoRecusado(f'repositório inválido: {repo!r} (use DONO/NOME)')
        _exigir_gh()
        existe = subprocess.run(['gh', 'repo', 'view', repo, '--json', 'name'], capture_output=True).returncode == 0
        if not existe:
            _rodar(['gh', 'repo', 'create', repo, '--public' if publico else '--private',
                    '--description', 'Memory Card: as entregas salvas pelas soluções (Vegapunk, Senku...)'])
        vis = _visibilidade(repo)
        if vis != 'PRIVATE' and not publico:
            raise CartaoRecusado(f'{repo} já existe e está {vis}: use um repositório privado '
                                 '(ou --publico, se for de propósito)')
        pasta = os.path.abspath(pasta or os.path.join(os.path.expanduser('~'), repo.split('/')[1]))
        if os.path.isdir(os.path.join(pasta, '.git')):
            remoto = _remoto_de(pasta).lower()
            if repo.lower() not in remoto:
                raise CartaoRecusado(f'a pasta {pasta} já é um clone de outro repositório ({remoto or "sem remoto"})')
        else:
            if os.path.exists(pasta) and os.listdir(pasta):
                raise CartaoRecusado(f'a pasta já existe e não está vazia: {pasta}')
            _rodar(['gh', 'repo', 'clone', repo, pasta])
    else:
        if not pasta:
            raise CartaoRecusado('sem --repo, diga a pasta do cartão local: --pasta DIR')
        pasta = os.path.abspath(pasta)
        if not os.path.isdir(os.path.join(pasta, '.git')):
            os.makedirs(pasta, exist_ok=True)
            _rodar(['git', 'init', '-q'], cwd=pasta)
    _gravar(caminho_config(), json.dumps({'repo': repo, 'pasta': pasta, 'publico': bool(publico)},
                                         ensure_ascii=False, indent=2))
    if not os.path.exists(os.path.join(pasta, 'README.md')):
        _gravar(os.path.join(pasta, 'README.md'), README_DO_CARTAO)
        _gravar(os.path.join(pasta, 'CATALOGO.md'), gerar_catalogo_md([]))
        _rodar(['git', 'add', 'README.md', 'CATALOGO.md'], cwd=pasta)
        _rodar(['git', 'commit', '-q', '-m', 'Memory Card'], cwd=pasta)
        if repo:
            _rodar(['git', 'branch', '-M', 'main'], cwd=pasta)
            _rodar(['git', 'push', '-q', '-u', 'origin', 'main'], cwd=pasta)
    return {'repo': repo, 'pasta': pasta, 'publico': bool(publico)}


def preparar_pasta(atualizar=True):
    c = config()
    pasta = c['pasta']
    if not os.path.isdir(os.path.join(pasta, '.git')):
        if not _pasta_e_desta_maquina(pasta):
            raise CartaoRecusado(OUTRA_MAQUINA.format(pasta=pasta))
        if not c['repo']:
            raise CartaoRecusado(f'a pasta do cartão local não existe: {pasta}')
        _exigir_gh()
        _rodar(['gh', 'repo', 'clone', c['repo'], pasta])
    elif atualizar and c['repo']:
        try:
            _rodar(['git', 'pull', '--ff-only', '--quiet'], cwd=pasta)
        except CartaoRecusado as e:
            print(f'AVISO: não consegui atualizar o cartão ({e}); usando a cópia local.', file=sys.stderr)
    return pasta


def publicar(pasta, mensagem):
    """Gera o catálogo, faz o commit só da pasta do Senku e do catálogo e envia (privado antes e depois)."""
    c = config()
    conferir_privado()
    _gravar(os.path.join(pasta, 'CATALOGO.md'), gerar_catalogo_md(ler_catalogo(pasta)))
    _rodar(['git', 'add', '-A', '--', f'{SAVES}/{PASTA_SOLUCAO}', 'CATALOGO.md'], cwd=pasta)
    _rodar(['git', 'commit', '-q', '-m', mensagem, '--', f'{SAVES}/{PASTA_SOLUCAO}', 'CATALOGO.md'], cwd=pasta)
    if c['repo']:
        conferir_privado()
        _rodar(['git', 'push', '-q'], cwd=pasta)


# ------------------------------------------------------------------ fichas e catálogo (formato do Vegapunk)

def slug(texto):
    t = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii').lower()
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    if not t:
        raise CartaoRecusado(f'nome vazio depois de normalizar: {texto!r}')
    return t


def _agora():
    return datetime.datetime.now().isoformat(timespec='seconds')


def normalizar_ficha(f):
    """Os mesmos padrões do Vegapunk: os dois leem o mesmo catálogo e geram o mesmo CATALOGO.md."""
    f.setdefault('solucao', 'Vegapunk')
    f.setdefault('instancia', 'egghead')
    f.setdefault('versao', 1)
    f.setdefault('status', 'rascunho')
    f.setdefault('relacionados', [])
    f.setdefault('colunas', [])
    f.setdefault('historico', [{'versao': 1, 'data': f.get('criado_em', ''), 'motivo': 'Primeira versão'}])
    return f


def pasta_do_save(pasta, ref):
    return os.path.join(pasta, SAVES, *ref.strip('/').split('/'))


def ler_ficha(pasta, ref):
    texto = _ler(os.path.join(pasta_do_save(pasta, ref), 'ficha.json'))
    if texto is None:
        raise CartaoRecusado(f'save não encontrado: {ref}')
    return normalizar_ficha(json.loads(texto))


def gravar_ficha(pasta, ref, ficha):
    f = {k: v for k, v in ficha.items() if k != 'ref'}
    _gravar(os.path.join(pasta_do_save(pasta, ref), 'ficha.json'), json.dumps(f, ensure_ascii=False, indent=2))


def ler_catalogo(pasta):
    """Fichas de todos os saves (de todas as soluções), com `ref`, na ordem do catálogo."""
    fichas = []
    raiz = os.path.join(pasta, SAVES)
    for d, _, arqs in os.walk(raiz):
        if 'ficha.json' in arqs:
            ficha = normalizar_ficha(json.loads(_ler(os.path.join(d, 'ficha.json'))))
            ficha['ref'] = os.path.relpath(d, raiz).replace(os.sep, '/')
            fichas.append(ficha)
    return sorted(fichas, key=lambda x: (x['solucao'].lower(), x['categoria'].lower(), x['secao'].lower(),
                                         x['artigo'].lower()))


def gerar_catalogo_md(fichas):
    """Igual ao do Vegapunk, linha por linha: quem enviar por último não reescreve o catálogo do outro."""
    linhas = ['# Catálogo', '', 'Gerado pelo envio. Não edite à mão.', '']
    sol = cat = sec = None
    for f in fichas:
        if linhas[-1] and (f['solucao'] != sol or f['categoria'] != cat or f['secao'] != sec):
            linhas.append('')
        if f['solucao'] != sol:
            sol, cat, sec = f['solucao'], None, None
            linhas += [f'## {sol}', '']
        if f['categoria'] != cat:
            cat, sec = f['categoria'], None
            linhas += [f'### {cat}', '']
        if f['secao'] != sec:
            sec = f['secao']
            linhas += [f'#### {sec}', '']
        desc = f' — {f["descricao"]}' if f.get('descricao') else ''
        quebrado = ' · **conferir: schema mudou**' if (f.get('conferencia') or {}).get('ok') is False else ''
        linhas.append(f'- [{f["artigo"]}]({SAVES}/{f["ref"]}/){desc} · v{f["versao"]} · {f["status"]}{quebrado}')
    por_tabela = {}
    for f in fichas:
        for t in f.get('tabelas', []):
            por_tabela.setdefault(t, []).append(f)
    if por_tabela:
        linhas += ['', '## Por tabela', '']
        for t in sorted(por_tabela):
            linhas.append(f'- `{t}`: ' + ', '.join(f'[{f["artigo"]}]({SAVES}/{f["ref"]}/)' for f in por_tabela[t]))
    if len(linhas) > 4:
        linhas.append('')
    return '\n'.join(linhas) + '\n'


def corpo_do_readme(texto):
    if not texto or CORPO_INI not in texto:
        return None
    return texto.split(CORPO_INI, 1)[1].split(CORPO_FIM, 1)[0].strip('\n')


def _link(de_ref, para_ref):
    return '../' * len(de_ref.split('/')) + para_ref + '/'


# ------------------------------------------------------------------ o artigo

def _numeros(c):
    from .analise import analisar
    from .util import formatar_minutos
    r = analisar(c)
    t = r['tempos']
    p = t.get('percentis') or {}
    carga = r.get('carga') or {}
    n = {
        'atividades': len([e for e in c.elementos.values() if e['tipo'] in ('atividade', 'subprocesso')]),
        'decisoes': len([e for e in c.elementos.values() if e['tipo'] == 'decisao']),
        'raias': len(c.papeis),
        'lead_time': formatar_minutos(t['lead_time']) if t.get('lead_time') else '',
        'p80': formatar_minutos(p['p80']) if p.get('p80') else '',
        'eficiencia': f'{t["eficiencia"] * 100:.0f}%' if t.get('eficiencia') else '',
        'passagens': len(r.get('passagens_caminho') or []),
        'pessoas': carga.get('pessoas'),
    }
    return n, [o['texto'] for o in r.get('oportunidades', [])[:3]]


def corpo_automatico(c, numeros, oportunidades):
    """O texto do artigo, montado da carta: o que é, quem participa, números e oportunidades."""
    p = c.processo
    esc = p.get('escopo') or {}
    l = ['## O que é', '']
    if p.get('objetivo'):
        l += [str(p['objetivo']), '']
    pares = [('Dono do processo', p.get('dono')), ('Área', p.get('area')), ('Gatilho', p.get('gatilho')),
             ('Resultado', p.get('resultado')), ('Começa em', esc.get('inicio')), ('Termina em', esc.get('fim')),
             ('Volume', p.get('volume')), ('Prazo informado', p.get('prazo_informado'))]
    l += [f'- **{k}:** {v}' for k, v in pares if v]
    l += ['', '## Quem participa', '', ', '.join(str(x.get('nome') or k) for k, x in c.papeis.items()) + '.', '']
    l += ['## Números', '', '| O quê | Valor |', '|---|---|',
          f'| Atividades / decisões / raias | {numeros["atividades"]} / {numeros["decisoes"]} / {numeros["raias"]} |']
    for rot, k in (('Lead time típico', 'lead_time'), ('80% dos casos até', 'p80'),
                   ('Eficiência do ciclo', 'eficiencia'), ('Passagens de bastão no caso típico', 'passagens')):
        if numeros.get(k) not in ('', None):
            l.append(f'| {rot} | {numeros[k]} |')
    if numeros.get('pessoas'):
        l.append(f'| Carga (pessoas em jornada cheia) | {str(round(numeros["pessoas"], 1)).replace(".", ",")} |')
    l += ['', 'Os tempos são estimativas da entrevista, não medição.']
    if oportunidades:
        l += ['', '## Maiores oportunidades', ''] + [f'{i}. {o}' for i, o in enumerate(oportunidades, 1)]
    return '\n'.join(l)


def gerar_readme(ficha, ref, corpo, titulos):
    l = [f'# {ficha["artigo"]}', '',
         f'{ficha["solucao"]} › {ficha["categoria"]} › {ficha["secao"]} · versão {ficha["versao"]} · '
         f'{ficha["status"]}', '']
    if ficha.get('descricao'):
        l += [f'> {ficha["descricao"]}', '']
    l += [CORPO_INI, corpo.strip('\n'), CORPO_FIM, '']
    arq = ficha.get('arquivos') or {}
    if arq.get('svg'):
        l += ['## Fluxograma', '', f'[![Fluxograma]({arq["svg"]})]({arq["svg"]})', '']
    l += ['## Arquivos', '']
    nomes = (('md', 'Mapeamento (Markdown, abre aqui no GitHub)'), ('docx', 'Mapeamento (Word)'),
             ('html', 'Mapeamento (HTML, para imprimir em PDF)'), ('bpmn', 'Fluxograma BPMN 2.0 (Bizagi, bpmn.io, '
                                                                          'Camunda, ARIS, Signavio)'),
             ('drawio', 'Fluxograma draw.io (diagrams.net e Visio)'), ('mmd', 'Fluxograma Mermaid'),
             ('csv', 'Planilha das atividades'), ('carta', 'Carta do processo (a fonte de tudo)'))
    l += [f'- [{rot}]({arq[k]})' for k, rot in nomes if arq.get(k)]
    ac = ficha.get('aceite')
    l += ['', '## Aceite', '']
    if ac:
        l.append(f'Aprovado por **{ac["por"]}** em {ac["quando"]} (hash `{ac["hash"]}`).')
    else:
        l.append('Ainda sem aceite do dono do processo: **rascunho**.')
    if ficha['relacionados']:
        l += ['', '## Relacionados', '']
        l += [f'- [{titulos.get(r, r)}]({_link(ref, r)})' for r in ficha['relacionados']]
    l += ['', '## Histórico', '', '| Versão | Data | Motivo |', '|---|---|---|']
    l += [f'| {h["versao"]} | {h["data"][:10]} | {h["motivo"]} |' for h in reversed(ficha['historico'])]
    return '\n'.join(l) + '\n'


def _diff(antes, depois, nome):
    return ''.join(difflib.unified_diff((antes or '').splitlines(True), depois.splitlines(True),
                                        f'{nome} (no cartão)', f'{nome} (novo)'))


# ------------------------------------------------------------------ envio

def padroes(c):
    """Categoria, seção e artigo sugeridos pela carta."""
    p = c.processo
    categoria = p.get('area') or p.get('macroprocesso') or ''
    secao = p.get('macroprocesso') or p.get('area') or ''
    nome = ' · '.join(str(x) for x in (p.get('codigo'), p.get('nome')) if x) or 'Processo'
    return str(categoria), str(secao), f'{nome} ({c.cenario().upper()})'


def _gerar_arquivos(c, destino):
    """Roda o `documentar` numa pasta temporária: o save leva sempre a versão gerada agora, nunca à mão."""
    r = subprocess.run([sys.executable, os.path.join(RAIZ, 'senku.py'), 'documentar', c.caminho, '-o', destino],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise CartaoRecusado('o documentar falhou: ' + (r.stdout + r.stderr).strip()[-400:])
    return sorted(os.listdir(destino))


def montar_envio(caminho_carta, pasta, categoria=None, secao=None, artigo=None, descricao=None, texto=None,
                 motivo=None, status=None, relacionados=(), sem_aceite=False):
    from . import aprovacao, modelo, validacao
    c = modelo.carregar(os.path.join(caminho_carta, 'carta.json') if os.path.isdir(caminho_carta) else caminho_carta)
    erros = [x for x in validacao.validar(c) if x.nivel == 'erro']
    if erros:
        raise CartaoRecusado(f'a carta tem {len(erros)} erro(s) de fluxo: rode python senku.py validar {c.caminho}')
    estado, reg = aprovacao.situacao_aprovacao(c)
    if estado != 'aprovada' and not sem_aceite:
        motivo_aceite = 'mudou depois do aceite' if estado == 'mudou' else 'ainda não tem o aceite do dono'
        raise CartaoRecusado(f'a carta {motivo_aceite}. O cartão guarda o processo aprovado: rode '
                             'python senku.py aprovar <carta> --por "Nome (cargo)" e salve depois. Para guardar '
                             'mesmo assim, como rascunho: --sem-aceite')
    if status and status not in STATUS:
        raise CartaoRecusado(f'status inválido: {status} (use {" ou ".join(STATUS)})')
    cat0, sec0, art0 = padroes(c)
    categoria, secao, artigo = (categoria or cat0).strip(), (secao or sec0).strip(), (artigo or art0).strip()
    if not categoria or not secao:
        raise CartaoRecusado('a carta não tem área nem macroprocesso: diga onde guardar com --categoria e --secao')
    ref = '/'.join([PASTA_SOLUCAO] + [slug(x) for x in (categoria, secao, artigo)])
    destino = pasta_do_save(pasta, ref)
    anterior = ler_ficha(pasta, ref) if os.path.exists(os.path.join(destino, 'ficha.json')) else None
    if anterior and not (motivo or '').strip():
        raise CartaoRecusado(f'{ref} já existe (versão {anterior["versao"]}): diga o motivo da mudança com --motivo')
    catalogo = ler_catalogo(pasta)
    refs = {f['ref']: f for f in catalogo}
    for r in relacionados:
        if r == ref:
            raise CartaoRecusado('um save não se relaciona com ele mesmo')
        if r not in refs:
            raise CartaoRecusado(f'save não encontrado: {r}')
        if not r.startswith(PASTA_SOLUCAO + '/'):
            raise CartaoRecusado(f'{r} é de outra solução: o Senku só liga saves do Senku')
    # AS-IS e TO-BE do mesmo processo ficam ligados sozinhos
    codigo = str(c.processo.get('codigo') or '').strip()
    automaticos = [f['ref'] for f in catalogo if codigo and f['ref'] != ref and f['ref'].startswith(PASTA_SOLUCAO + '/')
                   and str((f.get('processo') or {}).get('codigo') or '').strip().lower() == codigo.lower()]
    if texto is not None:
        corpo = _ler(texto) if os.path.isfile(texto) else None
        if corpo is None:
            raise CartaoRecusado(f'texto do artigo não encontrado: {texto}')
    else:
        corpo = None
    numeros, oport = _numeros(c)
    if corpo is None:
        corpo = corpo_automatico(c, numeros, oport)
    tmp = tempfile.mkdtemp(prefix='senku-cartao-')
    gerados = _gerar_arquivos(c, tmp)
    shutil.copyfile(c.caminho, os.path.join(tmp, 'carta.json'))
    arq_aceite = aprovacao.arquivo_aprovacao(c.caminho)
    if os.path.exists(arq_aceite):
        shutil.copyfile(arq_aceite, os.path.join(tmp, 'carta.aprovacao.json'))
    arquivos = {'carta': 'carta.json'}
    for nome in gerados:
        for k, fim in (('csv', '-atividades.csv'), ('svg', '.svg'), ('bpmn', '.bpmn'), ('drawio', '.drawio'),
                       ('mmd', '.mmd'), ('md', '.md'), ('docx', '.docx'), ('html', '.html')):
            if nome.endswith(fim) and k not in arquivos:
                arquivos[k] = nome
                break
    agora = _agora()
    versao = anterior['versao'] + 1 if anterior else 1
    p = c.processo
    ficha = {
        'solucao': SOLUCAO, 'instancia': INSTANCIA,
        'categoria': categoria, 'secao': secao, 'artigo': artigo,
        'descricao': (descricao if descricao is not None else
                      (anterior or {}).get('descricao') or str(p.get('objetivo') or '')).strip(),
        'status': status or ('em-uso' if estado == 'aprovada' else 'rascunho'),
        'versao': versao,
        'processo': dict({k: str(p.get(k) or '') for k in ('codigo', 'nome', 'dono', 'area', 'macroprocesso')},
                         cenario=c.cenario()),
        'aceite': ({'por': reg.get('por'), 'quando': reg.get('quando'), 'hash': str(reg.get('hash') or '')[:12]}
                   if estado == 'aprovada' else None),
        'numeros': numeros,
        'arquivos': arquivos,
        'relacionados': sorted(set((anterior or {}).get('relacionados', [])) | set(relacionados) | set(automaticos)),
        'criado_em': anterior['criado_em'] if anterior else agora, 'atualizado_em': agora,
        'historico': (anterior or {}).get('historico', []) + [
            {'versao': versao, 'data': agora, 'motivo': (motivo or 'Primeira versão').strip()}],
    }
    titulos = {f['ref']: f['artigo'] for f in catalogo}
    readme = gerar_readme(ficha, ref, corpo, titulos)
    carta_nova = _ler(c.caminho)
    avisos = []
    if estado != 'aprovada':
        avisos.append('sem aceite válido do dono: vai como rascunho')
    return {'ref': ref, 'destino': destino, 'ficha': ficha, 'readme': readme, 'tmp': tmp,
            'substitui': anterior is not None, 'avisos': avisos,
            'diff_carta': _diff(_ler(os.path.join(destino, 'carta.json')), carta_nova, 'carta.json') if anterior else '',
            'diff_readme': _diff(_ler(os.path.join(destino, 'README.md')), readme, 'README.md') if anterior else '',
            'novos_relacionados': [r for r in ficha['relacionados'] if r not in (anterior or {}).get('relacionados', [])]}


def descartar(envio):
    shutil.rmtree(envio['tmp'], ignore_errors=True)


def gravar_envio(envio, pasta):
    d = envio['destino']
    if os.path.isdir(d):
        shutil.rmtree(d)                          # o save é a versão de agora: arquivo que sumiu sai junto
    shutil.copytree(envio['tmp'], d)
    descartar(envio)
    gravar_ficha(pasta, envio['ref'], envio['ficha'])
    _gravar(os.path.join(d, 'README.md'), envio['readme'])
    titulos = {f['ref']: f['artigo'] for f in ler_catalogo(pasta)}
    for r in envio['ficha']['relacionados']:       # a ligação vale nos dois sentidos
        outra = ler_ficha(pasta, r)
        if envio['ref'] not in outra['relacionados']:
            outra['relacionados'] = sorted(outra['relacionados'] + [envio['ref']])
            gravar_ficha(pasta, r, outra)
            _regravar_readme(pasta, r, outra, titulos)
    fi = envio['ficha']
    publicar(pasta, f'save: {fi["solucao"]} / {fi["categoria"]} / {fi["secao"]} / {fi["artigo"]} '
                    f'(v{fi["versao"]}): {fi["historico"][-1]["motivo"]}')


def _regravar_readme(pasta, ref, ficha, titulos=None):
    d = pasta_do_save(pasta, ref)
    corpo = corpo_do_readme(_ler(os.path.join(d, 'README.md'))) or ''
    titulos = titulos or {f['ref']: f['artigo'] for f in ler_catalogo(pasta)}
    _gravar(os.path.join(d, 'README.md'), gerar_readme(ficha, ref, corpo, titulos))


def marcar(pasta, ref, status):
    if status not in STATUS:
        raise CartaoRecusado(f'status inválido: {status} (use {" ou ".join(STATUS)})')
    if not ref.startswith(PASTA_SOLUCAO + '/'):
        raise CartaoRecusado(f'{ref} é de outra solução: o Senku só marca saves do Senku')
    ficha = ler_ficha(pasta, ref)
    ficha['status'] = status
    gravar_ficha(pasta, ref, ficha)
    _regravar_readme(pasta, ref, ficha)
    publicar(pasta, f'save: {ficha["solucao"]} / {ficha["categoria"]} / {ficha["secao"]} / {ficha["artigo"]}: '
                    f'status {status}')


# ------------------------------------------------------------------ busca

_PARADAS = set('a o as os de da do das dos e em no na nos nas um uma para por com sem que ao aos the of and '
               'processo processos mapear mapeamento fluxo'.split())


def _tokens(texto):
    t = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode('ascii').lower()
    out = set()
    for w in re.findall(r'[a-z0-9]+', t):
        if w in _PARADAS or len(w) < 2:
            continue
        for fim in ('oes', 'aes', 'ais', 'eis', 'es', 's'):
            if len(w) > 4 and w.endswith(fim):
                w = w[:-len(fim)]
                break
        out.add(w)
    return out


def buscar(pasta, termos, limite=10, cobertura_minima=0.5):
    """[(pontos, ficha)] em todos os saves do cartão: artigo e descrição valem 3, solução, categoria, seção e
    processo 2, o texto do artigo (e, num save do Senku, os nomes das atividades e dos papéis) 1. Só entra
    o save que cobre pelo menos metade dos termos."""
    alvo = sorted(_tokens(' '.join(termos)))
    if not alvo:
        return []
    achados = []
    for f in ler_catalogo(pasta):
        d = pasta_do_save(pasta, f['ref'])
        proc = f.get('processo') or {}
        extra = ''
        carta = _ler(os.path.join(d, 'carta.json'))
        if carta:
            try:
                dados = json.loads(carta)
                extra = ' '.join(str(e.get('nome') or '') for e in dados.get('elementos', []) if isinstance(e, dict))
                extra += ' ' + ' '.join(str(x.get('nome') or '') for x in dados.get('papeis', []) if isinstance(x, dict))
            except (ValueError, AttributeError):
                pass
        campos = [(3, _tokens(f'{f["artigo"]} {f.get("descricao", "")}')),
                  (2, _tokens(f'{f["solucao"]} {f["categoria"]} {f["secao"]} {proc.get("nome", "")} '
                              f'{proc.get("codigo", "")}')),
                  (1, _tokens(f'{corpo_do_readme(_ler(os.path.join(d, "README.md"))) or ""} {extra}'))]
        pontos = cobertos = 0
        for t in alvo:
            p = sum(peso for peso, toks in campos if t in toks)
            pontos += p
            cobertos += bool(p)
        if pontos and cobertos / len(alvo) >= cobertura_minima:
            achados.append((pontos, f))
    return sorted(achados, key=lambda x: (-x[0], x[1]['ref']))[:limite]


# ------------------------------------------------------------------ situação de uma carta no cartão

def situacao_da_carta(c):
    """None (sem cartão aqui), 'ausente', 'salvo' (o aceite atual está no cartão) ou 'desatualizado'.
    Só a cópia local, sem rede."""
    ok, _ = disponivel()
    if not ok:
        return None
    from . import aprovacao
    estado, reg = aprovacao.situacao_aprovacao(c)
    codigo = str(c.processo.get('codigo') or '').strip().lower()
    nome = str(c.processo.get('nome') or '').strip().lower()
    for f in ler_catalogo(config()['pasta']):
        p = f.get('processo') or {}
        if f.get('solucao') != SOLUCAO or p.get('cenario') != c.cenario():
            continue
        if (codigo and str(p.get('codigo', '')).lower() == codigo) or (not codigo and p.get('nome', '').lower() == nome):
            hash_salvo = (f.get('aceite') or {}).get('hash')
            atual = str((reg or {}).get('hash') or '')[:12] if estado == 'aprovada' else None
            return 'salvo' if hash_salvo and hash_salvo == atual else 'desatualizado'
    return 'ausente'


def lembrete(texto):
    print(f'LEMBRETE: {texto}', file=sys.stderr)
