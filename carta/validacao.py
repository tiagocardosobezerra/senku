"""
Validação da carta em três níveis:

    erro   o fluxo está quebrado ou cita o que não existe: o desenho sai errado (bloqueia o aceite)
    aviso  o fluxo funciona, mas fere uma regra de boa modelagem; cada aviso diz a regra e a fonte
    dica   melhora a leitura, sem mudar o processo

Fontes das regras de estilo (referencias/estilo.md):
    7PMG   Mendling, Reijers e van der Aalst, "Seven Process Modeling Guidelines" (2010)
    M&S    Bruce Silver, "BPMN Method and Style" (regras de estilo)
    Casa   regras do Senku, do jeito que o time lê o mapa
"""

import os
import re

from .modelo import ESCOLHA, NOS_DE_TRABALHO, PORTAS
from .util import sem_acento


class Achado:
    __slots__ = ('nivel', 'codigo', 'elemento', 'texto', 'fonte')

    def __init__(self, nivel, codigo, elemento, texto, fonte='Casa'):
        self.nivel, self.codigo, self.elemento, self.texto, self.fonte = nivel, codigo, elemento, texto, fonte

    def como_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}

    def __repr__(self):
        return f'<{self.nivel} {self.codigo} {self.elemento}: {self.texto}>'


# ------------------------------------------------------------------ o nome da atividade
_INFINITIVO = re.compile(r'^[a-z]+(ar|er|ir|por)$')
# palavras em -ar/-er/-ir que no começo de um nome de atividade quase nunca são verbo (substantivo/adjetivo);
# verbos que também são adjetivos ("popular a planilha", "regular o estoque", "colar") ficam de fora da lista
_NAO_VERBOS = {'lugar', 'par', 'mar', 'bar', 'colher', 'mulher', 'talher', 'poder', 'dever', 'prazer', 'elixir',
               'ar', 'lar', 'altar', 'militar', 'familiar', 'particular', 'similar', 'celular', 'auxiliar',
               'escolar', 'singular', 'polar', 'solar', 'exemplar', 'patamar', 'radar', 'jantar', 'almocar', 'sir',
               'zir', 'emir', 'ser', 'titular', 'modular', 'mensageiro', 'fornecedor', 'valor', 'setor', 'gestor',
               'diretor', 'vencedor', 'cliente', 'mestre', 'interior', 'exterior', 'anterior', 'posterior', 'maior',
               'menor', 'melhor', 'pior', 'superior', 'inferior'}
_ARTIGOS = {'o', 'a', 'os', 'as', 'um', 'uma'}
_PREFIXOS = {'pre', 're', 'pos', 'auto', 'co', 'sub', 'super', 'inter', 'contra', 'semi', 'des', 'multi'}


def primeira_palavra(nome):
    """A primeira palavra do nome, sem artigo; "Pré-aprovar" e "Re-enviar" contam como o verbo depois do
    prefixo."""
    palavras = [p for p in re.split(r'[^a-z\-]+', sem_acento(nome).lower()) if p.strip('-')]
    while palavras and palavras[0] in _ARTIGOS:
        palavras.pop(0)
    if not palavras:
        return ''
    p = palavras[0].strip('-')
    if '-' in p:
        partes = p.split('-')
        if partes[0] in _PREFIXOS:
            return partes[-1]
        return partes[0]
    return p


def parece_verbo(palavra):
    palavra = sem_acento(palavra).lower()
    if palavra in ('por', 'ver', 'ler', 'ir', 'vir', 'dar', 'ter', 'rir'):
        return True
    return bool(_INFINITIVO.match(palavra)) and palavra not in _NAO_VERBOS


# substantivo de processo -> verbo (os comuns, conferidos à mão); fora daqui, só a regra segura "-ação" -> "-ar"
_VERBO_DE = {
    'analise': 'Analisar', 'aprovacao': 'Aprovar', 'pagamento': 'Pagar', 'lancamento': 'Lançar',
    'recebimento': 'Receber', 'conferencia': 'Conferir', 'emissao': 'Emitir', 'revisao': 'Revisar',
    'inclusao': 'Incluir', 'exclusao': 'Excluir', 'cadastro': 'Cadastrar', 'registro': 'Registrar',
    'envio': 'Enviar', 'controle': 'Controlar', 'entrega': 'Entregar', 'compra': 'Comprar', 'venda': 'Vender',
    'abertura': 'Abrir', 'manutencao': 'Manter', 'inscricao': 'Inscrever', 'descricao': 'Descrever',
    'admissao': 'Admitir', 'demissao': 'Demitir', 'contratacao': 'Contratar', 'conciliacao': 'Conciliar',
    'apuracao': 'Apurar', 'validacao': 'Validar', 'verificacao': 'Verificar', 'solicitacao': 'Solicitar',
    'elaboracao': 'Elaborar', 'definicao': 'Definir', 'execucao': 'Executar', 'atualizacao': 'Atualizar',
    'confirmacao': 'Confirmar', 'assinatura': 'Assinar', 'leitura': 'Ler', 'escolha': 'Escolher',
    'cobranca': 'Cobrar', 'baixa': 'Baixar', 'impressao': 'Imprimir', 'separacao': 'Separar',
    'expedicao': 'Expedir', 'distribuicao': 'Distribuir', 'devolucao': 'Devolver', 'avaliacao': 'Avaliar',
    'triagem': 'Triar', 'digitacao': 'Digitar', 'cotacao': 'Cotar', 'preenchimento': 'Preencher',
    'acompanhamento': 'Acompanhar', 'encaminhamento': 'Encaminhar', 'fechamento': 'Fechar',
    'levantamento': 'Levantar', 'planejamento': 'Planejar', 'atendimento': 'Atender', 'faturamento': 'Faturar',
    'agendamento': 'Agendar', 'arquivamento': 'Arquivar', 'tratamento': 'Tratar', 'treinamento': 'Treinar',
    'calculo': 'Calcular', 'consulta': 'Consultar', 'checagem': 'Checar', 'notificacao': 'Notificar',
}


def sugestao_de_verbo(nome):
    """'Aprovação da requisição' -> 'Aprovar ...' quando der com segurança (o objeto quem escolhe é a pessoa:
    em "Aprovação do gestor", o gestor é quem aprova, não o que é aprovado)."""
    p = primeira_palavra(nome)
    verbo = _VERBO_DE.get(p)
    if not verbo and p.endswith('acao') and len(p) > 6:
        verbo = p[:-4].capitalize() + 'ar'
    return f'{verbo} ...' if verbo else None


def _duas_atividades(nome):
    """'Conferir e aprovar nota' -> True: dois verbos ligados por 'e' costumam ser duas atividades."""
    partes = re.split(r'\s+e\s+|\s*/\s*|,\s*', sem_acento(nome).lower())
    verbos = [p for p in partes if p and parece_verbo(p.split()[0])]
    return len(verbos) >= 2


# ------------------------------------------------------------------ validação
def tempos_do_detalhe(c, e):
    """(esforço, lead time esperado) da carta filha de um subprocesso, em minutos úteis; None se não dá."""
    from .analise import analisar
    from .modelo import carregar
    arq = os.path.join(os.path.dirname(os.path.abspath(c.caminho)), str(e['bruto'].get('detalhe')))
    if os.path.isdir(arq):
        arq = os.path.join(arq, 'carta.json')
    arq = os.path.abspath(arq)
    if arq in _DETALHE_EM_CURSO or arq == os.path.abspath(c.caminho) or not os.path.exists(arq):
        return None                                     # detalhe que aponta para si (ou ciclo A -> B -> A)
    chave = (arq, os.path.getmtime(arq))               # a carta filha mudou: conta de novo
    if chave in _DETALHE_CACHE:
        return _DETALHE_CACHE[chave]
    _DETALHE_EM_CURSO.add(arq)
    try:
        t = analisar(carregar(arq))['tempos']
        r = (t['execucao'], t['lead_time_esperado'])
    except Exception:                                   # carta filha quebrada: o validar dela é que diz
        r = None
    finally:
        _DETALHE_EM_CURSO.discard(arq)
    _DETALHE_CACHE[chave] = r
    return r


_DETALHE_EM_CURSO = set()
_DETALHE_CACHE = {}


def _conferir_detalhe(c, e, add):
    """O tempo do subprocesso no mapa de cima tem de bater com o da carta dele (o nível de baixo manda)."""
    from .util import formatar_minutos
    r = tempos_do_detalhe(c, e)
    if not r:
        return
    ex_filho, lead_filho = r
    ex_pai = e['execucao']
    lead_pai = (e['execucao'] or 0) + (e['espera'] or 0) if (e['execucao'] is not None or e['espera'] is not None)         else None

    def longe(a, b):
        return a is not None and b is not None and abs(a - b) > max(15, 0.3 * max(a, b))
    if ex_pai is None and lead_pai is None and (ex_filho or lead_filho):
        add('dica', 'detalhe_sem_tempo', e['id'], f'"{c.nome(e["id"])}" não tem tempo; a carta do detalhe diz '
            f'esforço {formatar_minutos(ex_filho)} e lead time esperado {formatar_minutos(lead_filho)}: use esses')
    elif longe(ex_pai, ex_filho) or longe(lead_pai, lead_filho):
        add('aviso', 'detalhe_tempo_diferente', e['id'], f'"{c.nome(e["id"])}" diz esforço '
            f'{formatar_minutos(ex_pai)} e total {formatar_minutos(lead_pai)}, mas a carta do detalhe dá esforço '
            f'{formatar_minutos(ex_filho)} e lead time esperado {formatar_minutos(lead_filho)}: o nível de baixo '
            'manda; acerte o tempo aqui (ou o detalhe está desatualizado)')


def _lembrete_que_volta(c, add):
    """Borda que não interrompe cujo caminho volta ao fluxo principal numa atividade: a atividade roda de novo
    em paralelo com o caso (duas vezes), quase sempre sem querer."""
    for b in c.de_tipo('borda'):
        if b['interrompe']:
            continue
        alcance, pilha = set(), [f['para'] for f in c.saidas[b['id']]]
        while pilha:
            x = pilha.pop()
            if x in alcance or x not in c.elementos:
                continue
            alcance.add(x)
            pilha.extend(f['para'] for f in c.saidas[x])
        for x in alcance:
            if c.elementos[x]['tipo'] not in NOS_DE_TRABALHO:
                continue
            de_fora = [f for f in c.entradas[x] if f['de'] not in alcance and f['de'] != b['id']]
            if de_fora:
                add('erro', 'lembrete_volta_ao_fluxo', b['id'], f'a borda que não interrompe "{c.nome(b["id"])}" '
                    f'leva de volta a "{c.nome(x)}", que também está no caminho normal: a atividade roda de novo '
                    'enquanto o caso continua (duas vezes). Se é para refazer, a borda interrompe; se é aviso, '
                    'termine o caminho dela num fim próprio', 'M&S')
                break


def _quis_dizer(c, alvo):
    """Sugestão para id digitado errado: "a1 " -> "a1"; "D1" -> "d1"; "a12" perto de "a1"; ou o nome."""
    import difflib
    alvo_s = str(alvo).strip()
    ids = list(c.elementos)
    for i in ids:
        if i == alvo_s or i.lower() == alvo_s.lower():
            return f' (quis dizer "{i}"?)'
    por_nome = {sem_acento(str(e['nome'] or '')).lower(): i for i, e in c.elementos.items() if e['nome']}
    if sem_acento(alvo_s).lower() in por_nome:
        return f' (quis dizer "{por_nome[sem_acento(alvo_s).lower()]}", o id de "{alvo_s}"?)'
    perto = difflib.get_close_matches(alvo_s, ids, n=1, cutoff=0.6)
    return f' (quis dizer "{perto[0]}"?)' if perto else ''


def _plausibilidade(c, add):
    """Tempos e percentuais que não podem ser verdade juntos."""
    volta = c.arestas_de_volta()
    for e in c.de_tipo('corrida'):
        alvos = [c.elementos[f['para']] for f in c.saidas[e['id']] if f['para'] in c.elementos]
        prazos = [x for x in alvos if x['gatilho'] == 'tempo' and x['espera']]
        if not prazos:
            continue
        prazo = min(x['espera'] for x in prazos)
        for x in alvos:
            if x['gatilho'] != 'tempo' and x['espera'] and x['espera'] >= prazo:
                add('aviso', 'corrida_espera_maior_que_prazo', x['id'], f'"{c.nome(x["id"])}" espera '
                    f'{x["tempo_texto"].get("espera")}, mais que o prazo da corrida '
                    f'({min(prazos, key=lambda y: y["espera"])["tempo_texto"].get("espera")}): o prazo sempre vence. '
                    'O tempo da resposta é o normal dentro do prazo?')
    for b in c.de_tipo('borda'):
        host = c.elementos.get(b['anexo'])
        if not host or b['gatilho'] != 'tempo' or not b['espera'] or not b['interrompe']:
            continue
        dur = (host['execucao'] or 0) + (host['espera'] or 0)
        pct = b.get('percentual_borda')
        if dur and b['espera'] < dur and (pct is None or pct < 50):
            add('aviso', 'prazo_menor_que_atividade', b['id'], f'o prazo "{c.nome(b["id"])}" '
                f'({b["tempo_texto"].get("espera")}) vence antes do tempo normal de "{c.nome(host["id"])}": ou a '
                'borda dispara quase sempre, ou o tempo da atividade está alto')
    for f in c.fluxos:
        if f['id'] in volta and f['percentual'] is not None and f['percentual'] >= 100:
            add('erro', 'laco_sempre', f['de'], f'de "{c.nome(f["de"])}", 100% dos casos voltam: o processo nunca '
                'termina. Qual parte segue em frente?')


def _datas(c, add):
    """Prazo do plano de ação escrito como data (dd/mm/aaaa) tem de ser uma data que existe."""
    import datetime
    for m in c.melhorias:
        prazo = str(m.get('prazo') or '')
        d = re.fullmatch(r'\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*', prazo)
        if d:
            try:
                datetime.date(int(d.group(3)), int(d.group(2)), int(d.group(1)))
            except ValueError:
                add('aviso', 'data_invalida', None, f'a melhoria "{m.get("id")}" tem prazo "{prazo}", que não é uma '
                    'data que existe')


def validar(c):
    """Achados da carta. Guarda o resultado na própria carta: o analisar e o documentar perguntam de novo."""
    cache = c.__dict__.get('_validacao_cache')
    if cache is not None:
        return list(cache)
    out = _validar(c)
    c.__dict__['_validacao_cache'] = out
    return list(out)


def _validar(c):
    out = []

    def add(nivel, codigo, elemento, texto, fonte='Casa'):
        out.append(Achado(nivel, codigo, elemento, texto, fonte))

    for codigo, eid, texto in c.problemas:
        # o caractere invisível já foi limpo na leitura: só avisa
        add('aviso' if codigo in ('caractere_invisivel', 'sem_id') else 'erro', codigo, eid, texto)
    if not (c.processo.get('nome') or '').strip():
        add('aviso', 'processo_sem_nome', None, 'o processo não tem nome ("processo.nome"): o título sai '
            '"Processo sem nome"')
    vistos_fluxo = set()
    for f in c.fluxos:
        chave = (f['de'], f['para'])
        if chave in vistos_fluxo:
            add('erro', 'fluxo_repetido', f['de'], f'"{c.nome(f["de"])}" segue duas vezes para "{c.nome(f["para"])}": '
                'tire a ligação repetida')
        vistos_fluxo.add(chave)
    _percentuais(c, add)
    _papeis_que_parecem_pessoas(c, add)
    _corridas(c, add)
    _lembrete_que_volta(c, add)
    _plausibilidade(c, add)
    _datas(c, add)
    if not c.elementos:
        add('erro', 'sem_elementos', None, 'a carta ainda não tem nenhum elemento no fluxo ("elementos")')
        return out

    inicios = c.de_tipo('inicio')
    fins = c.de_tipo('fim')
    if not inicios:
        add('erro', 'sem_inicio', None, 'o fluxo não tem evento de início: o que dispara o processo?', 'M&S')
    if not fins:
        add('erro', 'sem_fim', None, 'o fluxo não tem evento de fim: como o processo termina?', 'M&S')

    # id de destino digitado errado: os erros de ligação que vêm dele (nada chega, nunca termina) não repetem
    destino_errado = any(f['para'] not in c.elementos for f in c.fluxos)
    for f in c.fluxos:
        if f['para'] not in c.elementos:
            add('erro', 'destino_inexistente', f['de'], f'"{c.nome(f["de"])}" segue para "{f["para"]}", '
                'que não existe nos elementos' + _quis_dizer(c, f['para']) + '. Corrija este primeiro: outros '
                'erros de ligação costumam ser efeito dele')
        if f['de'] == f['para']:
            add('aviso', 'laco_em_si', f['de'], f'"{c.nome(f["de"])}" volta para si mesma; desenhe a decisão '
                'que faz repetir (ex.: "Documento completo?")', 'M&S')

    alcance = c.alcancaveis([e['id'] for e in inicios])
    chega_ao_fim = c.alcancaveis([e['id'] for e in fins], para_tras=True)

    for e in c.elementos.values():
        eid, tipo, nome = e['id'], e['tipo'], e['nome']
        n_in = len(c.entradas[eid])
        n_out = len([f for f in c.saidas[eid] if not f['borda']])      # a borda é exceção, não divisão
        if tipo == 'borda':
            host = c.elementos.get(e['anexo'])
            if not host or host['tipo'] not in NOS_DE_TRABALHO:
                add('erro', 'borda_sem_atividade', eid, f'a borda "{nome}" fica presa numa atividade ou subprocesso')
            if e['gatilho'] not in ('tempo', 'mensagem', 'erro', 'sinal', 'condicao'):
                add('erro', 'borda_gatilho', eid, f'a borda "{nome}" precisa de gatilho: tempo (prazo), mensagem, '
                    'erro, sinal ou condição')
            if e['gatilho'] == 'tempo' and e['espera'] is None:
                add('aviso', 'borda_sem_prazo', eid, f'a borda de prazo "{nome}" não diz o prazo ("tempo": "48h")')
            if not e['nome']:
                add('aviso', 'borda_sem_nome', eid, 'dê nome à borda com o que aconteceu ("Prazo de 48h estourado")',
                    'M&S')
            if len(c.saidas[eid]) > 1:
                add('aviso', 'borda_divide', eid, 'a borda' + (f' "{nome}"' if nome else '') + f' segue para {len(c.saidas[eid])} lugares de uma '
                    'vez (todos acontecem, como um paralelo escondido): se é um caminho só, deixe um "segue"; se '
                    'são vários ao mesmo tempo, ponha um paralelo depois da borda', '7PMG')

        # -------- ligação
        if tipo == 'inicio' and n_in:
            add('erro', 'inicio_com_entrada', eid, f'o início "{nome}" recebe fluxo; um início só tem saída '
                '(para voltar ao começo, aponte para a primeira atividade)', 'M&S')
        if tipo == 'borda' and n_in > 1 or (tipo == 'borda' and any(not f['borda'] for f in c.entradas[eid])):
            add('erro', 'fluxo_para_borda', eid, f'um fluxo chega na borda "{nome}": a borda só dispara durante a '
                'atividade em que está presa; aponte o fluxo para a atividade', 'M&S')
        if tipo in NOS_DE_TRABALHO and sum(1 for f in c.saidas[eid] if f['borda']) > 4:
            add('aviso', 'bordas_demais', eid, f'"{nome}" tem {sum(1 for f in c.saidas[eid] if f["borda"])} bordas: '
                'o desenho fica ilegível. Deixe as raras em "excecoes" da atividade ou faça dela um subprocesso', 'M&S')
        if tipo == 'fim' and e['gatilho'] == 'tempo':
            add('erro', 'fim_de_tempo', eid, f'o fim "{nome}" tem gatilho de tempo: fim não espera; ponha um '
                'evento de tempo antes dele', 'M&S')
        if tipo in NOS_DE_TRABALHO:
            soma = sum(c.elementos[f['para']].get('percentual_borda') or 0 for f in c.saidas[eid]
                       if f['borda'] and f['para'] in c.elementos and c.elementos[f['para']]['interrompe'])
            if soma > 100:
                add('erro', 'bordas_mais_de_100', eid, f'as bordas que interrompem "{nome}" somam {soma:.0f}% dos '
                    'casos: não sobra caso para o caminho normal')
        if tipo == 'fim' and n_out:
            add('erro', 'fim_com_saida', eid, f'o fim "{nome}" tem saída; um fim encerra o caminho', 'M&S')
        if tipo != 'fim' and n_out == 0:
            add('erro', 'beco_sem_saida', eid, f'"{c.nome(eid)}" não segue para lugar nenhum: depois dela, o que '
                'acontece? (ou ligue a um fim)', 'M&S')
        if tipo != 'inicio' and n_in == 0 and not destino_errado:
            add('erro', 'sem_entrada', eid, f'nada chega em "{c.nome(eid)}": de onde ela vem?', 'M&S')
        elif inicios and eid not in alcance and tipo != 'inicio' and not destino_errado:
            add('erro', 'inalcancavel', eid, f'"{c.nome(eid)}" não é alcançada a partir de nenhum início')
        if fins and eid not in chega_ao_fim and tipo != 'fim' and n_out and not destino_errado:
            add('erro', 'nunca_termina', eid, f'a partir de "{c.nome(eid)}" o processo nunca chega a um fim '
                '(laço sem saída)')

        # -------- referências
        if e['papel'] and e['papel'] not in c.papeis and c.papeis:
            import difflib
            perto = difflib.get_close_matches(str(e['papel']), list(c.papeis) + [str(p.get('nome') or '')
                                                                                 for p in c.papeis.values()], 1, 0.6)
            add('erro', 'papel_inexistente', eid, f'"{c.nome(eid)}" cita o papel "{e["papel"]}", que não está em '
                '"papeis"' + (f' (quis dizer "{perto[0]}"?)' if perto else ''))
        for s in e['sistema']:
            if s not in c.sistemas and c.sistemas:            # sem lista de sistemas, o nome escrito já basta
                add('erro', 'sistema_inexistente', eid, f'"{c.nome(eid)}" cita o sistema "{s}", que não está em '
                    '"sistemas"')
        for r in e['regras']:
            if r not in c.regras:
                add('erro', 'regra_inexistente', eid, f'"{c.nome(eid)}" cita a regra "{r}", que não está em "regras"')
        raci_bruto = e['bruto'].get('raci')
        if isinstance(raci_bruto, dict) and any(str(k).upper() == 'R' for k in raci_bruto):
            add('aviso', 'raci_r', eid, f'RACI de "{c.nome(eid)}" tem "R": o R é o papel da atividade (a raia); '
                'tire o R e mude o "papel" se quem executa é outro')
        if len(e['raci'].get('A') or []) > 1:
            add('aviso', 'raci_dois_a', eid, f'"{c.nome(eid)}" tem {len(e["raci"]["A"])} aprovadores (A): o RACI '
                'pede um só responsável final; os outros vão em C (consultado)')
        for k, lista in e['raci'].items():
            for p in lista:
                if p not in c.papeis:
                    add('erro', 'raci_papel_inexistente', eid, f'RACI "{k}" de "{c.nome(eid)}" cita "{p}", que '
                        'não está em "papeis"')

        # -------- atividades
        if tipo in NOS_DE_TRABALHO:
            if not nome:
                add('erro', 'atividade_sem_nome', eid, f'a atividade "{eid}" não tem nome')
            else:
                _estilo_atividade(c, e, add)
            if tipo == 'subprocesso':
                detalhe = e['bruto'].get('detalhe')
                if detalhe and not isinstance(detalhe, str):
                    add('aviso', 'detalhe_tipo', eid, f'"detalhe" de "{c.nome(eid)}" tem de ser o caminho de uma carta '
                        '(texto), ex.: "kyc/carta.json"')
                    detalhe = None
                elif detalhe and c.caminho and os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(
                        c.caminho)), detalhe)) in (os.path.abspath(c.caminho), os.path.dirname(os.path.abspath(
                        c.caminho))):
                    add('aviso', 'detalhe_si_mesma', eid, f'o detalhe de "{c.nome(eid)}" aponta para esta mesma carta')
                    detalhe = None
                if not detalhe and not e['bruto'].get('detalhe'):
                    add('dica', 'subprocesso_sem_detalhe', eid, f'"{c.nome(eid)}" é subprocesso: aponte a carta dele '
                        'em "detalhe" (ex.: "../kyc/carta.json") para o mapa ter os níveis ligados')
                elif detalhe and c.caminho and not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(c.caminho)),
                                                                   str(detalhe))):
                    add('aviso', 'detalhe_nao_existe', eid, f'"{c.nome(eid)}" aponta o detalhe "{detalhe}", que não '
                        'existe (o caminho é a partir da pasta desta carta)')
                elif detalhe and c.caminho:
                    _conferir_detalhe(c, e, add)
            if not e['papel']:
                add('aviso', 'sem_responsavel', eid, f'quem executa "{c.nome(eid)}"? (sem papel, ela cai na raia '
                    '"sem responsável")')
            if n_out > 1:
                add('aviso', 'divisao_implicita', eid, f'"{c.nome(eid)}" tem {n_out} saídas sem uma porta: use uma '
                    'decisão (um caminho ou outro) ou um paralelo (todos ao mesmo tempo)', '7PMG G4')

        # -------- portas
        if tipo in PORTAS:
            _estilo_porta(c, e, add, n_in, n_out)

        if tipo in ('inicio', 'evento') and n_out > 1:
            add('aviso', 'evento_divide', eid, f'"{c.nome(eid)}" segue para {n_out} lugares: todos acontecem ao '
                'mesmo tempo. Se é isso, ponha um paralelo depois; se é um OU outro, ponha uma decisão', 'M&S')
        if tipo in NOS_DE_TRABALHO + ('evento', 'borda'):
            texto_espera = sem_acento(str(e['tempo_texto'].get('espera', ''))).lower()
            if (e['espera'] and ((e['espera'] >= 5 * 480 and re.search(r'\bdias?\b', texto_espera)) or
                                   (e['espera'] >= 10 * 480 and re.search(r'\d\s*d\b', texto_espera)))
                    and not re.search(r'uteis|util|corrid', texto_espera)):
                add('aviso', 'dias_ambiguos', eid, f'"{c.nome(eid)}": espera de "{e["tempo_texto"].get("espera")}" '
                    'conta como dias ÚTEIS. Se são dias corridos (prazo de contrato, calendário), escreva "dc" '
                    '(30dc ≈ 21 dias úteis)')
            texto_exec = sem_acento(str(e['tempo_texto'].get('execucao', ''))).lower()
            if (e['execucao'] and e['execucao'] >= 5 * 480 and re.search(r'\bdias?\b|\d\s*d\b', texto_exec)
                    and not re.search(r'uteis|util|corrid', texto_exec)):
                add('aviso', 'dias_ambiguos', eid, f'"{c.nome(eid)}": execução de "{e["tempo_texto"].get("execucao")}" '
                    'conta como dias ÚTEIS de trabalho (8 h cada). É isso mesmo, ou é o prazo (espera) em dias '
                    'corridos?')
        # -------- eventos
        if tipo == 'inicio' and not nome:
            add('aviso', 'inicio_sem_nome', eid, 'dê nome ao início com o que dispara o processo '
                '(ex.: "Pedido recebido", "Todo dia 5")', 'M&S')
        if e['gatilho'] == 'erro' and tipo in ('inicio', 'evento'):
            add('erro', 'erro_fora_do_fim', eid, f'"{c.nome(eid)}": gatilho "erro" só vale no fim (o processo termina '
                'com erro); para um erro no meio, use uma decisão ("Deu erro?") e o caminho de exceção', 'M&S')
        if tipo == 'fim' and e['encerra'] and len(c.de_tipo('fim')) == 1:
            add('dica', 'encerra_sozinho', eid, 'com um fim só, "encerra" não muda nada', 'M&S')
        if tipo in ('atividade', 'subprocesso', 'evento', 'borda'):
            texto_espera = str(e['tempo_texto'].get('espera', ''))
            if e['espera'] and e['espera'] >= 24 * 60 and re.search(r'\d\s*(h|hr|hrs|hs|horas?)\b',
                                                                     sem_acento(texto_espera).lower()):
                add('aviso', 'horas_ambiguas', eid, f'"{c.nome(eid)}": espera de "{texto_espera}" conta como horas de '
                    'expediente (24h = 3 dias úteis). Se são horas corridas, escreva "hc" (24hc ≈ 0,7 dia útil)')
        if tipo == 'evento':
            if e['gatilho'] == 'nenhum':
                add('aviso', 'evento_sem_gatilho', eid, f'o evento "{c.nome(eid)}" espera o quê? Diga o "gatilho": '
                    'tempo (prazo), mensagem (chega algo de alguém) ou condição', 'M&S')
            if not nome:
                add('aviso', 'evento_sem_nome', eid, 'todo evento intermediário tem nome (ex.: "Aguardar 2 dias", '
                    '"Resposta do fornecedor recebida")', 'M&S')

    # -------- conjunto
    if len(inicios) > 1:
        add('aviso', 'varios_inicios', None, f'{len(inicios)} inícios: um processo tem um gatilho; se são '
            'gatilhos diferentes do mesmo trabalho, mantenha e dê nome a cada um', '7PMG G3')
    nomes_fim = [sem_acento(e['nome']).lower().strip() for e in fins]
    if len(fins) > 1:
        sem_nome = [e['id'] for e in fins if not e['nome'] or sem_acento(e['nome']).lower().strip() in ('fim', 'final')]
        if sem_nome:
            add('aviso', 'fins_sem_estado', None, f'há {len(fins)} fins: nomeie cada um com o estado final '
                '(ex.: "Pedido entregue", "Pedido cancelado") em vez de "Fim"', 'M&S')
        repetidos = {n for n in nomes_fim if n and nomes_fim.count(n) > 1}
        for n in sorted(repetidos):
            add('dica', 'fins_repetidos', None, f'há mais de um fim chamado "{n}": se é o mesmo estado, '
                'ligue os caminhos a um fim só', 'M&S')
    total = len(c.elementos)
    if total > 50:
        add('aviso', 'mapa_grande', None, f'{total} elementos: acima de 50 o mapa fica difícil de ler; quebre em '
            'subprocessos (tipo "subprocesso") e mapeie cada um numa carta própria', '7PMG G7')
    usados = {e['papel'] for e in c.elementos.values()}
    for pid, p in c.papeis.items():
        if pid not in usados:
            add('dica', 'papel_sem_atividade', None, f'o papel "{p["nome"]}" não executa nada no fluxo '
                '(tire das raias ou ponha no RACI como consultado/informado)')
    for d in c.dores + c.riscos:
        for ref in d.get('elementos') or []:
            if ref not in c.elementos:
                add('erro', 'referencia_inexistente', None, f'"{d.get("id") or d.get("descricao", "")[:40]}" cita o '
                    f'elemento "{ref}", que não existe')
    ids_dores = {d.get('id') for d in c.dores}
    for m in c.melhorias:
        for ref in m.get('resolve') or []:
            if ref not in ids_dores:
                add('erro', 'dor_inexistente', None, f'a melhoria "{m.get("id") or m.get("descricao", "")[:40]}" '
                    f'resolve "{ref}", que não está em "dores"')
        for ref in m.get('elementos') or []:
            if ref not in c.elementos:
                add('erro', 'referencia_inexistente', None, f'a melhoria "{m.get("id")}" cita o elemento "{ref}", '
                    'que não existe')
    # a prova do fluxo (jogo de fichas) só faz sentido com o fluxo ligado: com erro de ligação, ela repetiria
    # o mesmo problema com outras palavras
    if not any(a.nivel == 'erro' for a in out):
        from .fichas import achados
        for nivel, codigo, eid, texto in achados(c):
            add(nivel, codigo, eid, texto, '7PMG G4' if codigo != 'fichas_incompleto' else 'Casa')
    return out


def _estilo_atividade(c, e, add):
    nome, eid = e['nome'], e['id']
    p = primeira_palavra(nome)
    if not parece_verbo(p):
        sug = sugestao_de_verbo(nome)
        extra = f' (ex.: "{sug}" + o que é feito)' if sug else ' (ex.: "Aprovar requisição", "Emitir nota fiscal")'
        add('aviso', 'nome_sem_verbo', eid, f'"{nome}": comece a atividade com verbo no infinitivo + objeto{extra}',
            '7PMG G6')
    if _duas_atividades(nome):
        add('aviso', 'duas_atividades', eid, f'"{nome}" parece ter dois trabalhos; se forem feitos por pessoas ou '
            'em momentos diferentes, separe em duas atividades', 'Casa')
    if len(nome) > 60:
        add('dica', 'nome_longo', eid, f'"{nome[:40]}...": nome com {len(nome)} caracteres; deixe o detalhe na '
            '"descricao" (até ~6 palavras no desenho)', 'M&S')


def _estilo_porta(c, e, add, n_in, n_out):
    eid, tipo, nome = e['id'], e['tipo'], e['nome']
    rotulo_tipo = {'decisao': 'decisão', 'paralelo': 'paralelo', 'inclusivo': 'inclusivo',
                   'corrida': 'corrida'}[tipo]
    if n_in > 1 and n_out > 1:
        add('aviso', 'porta_mista', eid, f'a {rotulo_tipo} "{c.nome(eid)}" junta e divide ao mesmo tempo: separe '
            'em duas (uma junta, outra divide)', '7PMG G2')
    if n_out < 2 and n_in < 2:
        add('erro', 'porta_inutil', eid, f'a {rotulo_tipo} "{c.nome(eid)}" tem uma entrada e uma saída: ou falta um '
            'caminho, ou ela não é necessária', 'M&S')
    divide = n_out > 1
    if tipo == 'inclusivo' and divide:
        pcts = [f['percentual'] for f in c.saidas[eid]]
        nenhum = 1.0
        for x in pcts:
            nenhum *= 1 - (x or 0) / 100
        if pcts and None not in pcts and nenhum > 0.01 and not any('senao' in sem_acento(f['rotulo']).lower()
                                                                   for f in c.saidas[eid]):
            add('aviso', 'inclusivo_pode_nao_seguir', eid, f'em "{c.nome(eid)}", com esses percentuais, em '
                f'{nenhum:.0%} dos casos nenhum caminho acontece e o caso para: ponha um caminho "Senão" ou '
                'confira os percentuais', 'M&S')
        add('aviso', 'inclusivo', eid, f'"{c.nome(eid)}" é um OU inclusivo (um ou mais caminhos): é o que mais gera '
            'erro de leitura; dá para escrever com decisões ou paralelo?', '7PMG G5')
    if tipo == 'corrida' and n_in > 1 and not divide:
        add('erro', 'corrida_juntando', eid, f'a corrida "{c.nome(eid)}" junta caminhos: ela só abre ("o que vier '
            'primeiro"); para juntar, use uma decisão sem nome ou ligue direto na próxima atividade', 'M&S')
    if tipo == 'corrida' and not divide and n_in <= 1:
        add('erro', 'corrida_um_caminho', eid, f'a corrida "{c.nome(eid)}" tem um caminho só: ela existe para '
            'escolher entre eventos que podem chegar primeiro (pelo menos dois)', 'M&S')
    if tipo == 'corrida' and divide:
        # o BPMN só aceita, depois da porta por evento, eventos que esperam algo (prazo, mensagem, condição, sinal)
        for f in c.saidas[eid]:
            alvo = c.elementos.get(f['para'])
            if alvo and len(c.entradas[alvo['id']]) > 1:
                add('erro', 'corrida_evento_compartilhado', eid, f'"{c.nome(alvo["id"])}" vem da corrida '
                    f'"{c.nome(eid)}" e de outro lugar: o evento depois de uma corrida só pode vir dela (BPMN)', 'M&S')
            recebe = alvo and alvo['tipo'] == 'atividade' and alvo['bruto'].get('recebe')
            if alvo and not recebe and not (alvo['tipo'] == 'evento' and alvo['gatilho'] in
                                            ('tempo', 'mensagem', 'condicao', 'sinal')
                                            and not alvo['bruto'].get('envia')):
                add('erro', 'corrida_sem_evento', eid, f'na corrida "{c.nome(eid)}", cada caminho começa com o '
                    f'evento que pode chegar primeiro (prazo, mensagem, condição); "{c.nome(f["para"])}" não é um '
                    'evento assim. Ex.: corrida -> "Resposta do cliente recebida" (mensagem) / "Aguardar 5 dias" '
                    '(tempo)', 'M&S')
    if tipo == 'decisao' and divide and re.search(
            r'\b(em|dentro de|antes de)\s+(ate\s+)?\d+\s*(dias?|horas?|h|d|semanas?|meses?)\b|\bprazo\b|\bvenc|\bexpir',
            sem_acento(nome or '').lower()):
        add('aviso', 'decisao_de_prazo', eid, f'"{nome}" decide DEPOIS se o prazo passou: no BPMN, esperar algo OU um '
            'prazo é uma corrida (mensagem x tempo) ou uma borda de prazo na atividade; a decisão deixa o caso '
            'parado sem dizer o que acontece quando o prazo vence', 'M&S')
    if tipo == 'decisao' and divide:
        saidas = c.saidas[eid]
        sem_rotulo = [f for f in saidas if not f['rotulo']]
        if sem_rotulo:
            add('erro', 'saida_sem_rotulo', eid, f'a decisão "{c.nome(eid)}" tem saída sem rótulo: diga a resposta '
                'de cada caminho ("Sim"/"Não" ou o resultado: "Aprovado", "Reprovado")', 'M&S')
        rotulos = [sem_acento(f['rotulo']).lower() for f in saidas if f['rotulo']]
        if len(set(rotulos)) < len(rotulos):
            add('erro', 'rotulo_repetido', eid, f'a decisão "{c.nome(eid)}" tem duas saídas com o mesmo rótulo')
        if not nome:
            add('aviso', 'decisao_sem_pergunta', eid, 'escreva a decisão como pergunta (ex.: "Pedido aprovado?")',
                'M&S')
        elif not nome.rstrip().endswith('?'):
            add('aviso', 'decisao_sem_interrogacao', eid, f'"{nome}": escreva a decisão como pergunta, com "?" '
                '(ex.: "Pedido aprovado?")', 'M&S')
        antes = [c.elementos.get(f['de']) for f in c.entradas[eid]]
        if antes and all(a and a['tipo'] == 'inicio' for a in antes):
            add('aviso', 'decisao_sem_trabalho', eid, f'"{c.nome(eid)}" vem logo depois do início: a porta não '
                'decide sozinha; quem analisa e decide? (ponha a atividade antes, ex.: "Analisar pedido")', 'M&S')
        elif (e['papel'] and antes and all(a and a['tipo'] in NOS_DE_TRABALHO and a['papel'] != e['papel']
                                            for a in antes)):
            add('aviso', 'decisao_sem_trabalho', eid, f'"{c.nome(eid)}" é decidida por {c.nome_papel(e["papel"])}, '
                f'mas a atividade antes é de outro papel: a porta não decide sozinha; falta "Analisar ..." de '
                f'{c.nome_papel(e["papel"])}? (ou a decisão é de quem fez a atividade anterior)', 'M&S')
    if tipo == 'paralelo' and divide:
        esperas = [c.elementos[f['para']] for f in c.saidas[eid] if f['para'] in c.elementos
                   and c.elementos[f['para']]['tipo'] == 'evento' and c.elementos[f['para']]['gatilho'] in
                   ('tempo', 'mensagem', 'condicao', 'sinal') and not c.elementos[f['para']]['bruto'].get('envia')]
        if len(esperas) > 1 and any(x['gatilho'] == 'tempo' for x in esperas):
            add('aviso', 'paralelo_de_esperas', eid, 'o paralelo' + (f' "{nome}"' if nome else '') + ' espera '
                + ' E '.join(f'"{c.nome(x["id"])}"' for x in esperas) + ': todo caso passa pelos dois (e termina '
                'pelos dois fins). Se vale o que acontecer primeiro (resposta ou prazo), troque por uma corrida '
                '("tipo": "corrida")', 'M&S')
        if any(f['rotulo'] for f in c.saidas[eid]):
            add('dica', 'paralelo_rotulado', eid, 'as saídas de um paralelo não têm rótulo: todas acontecem', 'M&S')
    if not divide and n_in > 1 and nome and tipo != 'paralelo':
        add('dica', 'juncao_com_nome', eid, f'"{nome}" só junta caminhos: a junção não precisa de nome', 'M&S')


def _corridas(c, add):
    """Paralelo em que um ramo encerra tudo (prazo que vence) e outro termina num fim comum: quando o ramo
    comum acaba, a espera do outro continua e, ao vencer, encerra o processo como se tivesse expirado."""
    from .analise import _corrida, _ramo
    volta = c.arestas_de_volta()
    for p in c.de_tipo('paralelo'):
        if len(c.saidas[p['id']]) < 2:
            continue
        ramos = [_ramo(c, f['para'], volta) for f in c.saidas[p['id']]]
        if not _corrida(c, ramos):
            continue
        comuns = [r[-1] for r, j in ramos if j is None and r and c.elementos[r[-1]]['tipo'] == 'fim'
                  and not c.elementos[r[-1]]['encerra']]
        for f in comuns:
            add('aviso', 'corrida_sem_encerra', f, f'o fim "{c.nome(f)}" acontece com outro ramo em paralelo que '
                'encerra tudo (prazo): depois de "{0}", o prazo continua correndo e encerra o processo do jeito '
                'errado. Marque "{0}" com "encerra": true também (o primeiro que chegar encerra)'.format(c.nome(f)),
                'M&S')


def _percentuais(c, add):
    """As saídas de uma decisão somam 100%; 0,85 (fração) quase sempre quis dizer 85%."""
    for e in c.de_tipo(*ESCOLHA):
        saidas = c.saidas[e['id']]
        pcts = [f['percentual'] for f in saidas if f['percentual'] is not None]
        if not pcts or len(saidas) < 2:
            continue
        if len(pcts) == len(saidas) and all(p <= 1 for p in pcts) and abs(sum(pcts) - 1) < 0.02:
            add('erro', 'percentual_fracao', e['id'], f'"{c.nome(e["id"])}": os percentuais parecem fração '
                f'({", ".join(f"{p:g}" for p in pcts)}): escreva de 0 a 100 (85, não 0,85)')
            continue
        soma = sum(pcts)
        if e['tipo'] in ('decisao', 'corrida') and len(pcts) == len(saidas) and abs(soma - 100) > 1:
            add('erro', 'percentual_soma', e['id'], f'"{c.nome(e["id"])}": as saídas somam {soma:g}% (uma decisão '
                'escolhe um caminho: o total é 100%)')
        elif e['tipo'] in ('decisao', 'corrida') and soma > 101:
            add('erro', 'percentual_soma', e['id'], f'"{c.nome(e["id"])}": as saídas informadas já somam {soma:g}%')


_PRENOMES = {'ana', 'maria', 'joao', 'jose', 'carlos', 'paulo', 'pedro', 'lucas', 'marcos', 'luiz', 'luis',
             'gabriel', 'rafael', 'daniel', 'marcelo', 'bruno', 'eduardo', 'felipe', 'rodrigo', 'fernando',
             'gustavo', 'leonardo', 'ricardo', 'tiago', 'thiago', 'andre', 'antonio', 'francisco', 'juliana',
             'mariana', 'fernanda', 'patricia', 'aline', 'camila', 'amanda', 'bruna', 'jessica', 'leticia',
             'julia', 'beatriz', 'larissa', 'vanessa', 'sandra', 'adriana', 'claudia', 'renata', 'carla', 'paula',
             'marina', 'luana', 'roberto', 'sergio', 'fabio', 'alexandre', 'vinicius', 'mateus', 'matheus',
             'diego', 'leandro', 'renato', 'jorge', 'claudio', 'cristiane', 'simone', 'debora', 'raquel',
             'priscila', 'tatiana', 'silvia', 'helena', 'alice', 'laura', 'sofia', 'isabela', 'joana', 'rita'}


def _papeis_que_parecem_pessoas(c, add):
    for pid, p in c.papeis.items():
        palavras = sem_acento(p['nome']).lower().split()
        if palavras and palavras[0] in _PRENOMES and p.get('tipo') != 'externo':
            add('aviso', 'papel_pessoa', None, f'o papel "{p["nome"]}" parece o nome de uma pessoa: use o cargo '
                'ou a área ("Analista de RH"); a pessoa vai em "participantes"')


def resumo(achados):
    n = {'erro': 0, 'aviso': 0, 'dica': 0}
    for a in achados:
        n[a.nivel] += 1
    return n


def imprimir(c, achados, detalhe_dicas=True):
    n = resumo(achados)
    print(f'Carta: {c.titulo()}  ({len(c.elementos)} elementos, {len(c.fluxos)} fluxos, {len(c.raias())} raias)')
    if not achados:
        print('✓ Nenhum problema. Próximo: python senku.py lacunas <carta> (o que falta perguntar) '
              'ou python senku.py desenhar <carta>')
        return
    rotulo = {'erro': '✗ ERROS (o desenho sai errado; corrija antes do aceite)',
              'aviso': '! AVISOS (regras de boa modelagem; decida com a pessoa)',
              'dica': '· DICAS'}
    for nivel in ('erro', 'aviso', 'dica'):
        lista = [a for a in achados if a.nivel == nivel]
        if not lista or (nivel == 'dica' and not detalhe_dicas):
            continue
        print(f'\n{rotulo[nivel]}: {len(lista)}')
        for a in lista:
            onde = f'[{a.elemento}] ' if a.elemento else ''
            fonte = f'  ({a.fonte})' if a.fonte != 'Casa' else ''
            print(f'  {onde}{a.texto}{fonte}')
    print(f'\nTotal: {n["erro"]} erro(s), {n["aviso"]} aviso(s), {n["dica"]} dica(s).')
    if n['erro']:
        print('Próximo: corrija os erros no carta.json e rode validar de novo.')
    else:
        print('Próximo: leve os avisos à pessoa em linguagem de negócio; depois, python senku.py lacunas <carta>.')
