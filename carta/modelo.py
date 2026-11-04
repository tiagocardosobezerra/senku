"""
Carrega a carta e devolve o processo como grafo: papéis (raias), elementos
(nós) e fluxos (arestas). Aceita o jeito curto de escrever o fluxo ("segue")
e o jeito longo ("fluxos"), papéis pelo id ou pelo nome e os sinônimos de
tipo ("tarefa", "gateway", "xor"...). O que não dá para entender não é
adivinhado: vira um problema, que a validação mostra.
"""

import re

from . import FORMATO
from .util import como_lista, ler_json, minutos, sem_acento


_MANUAL = {'manual', 'nenhum', 'nenhuma', '-', 'n/a', 'na', 'papel', 'sem sistema'}
_CONTROLE = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ud800-\udfff￾￿]')


def prazo_no_nome(nome):
    """O prazo escrito no nome de um evento de tempo ("Aguardar 10 dias corridos" -> "10 dias corridos")."""
    achado = re.search(r'(\d+(?:[.,]\d+)?(?:\s*(?:a|-|ou)\s*\d+(?:[.,]\d+)?)?\s*'
                       r'(?:minutos?|min|horas? corridas?|horas?|hc|h|dias? uteis|dias? corridos?|dias?|'
                       r'dc|du|d|semanas?|sem|mes(?:es)?))\b', sem_acento(str(nome or '')).lower())
    return achado.group(1) if achado and minutos(achado.group(1)) is not None else None


def _limpar(x):
    """Tira caracteres que o XML não aceita (BPMN, draw.io, SVG e Word quebrariam): devolve (cópia, quantos)."""
    if isinstance(x, str):
        novo = _CONTROLE.sub(' ', x)
        return novo, int(novo != x)
    if isinstance(x, dict):
        out, n = {}, 0
        for k, v in x.items():
            v2, m = _limpar(v)
            k2, m2 = _limpar(k) if isinstance(k, str) else (k, 0)
            out[k2] = v2
            n += m + m2
        return out, n
    if isinstance(x, list):
        out, n = [], 0
        for v in x:
            v2, m = _limpar(v)
            out.append(v2)
            n += m
        return out, n
    return x, 0


def _booleano(v):
    """true/false de verdade, e também "sim"/"não", "true"/"false", 1/0. None se não der para saber."""
    if isinstance(v, bool):
        return v
    if v is None or v == '':
        return False
    if isinstance(v, (int, float)):
        return bool(v)
    t = sem_acento(str(v)).strip().lower()
    if t in ('true', 'sim', 's', 'yes', 'y', '1', 'verdadeiro', 'x'):
        return True
    if t in ('false', 'nao', 'n', 'no', '0', 'falso'):
        return False
    return None


def _obj(x):
    return x if isinstance(x, dict) else {}


def _textos(x):
    """Lista de textos: aceita texto solto, lista, número; ignora objeto (que não é texto)."""
    return [str(v).strip() for v in como_lista(x) if not isinstance(v, (dict, list)) and str(v).strip()]

TIPOS = {
    'inicio': 'inicio', 'start': 'inicio', 'evento_inicio': 'inicio',
    'fim': 'fim', 'end': 'fim', 'termino': 'fim', 'evento_fim': 'fim',
    'atividade': 'atividade', 'tarefa': 'atividade', 'task': 'atividade', 'passo': 'atividade',
    'subprocesso': 'subprocesso', 'subprocess': 'subprocesso',
    'decisao': 'decisao', 'gateway': 'decisao', 'xor': 'decisao', 'exclusivo': 'decisao',
    'paralelo': 'paralelo', 'and': 'paralelo',
    'inclusivo': 'inclusivo', 'or': 'inclusivo',
    'evento': 'evento', 'intermediario': 'evento', 'espera': 'evento',
    'corrida': 'corrida', 'porta_evento': 'corrida', 'evento_porta': 'corrida', 'primeiro': 'corrida',
    'o que vier primeiro': 'corrida', 'eventbased': 'corrida', 'borda': 'borda',
}
NOS_DE_TRABALHO = ('atividade', 'subprocesso')
PORTAS = ('decisao', 'paralelo', 'inclusivo', 'corrida')
# portas em que só alguns caminhos acontecem (cada saída tem uma chance): decisão, OU inclusivo e corrida
ESCOLHA = ('decisao', 'inclusivo', 'corrida')
EVENTOS = ('inicio', 'fim', 'evento')
GATILHOS = ('nenhum', 'mensagem', 'tempo', 'condicao', 'sinal', 'erro')
VALORES = {'VA': 'agrega valor ao cliente', 'NAV-N': 'não agrega, mas é necessário (negócio, lei, controle)',
           'NAV': 'não agrega valor (desperdício)'}
_SINONIMOS_VALOR = {'VA': 'VA', 'AV': 'VA', 'AGREGA': 'VA', 'BVA': 'NAV-N', 'NAVN': 'NAV-N', 'NAV-N': 'NAV-N',
                    'NECESSARIO': 'NAV-N', 'NNVA': 'NAV-N', 'NVA': 'NAV', 'NAV': 'NAV', 'DESPERDICIO': 'NAV'}
SEM_PAPEL = '_sem_papel'


class Carta:
    """O processo pronto para validar, analisar e desenhar."""

    def __init__(self, dados, caminho=None):
        self.problemas = []                     # (codigo, elemento, texto): o que a leitura não conseguiu entender
        dados, sujos = _limpar(dados)
        if sujos:
            self.problemas.append(('caractere_invisivel', None, f'{sujos} texto(s) tinham caractere invisível '
                                   '(comum em texto colado do Word ou do e-mail): troquei por espaço'))
        self.dados = dados
        self.caminho = caminho
        for chave, tipo in (('processo', dict), ('sipoc', dict), ('elementos', list), ('papeis', list),
                            ('sistemas', list), ('regras', list)):
            if dados.get(chave) not in (None, '') and not isinstance(dados.get(chave), tipo):
                forma = 'um objeto { }' if tipo is dict else 'uma lista [ ]'
                self.problemas.append(('tipo_invalido', None, f'"{chave}" deveria ser {forma} (referencias/carta.md)'))
        self.processo = dict(_obj(dados.get('processo')))
        for campo, v in list(self.processo.items()):
            if campo == 'escopo':
                continue
            if campo in ('normas', 'premissas'):
                self.processo[campo] = _textos(v)
            else:
                self.processo[campo] = self._texto_campo(v, f'processo.{campo}')
        cen = sem_acento(str(self.processo.get('cenario') or 'as-is')).lower().replace('_', '-').replace(' ', '-')
        cen = {'asis': 'as-is', 'atual': 'as-is', 'tobe': 'to-be', 'futuro': 'to-be', 'proposto': 'to-be'}.get(
            cen.replace('-', ''), cen)
        if cen not in ('as-is', 'to-be'):
            self.problemas.append(('tipo_invalido', None, f'"processo.cenario" é "as-is" ou "to-be" '
                                   f'(veio "{self.processo.get("cenario")}")'))
            cen = 'as-is'
        self.processo['cenario'] = cen
        escopo = self.processo.get('escopo')
        if escopo not in (None, '') and not isinstance(escopo, dict):
            self.problemas.append(('tipo_invalido', None, '"processo.escopo" é um objeto: {"inicio": ..., "fim": ..., '
                                   '"inclui": [...], "nao_inclui": [...]}'))
            self.processo['escopo'] = {}
        elif isinstance(escopo, dict):
            self.processo['escopo'] = {k: (_textos(v) if k in ('inclui', 'nao_inclui')
                                           else self._texto_campo(v, f'processo.escopo.{k}'))
                                       for k, v in escopo.items()}
        self.sipoc = {k: _textos(v) for k, v in _obj(dados.get('sipoc')).items()}
        self.papeis = {}                        # id -> {id, nome, tipo, descricao}
        self.sistemas = {}
        self.elementos = {}                     # id -> elemento normalizado (ordem da carta)
        self.fluxos = []                        # {id, de, para, rotulo, condicao}
        self.regras = {}
        for i, r in enumerate(como_lista(dados.get('regras')) if isinstance(dados.get('regras'), list) else []):
            if isinstance(r, str):
                r = {'texto': r}
            if isinstance(r, dict):
                self.regras[str(r.get('id') or f'R{i + 1}')] = r
        for chave in ('indicadores', 'dores', 'riscos', 'melhorias', 'glossario', 'pendencias', 'historico',
                      'documentos', 'participantes'):
            itens = []
            for x in como_lista(dados.get(chave)):
                if isinstance(x, str) and chave in ('pendencias', 'dores', 'melhorias'):
                    x = {'pergunta': x} if chave == 'pendencias' else {'descricao': x}
                if not isinstance(x, dict):
                    self.problemas.append(('tipo_invalido', None, f'um item de "{chave}" não é um objeto ({str(x)[:40]})'))
                    continue
                x = dict(x)
                for campo, v in list(x.items()):
                    if campo in ('elementos', 'resolve'):            # texto solto vira lista de um item, não letras
                        x[campo] = _textos(v)
                    else:
                        x[campo] = self._texto_campo(v, f'{chave}.{campo}')
                itens.append(x)
            setattr(self, chave, itens)
        self._ler_papeis()
        self._ler_sistemas()
        self._ler_elementos()
        self._ler_fluxos()
        self.entradas = {i: [] for i in self.elementos}
        self.saidas = {i: [] for i in self.elementos}
        for f in self.fluxos:
            if f['de'] in self.saidas:
                self.saidas[f['de']].append(f)
            if f['para'] in self.entradas:
                self.entradas[f['para']].append(f)
        self._herdar_papeis()

    def _herdar_papeis(self):
        """Evento e porta sem papel ficam na raia de quem vem antes (ou, no início, de quem vem depois): sem
        isso, nasce uma raia "(sem responsável)" que não existe no processo. Atividade sem papel não herda: a
        pergunta "quem faz?" continua aberta."""
        for _ in range(len(self.elementos)):
            mudou = False
            for e in self.elementos.values():
                if e['papel'] or e['tipo'] in NOS_DE_TRABALHO:
                    continue
                vizinhos = [self.elementos.get(f['de']) for f in self.entradas[e['id']]]
                vizinhos += [self.elementos.get(f['para']) for f in self.saidas[e['id']]]
                for v in vizinhos:
                    if v and v['papel']:
                        e['papel'] = v['papel']
                        e['papel_herdado'] = True
                        mudou = True
                        break
            if not mudou:
                break

    def _texto_campo(self, v, onde):
        """Campo de texto: número vira texto ("volume": 120), lista vira texto, objeto é erro de tipo."""
        if v is None or isinstance(v, str):
            return v
        if isinstance(v, bool):
            return 'sim' if v else 'não'
        if isinstance(v, (int, float)):
            return f'{v:g}' if isinstance(v, float) else str(v)
        if isinstance(v, (list, tuple)):
            return ' / '.join(_textos(v))
        self.problemas.append(('tipo_invalido', None, f'"{onde}" é texto, não objeto'))
        return ''

    # ------------------------------------------------------------ leitura
    def _ler_papeis(self):
        for i, p in enumerate(como_lista(self.dados.get('papeis') or self.dados.get('raias'))):
            if not isinstance(p, dict):
                p = {'nome': str(p)}
            pid = str(p.get('id') or p.get('nome') or f'papel{i + 1}')
            if pid in self.papeis:
                self.problemas.append(('papel_repetido', None, f'o papel "{pid}" aparece duas vezes em "papeis": '
                                       f'"{self.papeis[pid]["nome"]}" e "{p.get("nome") or pid}"'))
                continue
            self.papeis[pid] = {'id': pid, 'nome': str(p.get('nome') or pid), 'tipo': p.get('tipo') or 'interno',
                                'descricao': p.get('descricao', ''), 'area': p.get('area', '')}
        self._papel_por_nome = {sem_acento(p['nome']).lower(): pid for pid, p in self.papeis.items()}

    def _ler_sistemas(self):
        for i, s in enumerate(como_lista(self.dados.get('sistemas'))):
            if not isinstance(s, dict):
                s = {'nome': str(s)}
            sid = str(s.get('id') or s.get('nome') or f'sistema{i + 1}')
            self.sistemas[sid] = {'id': sid, 'nome': str(s.get('nome') or sid), 'descricao': s.get('descricao', '')}
        self._sistema_por_nome = {sem_acento(s['nome']).lower(): sid for sid, s in self.sistemas.items()}

    def id_papel(self, ref):
        if ref in (None, '') or isinstance(ref, (dict, list)):
            return None
        ref = str(ref)
        if ref in self.papeis:
            return ref
        return self._papel_por_nome.get(sem_acento(ref).lower(), ref)

    def id_sistema(self, ref):
        if ref in (None, '') or isinstance(ref, (dict, list)):
            return None
        ref = str(ref)
        if ref in self.sistemas:
            return ref
        return self._sistema_por_nome.get(sem_acento(ref).lower(), ref)

    def _expandir_bordas(self, brutos):
        """Cada borda de uma atividade ("prazo de 48h estourou", "cliente cancelou") vira um elemento próprio,
        logo depois da atividade: o evento preso na borda do BPMN."""
        out = []
        for i, e in enumerate(brutos):
            if isinstance(e, dict) and e.get('id') in (None, ''):
                # sem id: ganha o da posição na lista ORIGINAL aqui, antes de as bordas entrarem na lista (senão
                # a borda apontaria para um id que a atividade não recebe)
                e = dict(e, id=f'e{i + 1}')
                self.problemas.append(('sem_id', e['id'], f'o elemento {i + 1} ("{e.get("nome") or e.get("tipo") or ""}") '
                                       f'não tem "id": ganhou "{e["id"]}". Dê um id para ligar nele com segurança'))
            out.append(e)
            if not isinstance(e, dict) or not e.get('bordas'):
                continue
            host = str(e.get('id') or f'e{i + 1}')
            if not isinstance(e['bordas'], list):
                self.problemas.append(('tipo_invalido', host, '"bordas" é uma lista de objetos'))
                continue
            for k, b in enumerate(e['bordas'], 1):
                if not isinstance(b, dict):
                    self.problemas.append(('tipo_invalido', host, f'a borda {k} de "{host}" não é um objeto'))
                    continue
                tempo = b.get('tempo') or b.get('prazo')
                out.append({'id': str(b.get('id') or f'{host}~{k}'), 'tipo': 'borda', 'nome': b.get('nome', ''),
                            'gatilho': b.get('gatilho') or ('tempo' if tempo else 'erro'),
                            'tempo': {'espera': tempo} if tempo else {}, 'segue': b.get('segue'),
                            '_anexo': host, '_interrompe': b.get('interrompe', True),
                            '_percentual': b.get('percentual'), '_bruto_borda': b})
        return out

    def _ler_elementos(self):
        brutos = self._expandir_bordas(como_lista(self.dados.get('elementos')))
        for i, e in enumerate(brutos):
            if not isinstance(e, dict):
                self.problemas.append(('elemento_invalido', None, f'item {i + 1} de "elementos" não é um objeto'))
                continue
            eid = str(e.get('id') or f'e{i + 1}')
            if eid in self.elementos:
                self.problemas.append(('id_repetido', eid, f'o id "{eid}" aparece mais de uma vez'))
                continue
            tipo_bruto = sem_acento(str(e.get('tipo') or 'atividade')).lower()
            tipo = TIPOS.get(tipo_bruto)
            if tipo == 'borda' and not e.get('_anexo'):
                self.problemas.append(('tipo_desconhecido', eid, 'a borda não é um elemento solto: ela vai dentro da '
                                       'atividade, em "bordas" (referencias/carta.md)'))
                tipo = 'evento'
            if tipo is None:
                validos = sorted(set(TIPOS.values()) - {'borda'})
                self.problemas.append(('tipo_desconhecido', eid, f'tipo "{e.get("tipo")}" desconhecido '
                                       f'(use: {", ".join(validos)})'))
                tipo = 'atividade'
            tempo = e.get('tempo') or {}
            if not isinstance(tempo, dict):
                tempo = {'execucao': tempo} if isinstance(tempo, (str, int, float)) else {}
            valor = e.get('valor')
            if valor:
                v = _SINONIMOS_VALOR.get(sem_acento(str(valor)).upper().replace(' ', ''))
                if v is None:
                    self.problemas.append(('valor_desconhecido', eid, f'valor "{valor}" desconhecido '
                                           '(use VA, NAV-N ou NAV)'))
                valor = v
            raci = e.get('raci') or {}
            if not isinstance(raci, dict):
                self.problemas.append(('tipo_invalido', eid, '"raci" é um objeto: {"A": "papel", "C": [...], '
                                       '"I": [...]} (o R é o "papel")'))
                raci = {}
            for k in ('papel', 'sistema', 'sistemas'):
                if isinstance(e.get(k), dict):
                    self.problemas.append(('tipo_invalido', eid, f'"{k}" é o id ou o nome, não um objeto'))
            self.elementos[eid] = {
                'id': eid, 'tipo': tipo, 'nome': ' '.join(_textos(e.get('nome'))),
                'papel': self.id_papel(e.get('papel') or e.get('responsavel') or e.get('raia')),
                'sistema': [x for x in (self.id_sistema(s) for s in como_lista(e.get('sistema') or e.get('sistemas'))
                                        if sem_acento(str(s)).strip().lower() not in _MANUAL) if x],
                # respondeu sobre o sistema: lista (mesmo vazia = manual) ou "manual"; "" e null contam como não
                # respondido (o esqueleto deixa "" de lugar para a resposta)
                'sistema_respondido': any(k in e and e[k] not in ('', None) for k in ('sistema', 'sistemas')),
                'descricao': ' '.join(_textos(e.get('descricao'))),
                'como': _textos(e.get('como') or e.get('passos')),
                'entradas': _textos(e.get('entradas')), 'saidas': _textos(e.get('saidas')),
                'regras': _textos(e.get('regras')),
                'documentos': _textos(e.get('documentos')),
                'execucao': minutos(tempo.get('execucao')), 'espera': minutos(tempo.get('espera')),
                'tempo_texto': {k: tempo.get(k) for k in ('execucao', 'espera') if tempo.get(k) not in (None, '')},
                'valor': valor,
                'raci': {k: [self.id_papel(x) for x in como_lista(raci.get(k))] for k in ('A', 'C', 'I')},
                'gatilho': sem_acento(str(e.get('gatilho') or e.get('evento') or 'nenhum')).lower(),
                'frequencia': e.get('frequencia', ''), 'excecoes': _textos(e.get('excecoes')),
                'automatizada': bool(_booleano(e.get('automatizada'))),
                'encerra': bool(_booleano(e.get('encerra'))),
                'segue_bruto': e.get('segue', e.get('proximo')),
                'bruto': e,
                'anexo': e.get('_anexo'), 'interrompe': _booleano(e.get('_interrompe')) is not False,
                'percentual_borda': e.get('_percentual'),
            }
            el = self.elementos[eid]
            if el['anexo']:
                host = self.elementos.get(el['anexo'])
                el['papel'] = host['papel'] if host else el['papel']
                el['bruto'] = e.get('_bruto_borda') or {}
            if tipo == 'evento' and el['gatilho'] == 'tempo' and el['espera'] is None:
                # "Aguardar 10 dias corridos": o prazo já está no nome; sem ele, o lacunas pergunta
                achado = prazo_no_nome(el['nome'])
                if achado:
                    el['espera'] = minutos(achado)
                    el['tempo_texto'] = dict(el['tempo_texto'], espera=achado)
                    el['espera_do_nome'] = True
            for campo in ('automatizada', 'encerra'):
                if campo in e and _booleano(e.get(campo)) is None:
                    self.problemas.append(('tipo_invalido', eid, f'"{campo}" é true ou false (veio "{e.get(campo)}")'))
            if self.elementos[eid]['gatilho'] not in GATILHOS:
                self.problemas.append(('gatilho_desconhecido', eid, f'gatilho "{e.get("gatilho") or e.get("evento")}" '
                                       f'desconhecido (use: {", ".join(GATILHOS)})'))
                self.elementos[eid]['gatilho'] = 'nenhum'
            for t in ('execucao', 'espera'):
                if tempo.get(t) not in (None, '') and self.elementos[eid][t] is None:
                    self.problemas.append(('tempo_ilegivel', eid, f'tempo de {t} "{tempo.get(t)}" não deu para ler '
                                           '(use 15min, 2h, 1h30, 1,5d, 3dc, "2 a 4h")'))

    def _ler_fluxos(self):
        n = 0

        def novo(de, para, rotulo='', condicao='', percentual=None):
            nonlocal n
            n += 1
            try:
                if isinstance(percentual, bool):
                    raise ValueError
                pct = float(str(percentual).replace('%', '').replace(',', '.')) if percentual not in (None, '') else None
                if pct is not None and not 0 <= pct <= 100:
                    raise ValueError
            except ValueError:
                self.problemas.append(('percentual_ilegivel', de, f'percentual "{percentual}" não é um número de 0 '
                                       'a 100'))
                pct = None
            if isinstance(para, (dict, list)) or para in (None, ''):
                self.problemas.append(('fluxo_sem_destino', de, f'uma saída de "{de}" não diz para onde vai'))
                return
            self.fluxos.append({'id': f'f{n}', 'de': de, 'para': str(para), 'rotulo': str(rotulo or '').strip(),
                                'condicao': condicao or '', 'percentual': pct, 'borda': False})

        for e in self.elementos.values():
            if e['anexo']:                               # a atividade "segue" para a borda: é a saída de exceção
                novo(e['anexo'], e['id'], e['nome'], '', e['percentual_borda'])
                if self.fluxos and self.fluxos[-1]['para'] == e['id']:
                    self.fluxos[-1]['borda'] = True
                    e['percentual_borda'] = self.fluxos[-1]['percentual']    # "10%" vira 10.0
            for s in como_lista(e.pop('segue_bruto')):
                if s is None:
                    continue
                if isinstance(s, dict):
                    para = s.get('para') or s.get('destino')
                    if not para:
                        self.problemas.append(('fluxo_sem_destino', e['id'], f'uma saída de "{e["id"]}" não diz "para"'))
                        continue
                    novo(e['id'], para, s.get('rotulo') or s.get('se') or '', s.get('condicao', ''), s.get('percentual'))
                else:
                    novo(e['id'], s)
        for f in como_lista(self.dados.get('fluxos')):
            if isinstance(f, dict) and f.get('de') and f.get('para'):
                novo(str(f['de']), f['para'], f.get('rotulo', ''), f.get('condicao', ''), f.get('percentual'))

    # ------------------------------------------------------------ consultas
    def nome(self, eid):
        e = self.elementos.get(eid)
        if not e:
            return eid
        return e['nome'] or {'paralelo': '(paralelo)', 'decisao': '(decisão)', 'inclusivo': '(inclusivo)',
                             'inicio': '(início)', 'fim': '(fim)', 'evento': '(evento)'}.get(e['tipo'], eid)

    def destino_legivel(self, eid):
        """Para onde o fluxo vai, em palavras: atravessa porta sem nome ("(paralelo)" vira as atividades
        que ela dispara)."""
        e = self.elementos.get(eid)
        if not e:
            return eid
        if e['nome'] or e['tipo'] not in PORTAS:
            return self.nome(eid)
        alvos, pilha, vistos = [], [eid], set()
        while pilha:
            x = pilha.pop(0)
            if x in vistos or x not in self.elementos:
                continue
            vistos.add(x)
            y = self.elementos[x]
            if y['tipo'] in PORTAS and not y['nome']:
                pilha.extend(f['para'] for f in self.saidas[x])
            else:
                alvos.append(self.nome(x))
        junta = ' + ' if e['tipo'] == 'paralelo' else ' / '
        return junta.join(alvos) or self.nome(eid)

    def nome_papel(self, pid):
        if pid is None:
            return '(sem responsável)'
        p = self.papeis.get(pid)
        return p['nome'] if p else pid

    def nome_sistema(self, sid):
        s = self.sistemas.get(sid)
        return s['nome'] if s else sid

    def de_tipo(self, *tipos):
        return [e for e in self.elementos.values() if e['tipo'] in tipos]

    def raias(self):
        """Papéis na ordem da carta, só os usados, mais a raia dos elementos sem papel (se houver)."""
        usados = [e['papel'] for e in self.elementos.values()]
        ordem = [pid for pid in self.papeis if pid in usados]
        ordem += [p for p in dict.fromkeys(usados) if p and p not in self.papeis]
        if any(p is None for p in usados):
            ordem.append(SEM_PAPEL)
        return ordem

    def raia_de(self, eid):
        return self.elementos[eid]['papel'] or SEM_PAPEL

    def alcancaveis(self, inicio_ids, para_tras=False):
        vistos, pilha = set(), list(inicio_ids)
        while pilha:
            x = pilha.pop()
            if x in vistos or x not in self.elementos:
                continue
            vistos.add(x)
            lig = self.entradas[x] if para_tras else self.saidas[x]
            pilha.extend(f['de'] if para_tras else f['para'] for f in lig)
        return vistos

    def arestas_de_volta(self):
        """Fluxos que voltam para trás (laços de retrabalho), por busca em profundidade a partir dos inícios."""
        cor, volta = {}, set()
        raizes = [e['id'] for e in self.de_tipo('inicio')] + list(self.elementos)
        for r in raizes:
            if r in cor:
                continue
            pilha = [(r, iter(self.saidas[r]))]
            cor[r] = 1
            while pilha:
                no, it = pilha[-1]
                f = next(it, None)
                if f is None:
                    cor[no] = 2
                    pilha.pop()
                    continue
                d = f['para']
                if d not in self.elementos:
                    continue
                if cor.get(d) == 1:
                    volta.add(f['id'])
                elif d not in cor:
                    cor[d] = 1
                    pilha.append((d, iter(self.saidas[d])))
        return volta

    def atividades(self):
        return self.de_tipo(*NOS_DE_TRABALHO)

    def cenario(self):
        return self.processo.get('cenario') or 'as-is'

    def titulo(self):
        p = self.processo
        cod = f'{p["codigo"]} · ' if p.get('codigo') else ''
        return f'{cod}{p.get("nome") or "Processo sem nome"}'


def carregar(caminho):
    dados = ler_json(caminho)
    if not isinstance(dados, dict):
        from .util import ErroDeUso
        raise ErroDeUso(f'{caminho}: a carta é um objeto JSON (começa com {{)')
    return Carta(dados, caminho)


def esqueleto(nome, codigo='', dono='', cenario='as-is'):
    """A carta vazia de um processo novo: os campos na ordem em que a entrevista os preenche."""
    return {
        'formato': FORMATO,
        'processo': {
            'codigo': codigo, 'nome': nome, 'cenario': cenario, 'versao': '0.1',
            'objetivo': '', 'dono': dono, 'area': '', 'macroprocesso': '', 'nivel': 'processo',
            'gatilho': '', 'resultado': '', 'frequencia': '', 'volume': '', 'prazo_informado': '',
            'escopo': {'inicio': '', 'fim': '', 'inclui': [], 'nao_inclui': []},
            'normas': [], 'premissas': [],
        },
        'participantes': [],
        'sipoc': {'fornecedores': [], 'entradas': [], 'saidas': [], 'clientes': []},
        'papeis': [],
        'sistemas': [],
        'elementos': [],
        'regras': [],
        'indicadores': [],
        'dores': [],
        'riscos': [],
        'melhorias': [],
        'glossario': [],
        'pendencias': [],
        'historico': [],
    }
