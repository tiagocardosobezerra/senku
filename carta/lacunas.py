"""
Lacunas: o que ainda falta perguntar, em linguagem de negócio, por prioridade.

    1  o fluxo         sem a resposta, o desenho fica errado (beco sem saída, decisão sem o outro caminho)
    2  as atividades   critério e percentual das decisões, sistema, tempo: muda o mapa e a análise
    3  o processo      identificação e escopo: objetivo, dono, gatilho, onde começa e termina, SIPOC
    4  a gestão        indicadores, dores, riscos e controles, valor agregado
    5  o detalhe       como cada atividade é feita e o que produz (vai para o documento)

A entrevista anda melhor em blocos curtos: o comando devolve poucas perguntas
por vez (padrão 7), as mais importantes primeiro. Cada pergunta diz onde a
resposta entra na carta ("onde"), para quem conduz atualizar o carta.json.
"""

from .analise import decisao_sem_criterio, percentual_do_laco
from .modelo import ESCOLHA, NOS_DE_TRABALHO
from .util import como_lista

BLOCOS = {1: 'fluxo', 2: 'decisões e atividades', 3: 'processo', 4: 'gestão', 5: 'detalhe'}


class Pergunta:
    __slots__ = ('prioridade', 'elemento', 'texto', 'onde', 'porque')

    def __init__(self, prioridade, elemento, texto, onde, porque=''):
        self.prioridade, self.elemento, self.texto, self.onde, self.porque = prioridade, elemento, texto, onde, porque

    def como_dict(self):
        d = {k: getattr(self, k) for k in self.__slots__}
        d['bloco'] = BLOCOS[self.prioridade]
        return d


def _externo(c, pid):
    return (c.papeis.get(pid) or {}).get('tipo') == 'externo'


def _laco_coberto(c, f):
    """O retrabalho começa numa saída de decisão que já tem a pergunta de percentual: não pergunta de novo."""
    x, vistos = f['de'], set()
    while x in c.elementos and x not in vistos:
        vistos.add(x)
        e = c.elementos[x]
        if e['tipo'] in ESCOLHA or e['tipo'] == 'borda':       # a borda tem a pergunta de percentual dela
            return True
        ent = c.entradas[x]
        if len(ent) != 1:
            return False
        x = ent[0]['de']
    return False


def _respondido(e, chave):
    """A pessoa respondeu, mesmo que a resposta seja "nenhum": a chave existe no elemento original."""
    return chave in e['bruto']


def levantar(c):
    out = []

    def q(prio, eid, texto, onde, porque=''):
        out.append(Pergunta(prio, eid, texto, onde, porque))

    p = c.processo
    # ---------------------------------------------------------------- 1. o fluxo
    if not c.de_tipo('inicio'):
        q(1, None, 'O que dispara o processo? (um pedido que chega, uma data, um evento: "Pedido recebido")',
          'elementos: {"tipo": "inicio", "nome": ...}', 'sem início o fluxo não tem por onde começar')
    if not c.de_tipo('fim'):
        q(1, None, 'Como o processo termina? Quais são os resultados possíveis (ex.: "Pedido entregue", '
          '"Pedido cancelado")?', 'elementos: {"tipo": "fim", "nome": ...}', 'cada final vira um fim com nome')
    for e in c.elementos.values():
        eid = e['id']
        saidas = [f for f in c.saidas[eid] if not f['borda']]       # a borda é exceção, não divisão
        if e['tipo'] != 'fim' and not saidas:
            q(1, eid, f'Depois de "{c.nome(eid)}", o que acontece? Quem faz o próximo passo?',
              f'elementos[{eid}].segue', 'o caminho para aqui (beco sem saída)')
        if e['tipo'] == 'decisao':
            if len(saidas) == 1 and len(c.entradas[eid]) < 2:
                r = saidas[0]['rotulo'] or 'um caminho'
                q(1, eid, f'Em "{c.nome(eid)}", o caminho de "{r}" está desenhado. E quando a resposta é outra, o '
                  'que acontece?', f'elementos[{eid}].segue', 'decisão com um caminho só')
            for f in (saidas if len(saidas) > 1 else []):
                if not f['rotulo']:
                    q(1, eid, f'Em "{c.nome(eid)}", qual resposta leva a "{c.destino_legivel(f["para"])}"?',
                      f'elementos[{eid}].segue[].rotulo', 'saída de decisão sem rótulo')
        if e['tipo'] in NOS_DE_TRABALHO and not e['papel']:
            q(1, eid, f'Quem faz "{c.nome(eid)}"? (cargo ou área, não o nome da pessoa)',
              f'elementos[{eid}].papel', 'sem responsável a atividade cai na raia "sem responsável"')
        if e['tipo'] in NOS_DE_TRABALHO and len(saidas) > 1:
            q(1, eid, f'Depois de "{c.nome(eid)}" o fluxo vai para {len(saidas)} lugares: é um OU outro '
              '(decisão) ou todos ao mesmo tempo (paralelo)?', f'elementos[{eid}].segue', 'divisão sem porta')
    for d in c.de_tipo('decisao'):
        if decisao_sem_criterio(c, d) and not _externo(c, d['papel']):
            q(2, d['id'], f'Qual é o critério de "{c.nome(d["id"])}"? (valor, prazo, documento, alçada...)',
              f'regras + elementos[{d["id"]}].regras', 'a regra de decisão é o que mais se perde do mapa')

    # ---------------------------------------------------------------- 2. o processo
    campos = [
        ('objetivo', 'Para que serve o processo? Que resultado ele entrega e para quem?'),
        ('dono', 'Quem é o dono do processo (o cargo que responde pelo resultado e aprova o mapa)?'),
    ]
    # gatilho e resultado: o início e o fim com nome já respondem; só pergunta o que o desenho não diz
    if not any(e['nome'] for e in c.de_tipo('inicio')):
        campos.append(('gatilho', 'O que dispara o processo, e com que frequência?'))
    if not any(e['nome'] for e in c.de_tipo('fim')):
        campos.append(('resultado', 'Qual é a saída final quando tudo dá certo?'))
    for chave, texto in campos:
        if not str(p.get(chave) or '').strip():
            q(3, None, texto, f'processo.{chave}')
    escopo = p.get('escopo') or {}
    if not escopo.get('inicio') or not escopo.get('fim'):
        q(3, None, 'Onde o processo começa e onde termina? (o primeiro e o último passo que fazem parte dele)',
          'processo.escopo.inicio / processo.escopo.fim', 'escopo evita mapear o processo vizinho')
    if not escopo.get('nao_inclui'):
        q(3, None, 'O que fica de fora deste mapa? (processos vizinhos, exceções tratadas em outro lugar)',
          'processo.escopo.nao_inclui')
    if not str(p.get('volume') or p.get('frequencia') or '').strip():
        q(3, None, 'Quantas vezes o processo roda (por dia, semana ou mês)?', 'processo.volume',
          'com o volume, a análise calcula a carga de trabalho por papel (pessoas necessárias)')
    elif str(p.get('volume') or '').strip():
        from .analise import casos_por_mes
        if casos_por_mes(p.get('volume')) is None:
            q(3, None, f'O volume "{p.get("volume")}" não diz quantos casos por período: quantos casos por dia, '
              'semana ou mês? (ex.: "120 requisições por mês")', 'processo.volume',
              'sem número e período, a carga de trabalho por papel não é calculada')
    s = c.sipoc
    if not como_lista(s.get('clientes')):
        q(3, None, 'Quem recebe o resultado do processo (cliente interno ou externo)?', 'sipoc.clientes')
    if not como_lista(s.get('fornecedores')) or not como_lista(s.get('entradas')):
        q(3, None, 'O que o processo recebe para começar (documentos, dados, materiais) e de quem?',
          'sipoc.fornecedores / sipoc.entradas')

    # ---------------------------------------------------------------- 3. as atividades
    atividades = c.atividades()
    for e in atividades:
        eid, nome = e['id'], c.nome(e['id'])
        if not e['sistema_respondido'] and not _externo(c, e['papel']):
            q(2, eid, f'"{nome}" é feita em algum sistema, planilha ou e-mail? Qual? (ou "manual")',
              f'elementos[{eid}].sistema  (use [] se for manual)')
        if e['execucao'] is None:
            q(2, eid, f'Quanto tempo leva "{nome}" quando a pessoa está fazendo? E quanto tempo o trabalho espera '
              'antes de ela começar?', f'elementos[{eid}].tempo.execucao / .espera', 'tempo de ciclo e gargalo')
        if not e['saidas'] and not e['descricao']:
            q(5, eid, f'Como é feita "{nome}" e o que ela produz (documento, registro, aprovação)?',
              f'elementos[{eid}].descricao / .saidas')
    for e in c.de_tipo('evento'):
        if e['gatilho'] == 'tempo' and e['espera'] is None:
            q(2, e['id'], f'Quanto tempo dura a espera "{c.nome(e["id"])}"? (dias úteis ou corridos?)',
              f'elementos[{e["id"]}].tempo.espera', 'sem isso, o prazo do processo sai menor do que é')
        elif e['gatilho'] in ('mensagem', 'condicao', 'sinal') and not e['bruto'].get('envia') and e['espera'] is None:
            q(2, e['id'], f'Quanto tempo costuma levar até "{c.nome(e["id"])}"? (o normal, e o pior caso)',
              f'elementos[{e["id"]}].tempo.espera', 'sem isso, a espera pela resposta conta zero no prazo')
    volta = c.arestas_de_volta()
    for d in c.de_tipo(*ESCOLHA):
        saidas = c.saidas[d['id']]
        if len(saidas) > 1 and all(f['percentual'] is None for f in saidas):
            q(2, d['id'], f'Em "{c.nome(d["id"])}", de cada 100 casos, quantos vão por cada caminho '
              f'({", ".join(f["rotulo"] or c.destino_legivel(f["para"]) for f in saidas)})?',
              f'elementos[{d["id"]}].segue[].percentual', 'define o caminho feliz e o tamanho da exceção')
    for b in c.de_tipo('borda'):
        f = next((x for x in c.entradas[b['id']] if x['borda']), None)
        if f and f['percentual'] is None:
            q(2, b['id'], f'Em "{c.nome(b["anexo"])}", de cada 100 casos, em quantos acontece "{c.nome(b["id"])}"?',
              f'elementos[{b["anexo"]}].bordas[].percentual', 'sem isso a exceção não pesa no prazo esperado')
    if not str(c.processo.get('prazo_informado') or '').strip():
        q(2, None, 'Do começo ao fim, quanto tempo o processo leva hoje, na percepção de vocês? Qual é o prazo '
          'combinado?', 'processo.prazo_informado', 'compara com a soma dos tempos das atividades')
    for f in c.fluxos:
        if f['id'] in volta and percentual_do_laco(c, f) is None and not _laco_coberto(c, f):
            de = c.elementos.get(f['de'])
            rot = f' ("{f["rotulo"]}")' if f['rotulo'] else ''
            q(2, f['de'], f'De "{c.nome(f["de"])}"{rot} o trabalho volta para "{c.destino_legivel(f["para"])}". De cada 100 '
              'casos, quantos voltam?', f'elementos[{f["de"]}].segue[].percentual',
              'retrabalho é a primeira oportunidade de melhoria' if de else '')

    # ---------------------------------------------------------------- 4. a gestão
    if not c.indicadores:
        q(4, None, 'Como vocês sabem se o processo vai bem? Que número acompanham (prazo, volume, erro, custo)? '
          'Tem meta?', 'indicadores[]: nome, formula, meta, periodicidade, fonte')
    if not c.dores:
        q(4, None, 'O que mais atrasa, dá retrabalho ou irrita quem participa do processo?',
          'dores[]: descricao, elementos, impacto')
    if c.cenario() == 'as-is' and not c.riscos:
        q(4, None, 'O que pode dar errado de grave (multa, perda, fraude, cliente sem atendimento)? Que '
          'conferência existe hoje para evitar?', 'riscos[]: descricao, elementos, controle')
    sem_a = [e for e in atividades if not e['raci']['A']]
    if atividades and len(sem_a) * 2 > len(atividades):
        q(4, None, f'{len(sem_a)} de {len(atividades)} atividades não dizem quem responde pelo resultado (A). '
          'Quando é quem executa, marque A = o próprio papel; quem precisa ser consultado antes (C) ou avisado '
          'depois (I)?', 'elementos[].raci: {"A": papel, "C": [...], "I": [...]}', 'matriz RACI')
    sem_valor = [e for e in atividades if not e['valor']]
    if atividades and len(sem_valor) == len(atividades):
        q(4, None, 'Vamos classificar cada atividade: agrega valor ao cliente (VA), é necessária mas não agrega '
          '(NAV-N: controle, lei) ou é desperdício (NAV)? Eu proponho e você corrige.',
          'elementos[].valor', 'base da análise de valor')
    out.sort(key=lambda x: x.prioridade)
    return out


def imprimir(c, perguntas, maximo=7):
    if not perguntas:
        print(f'✓ {c.titulo()}: nada essencial faltando. Próximo: python senku.py desenhar <carta> e '
              'python senku.py documentar <carta>.')
        return
    mostradas = perguntas[:maximo] if maximo else perguntas
    print(f'{c.titulo()}: {len(perguntas)} lacuna(s). As {len(mostradas)} mais importantes:')
    bloco = None
    for i, x in enumerate(mostradas, 1):
        if x.prioridade != bloco:
            bloco = x.prioridade
            print(f'\n[{bloco}. {BLOCOS[bloco]}]')
        print(f'  {i}. {x.texto}')
        print(f'     → {x.onde}' + (f'  ({x.porque})' if x.porque else ''))
    if len(perguntas) > len(mostradas):
        print(f'\n(+{len(perguntas) - len(mostradas)} depois destas; --todas mostra tudo)')
    print('\nPergunte em bloco curto, com as palavras da pessoa; grave as respostas no carta.json e rode de novo.')
