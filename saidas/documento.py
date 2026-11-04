"""
O documento de mapeamento do processo: HTML (abre em qualquer navegador e imprime em PDF), Markdown (para
wiki, Confluence, Git) e a planilha das atividades (CSV que abre direto no Excel em português).

Seções (referencias/documento.md):
     1 ficha do processo        7 matriz RACI
     2 escopo                   8 indicadores
     3 SIPOC                    9 análise (tempos, valor, passagens, oportunidades)
     4 fluxograma              10 dores, melhorias, riscos e controles
     5 descrição das atividades 11 glossário, normas, pendências
     6 decisões e regras       12 participantes, histórico e aprovação

Sem o aceite do dono (ou com a carta mudada depois dele) o documento sai marcado RASCUNHO.
"""

import html

from carta.analise import analisar, pct_txt
from carta.aprovacao import situacao_aprovacao
from carta.gestao import nivel_risco, plano, riscos_ordenados
from carta.lacunas import levantar
from carta.layout import calcular, numerar
from carta.modelo import NOS_DE_TRABALHO, PORTAS, VALORES
from carta.util import como_lista, formatar_minutos, numero_br
from carta.validacao import validar

from . import svg as svg_saida




LEGENDA = ('círculo fino = início · círculo grosso = fim · círculo grosso com disco cheio = fim que encerra tudo · '
           'círculo duplo = espera, prazo ou mensagem · círculo duplo preso na atividade = borda (exceção durante '
           'a atividade; tracejado = não interrompe) · retângulo = atividade (número no topo, sistema embaixo) · '
           'retângulo com [+] = subprocesso · losango = decisão (a pergunta ao lado) · losango com + = caminhos '
           'em paralelo · losango com círculo = um ou mais caminhos (OU) · losango com pentágono = corrida (o que '
           'vier primeiro) · linha tracejada = retrabalho (volta).')

def caminho_txt(c, e, f):
    """Uma saída de decisão em texto: "Sim → Pagar (80%)"; na corrida, "se vier primeiro: Resposta recebida"."""
    if e['tipo'] == 'corrida' and not f['rotulo']:
        txt = f'se vier primeiro: {c.destino_legivel(f["para"])}'
    else:
        txt = f'{f["rotulo"] or "—"} → {c.destino_legivel(f["para"])}'
    return txt + (f' ({f["percentual"]:g}%)' if f['percentual'] is not None else '')

def _e(x):
    return html.escape(str(x if x is not None else ''))


def _lista(v, sep=', '):
    return sep.join(str(x) for x in como_lista(v))


def comparacao_asis(c):
    """No TO-BE: (nome do AS-IS, mudanças em texto, [(medida, antes, depois, diferença)]) contra a carta AS-IS
    de onde ele saiu (processo.base_as_is); None se não é TO-BE ou o AS-IS não está na pasta."""
    import os
    from carta.aprovacao import comparar
    from carta.modelo import carregar
    base = c.processo.get('base_as_is')
    if c.cenario() != 'to-be' or not base or not c.caminho:
        return None
    arq = os.path.join(os.path.dirname(os.path.abspath(c.caminho)), str(base))
    if not os.path.exists(arq):
        return None
    try:
        asis = carregar(arq)
        linhas, numeros = comparar(asis, c)
    except Exception:
        return None
    tabela = []
    for rot, x, y in numeros:
        if isinstance(x, float) or isinstance(y, float):
            dif = (y or 0) - (x or 0)
            sinal = '+' if dif > 0 else '-' if dif < 0 else ''
            tabela.append((rot, formatar_minutos(x), formatar_minutos(y),
                           sinal + formatar_minutos(abs(dif)) if dif else '='))
        else:
            tabela.append((rot, str(x), str(y), f'{y - x:+d}' if y != x else '='))
    return base, [t for _, t in linhas], tabela


def aceites(c):
    """Todos os aceites do dono, do mais antigo ao atual: (versão, quando, por, observação)."""
    _, reg = situacao_aprovacao(c)
    if not reg:
        return []
    return [(x.get('versao') or '—', x.get('quando'), x.get('por'), x.get('observacao') or '')
            for x in (reg.get('anteriores') or []) + [reg]]


def _status(c):
    estado, reg = situacao_aprovacao(c)
    if estado == 'aprovada':
        return 'aprovada', f'Aprovado por {reg["por"]} em {reg["quando"]}'
    if estado == 'mudou':
        return 'rascunho', f'RASCUNHO: a carta mudou depois do aceite de {reg["por"]} em {reg["quando"]}'
    return 'rascunho', 'RASCUNHO: ainda sem aceite do dono do processo'


def montar(c):
    """Os dados do documento, uma vez só, para o HTML e o Markdown."""
    lay = calcular(c)
    nums = numerar(c, lay)
    an = analisar(c)
    ativ = sorted(c.atividades(), key=lambda e: nums.get(e['id'], '99'))
    status, texto_status = _status(c)
    return {'lay': lay, 'nums': nums, 'an': an, 'ativ': ativ, 'status': status, 'texto_status': texto_status,
            'achados': validar(c), 'lacunas': levantar(c)}


def _linhas_atividades(c, d):
    for e in d['ativ']:
        tempo = []
        if e['execucao'] is not None:
            tempo.append(f'exec. {formatar_minutos(e["execucao"])}')
        if e['espera']:
            tempo.append(f'espera {formatar_minutos(e["espera"])}')
        yield {
            'n': d['nums'].get(e['id'], ''), 'id': e['id'], 'atividade': e['nome'],
            'responsavel': c.nome_papel(e['papel']),
            'sistema': ', '.join(c.nome_sistema(s) for s in e['sistema']) or ('manual' if e['sistema_respondido']
                                                                              else '—'),
            'entradas': _lista(e['entradas']), 'saidas': _lista(e['saidas']), 'regras': ', '.join(e['regras']),
            'tempo': ' · '.join(tempo) or '—', 'valor': e['valor'] or '—', 'descricao': e['descricao'],
            'como': e['como'], 'excecoes': _excecoes_de_borda(c, e) + list(e['excecoes']),
            'documentos': list(e['documentos']) + ([f'detalhe do subprocesso: {e["bruto"]["detalhe"]}']
                                                   if e['bruto'].get('detalhe') else []),
            'segue': [(f['rotulo'], c.destino_legivel(f["para"])) for f in c.saidas[e['id']] if not f['borda']],
        }


def _excecoes_de_borda(c, e):
    """As bordas da atividade em uma frase cada: "Se prazo de 48h estourado (10% dos casos): segue para X"."""
    out = []
    for f in c.saidas[e['id']]:
        if not f['borda']:
            continue
        b = c.elementos[f['para']]
        detalhe = []
        if b['tempo_texto'].get('espera'):
            detalhe.append(f'prazo {b["tempo_texto"]["espera"]}')
        if f['percentual'] is not None:
            detalhe.append(f'{f["percentual"]:g}% dos casos')
        if not b['interrompe']:
            detalhe.append('a atividade continua')
        destinos = ', '.join(c.destino_legivel(g['para']) for g in c.saidas[b['id']]) or '—'
        out.append(f'Se {b["nome"] or "exceção"}' + (f' ({"; ".join(detalhe)})' if detalhe else '') +
                   f': segue para {destinos}')
    return out


def _sipoc_processo(c, d):
    """A coluna P do SIPOC: as atividades do caminho feliz, no máximo 7 (o SIPOC é visão de alto nível)."""
    trabalho = [x for x in d['an']['caminho_feliz'] if c.elementos[x]['tipo'] in NOS_DE_TRABALHO]
    # o que o externo faz já aparece em fornecedores e clientes; a primeira e a última atividade sempre entram
    internos = [x for x in trabalho if (c.papeis.get(c.elementos[x]['papel']) or {}).get('tipo') != 'externo']
    passos = [c.nome(x) for x in (internos or trabalho)]
    if len(passos) > 7:
        passos = [passos[round(i * (len(passos) - 1) / 6)] for i in range(7)]
    return passos


def _raci(c, d):
    papeis = [r['id'] for r in d['lay'].raias if r['id'] in c.papeis]
    extra = [p for p in c.papeis if p not in papeis and any(p in v for x in d['an']['raci'].values()
                                                             for v in x.values())]
    papeis += extra
    linhas = []
    for e in d['ativ']:
        r = d['an']['raci'][e['id']]
        cel = []
        for p in papeis:
            letras = ''.join(k for k in ('R', 'A', 'C', 'I') if p in r.get(k, []))
            cel.append(letras)
        linhas.append((d['nums'].get(e['id'], ''), e['nome'], cel))
    return [c.nome_papel(p) for p in papeis], linhas


# ====================================================================== HTML
CSS = """
:root{--tx:#1d2733;--sv:#5b6878;--ln:#d5dce6;--fd:#f6f8fb;--ac:#2f4a6d;--ok:#2e7d32;--al:#a86b00;--er:#b3261e}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--tx);font:14px/1.5 "Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--ac)}
h3{font-size:15px;margin:20px 0 6px}
.sub{color:var(--sv);margin:0 0 14px}
.selo{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600}
.selo.aprovada{background:#e6f4ea;color:var(--ok)}.selo.rascunho{background:#fdecea;color:var(--er)}
table{border-collapse:collapse;width:100%;margin:8px 0 14px;font-size:13px}
th,td{border:1px solid var(--ln);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--fd);font-weight:600}
.ficha th{width:200px}
.sipoc td{width:20%}
.raci td,.raci th{text-align:center}.raci td:nth-child(2),.raci th:nth-child(2){text-align:left}
.fluxo{overflow-x:auto;border:1px solid var(--ln);border-radius:8px;padding:6px;background:#fff;margin:0 0 10px}
.fluxo svg{max-width:none;height:auto}.fluxo.parte svg{width:100%;max-width:100%}
.nums{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:10px 0}
.num{border:1px solid var(--ln);border-radius:8px;padding:10px 12px}
.num b{display:block;font-size:22px}.num span{color:var(--sv);font-size:12px}
.tag{display:inline-block;white-space:nowrap;padding:1px 7px;border-radius:9px;font-size:11px;font-weight:600;border:1px solid}
.VA{color:var(--ok)}.NAV-N{color:var(--al)}.NAV{color:var(--er)}
.det{border-left:3px solid var(--ln);padding:2px 0 2px 12px;margin:10px 0}
.det p{margin:4px 0}.muted{color:var(--sv)}
.aviso{background:#fff8e1;border:1px solid #f0d58c;border-radius:8px;padding:8px 12px;margin:10px 0}
nav.indice{columns:2;font-size:13px;margin:10px 0 0}nav.indice a{color:var(--ac);text-decoration:none}
ol,ul{margin:4px 0 10px;padding-left:22px}
@media (max-width:700px){nav.indice{columns:1}.ficha th{width:auto}}
@media print{main{max-width:none;padding:0}h2{break-after:avoid}table,.det{break-inside:avoid}
 .fluxo{overflow:visible;border:0;break-inside:avoid;break-after:page}.fluxo svg{max-width:100%;max-height:170mm}
 .fluxo.em-pe{page:em_pe}.fluxo.em-pe svg{max-height:255mm}
 @page{size:A4 landscape;margin:12mm}@page em_pe{size:A4 portrait;margin:12mm}}
"""


def _tabela(cab, linhas, classe=''):
    t = [f'<table class="{classe}"><thead><tr>' + ''.join(f'<th>{_e(x)}</th>' for x in cab) + '</tr></thead><tbody>']
    for ln in linhas:
        t.append('<tr>' + ''.join(f'<td>{x}</td>' for x in ln) + '</tr>')
    t.append('</tbody></table>')
    return ''.join(t)


def html_documento(c, d=None):
    d = d or montar(c)
    p = c.processo
    an = d['an']
    H = [f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width,initial-scale=1">'
         f'<title>{_e(c.titulo())}</title><style>{CSS}</style></head><body><main>']
    H.append(f'<p class="sub">Mapeamento de processo · {_e(c.cenario().upper())} · versão {_e(p.get("versao", "—"))}'
             f'</p><h1>{_e(c.titulo())}</h1>')
    H.append(f'<span class="selo {d["status"]}">{_e(d["texto_status"])}</span>')
    secoes = ['Ficha do processo', 'Escopo', 'SIPOC', 'Fluxograma', 'Descrição das atividades',
              'Decisões e regras de negócio', 'Matriz RACI', 'Indicadores', 'Análise do processo',
              'Dores, melhorias e riscos', 'Glossário, normas e pendências', 'Participantes e histórico']
    H.append('<nav class="indice"><ol>' + ''.join(f'<li><a href="#s{i}">{s}</a></li>' for i, s in
                                                 enumerate(secoes, 1)) + '</ol></nav>')
    erros = [a for a in d['achados'] if a.nivel == 'erro']
    if erros:
        H.append(f'<div class="aviso"><b>{len(erros)} erro(s) de fluxo</b> ainda sem correção: o desenho pode estar '
                 'incompleto. ' + '; '.join(_e(a.texto) for a in erros[:5]) + '</div>')

    def secao(i, extra=''):
        H.append(f'<h2 id="s{i}">{i}. {secoes[i - 1]}</h2>{extra}')

    # 1 ficha
    secao(1)
    ficha = [('Código', p.get('codigo')), ('Processo', p.get('nome')), ('Macroprocesso', p.get('macroprocesso')),
             ('Nível', p.get('nivel')), ('Área', p.get('area')), ('Dono do processo', p.get('dono')),
             ('Objetivo', p.get('objetivo')), ('Gatilho', p.get('gatilho')), ('Resultado esperado', p.get('resultado')),
             ('Frequência / volume', ' · '.join(x for x in (p.get('frequencia'), p.get('volume')) if x)),
             ('Prazo (informado)', p.get('prazo_informado')),
             ('Cenário', c.cenario().upper()), ('Versão', p.get('versao'))]
    H.append('<table class="ficha"><tbody>' + ''.join(
        f'<tr><th>{_e(k)}</th><td>{_e(v) if v else "<span class=muted>a definir</span>"}</td></tr>'
        for k, v in ficha) + '</tbody></table>')
    # 2 escopo
    secao(2)
    esc = p.get('escopo') or {}
    H.append(_tabela(['Começa em', 'Termina em'], [[_e(esc.get('inicio') or '—'), _e(esc.get('fim') or '—')]]))
    if esc.get('inclui'):
        H.append('<h3>Inclui</h3><ul>' + ''.join(f'<li>{_e(x)}</li>' for x in como_lista(esc['inclui'])) + '</ul>')
    if esc.get('nao_inclui'):
        H.append('<h3>Não inclui</h3><ul>' + ''.join(f'<li>{_e(x)}</li>' for x in como_lista(esc['nao_inclui']))
                 + '</ul>')
    if p.get('premissas'):
        H.append('<h3>Premissas</h3><ul>' + ''.join(f'<li>{_e(x)}</li>' for x in como_lista(p['premissas'])) +
                 '</ul>')
    # 3 SIPOC
    secao(3)
    s = c.sipoc
    cols = [como_lista(s.get('fornecedores')), como_lista(s.get('entradas')), _sipoc_processo(c, d),
            como_lista(s.get('saidas')), como_lista(s.get('clientes'))]
    H.append(_tabela(['Fornecedores (S)', 'Entradas (I)', 'Processo (P)', 'Saídas (O)', 'Clientes (C)'],
                     [['<ul>' + ''.join(f'<li>{_e(x)}</li>' for x in col) + '</ul>' if col else
                       '<span class=muted>a definir</span>' for col in cols]], 'sipoc'))
    # 4 fluxograma
    secao(4)
    cores = any(e['valor'] for e in d['ativ'])
    cortes, retratos = svg_saida.faixas_impressao(c, d['lay'])   # o mesmo corte (e a mesma página) do Word
    if len(cortes) > 1:
        H.append(f'<p class="muted">O mapa tem {svg_saida.colunas_total(d["lay"])} colunas: aparece em '
                 f'{len(cortes)} partes para caber na página (a última coluna de uma parte repete na seguinte). '
                 'O desenho inteiro está no arquivo .svg.</p>')
    for i, faixa in enumerate(cortes, 1):
        parte = (i, len(cortes)) if len(cortes) > 1 else None
        em_pe = ' em-pe' if parte and retratos[i - 1] else ''
        H.append(f'<div class="fluxo{" parte" if parte else ""}{em_pe}">' + svg_saida.desenhar(c, d['lay'], cores_valor=cores, titulo=bool(parte),
                                                           faixa=faixa if parte else None, parte=parte) + '</div>')
    H.append('<p class="muted">Legenda: ' + _e(LEGENDA) + ' Passe o mouse sobre um elemento para ver o '
             'detalhe.</p>')
    # 5 atividades
    secao(5)
    linhas = list(_linhas_atividades(c, d))
    H.append(_tabela(['Nº', 'Atividade', 'Responsável', 'Sistema', 'Entradas', 'Saídas', 'Regras', 'Tempo', 'Valor'],
                     [[_e(x['n']), _e(x['atividade']), _e(x['responsavel']), _e(x['sistema']), _e(x['entradas']),
                       _e(x['saidas']), _e(x['regras']), _e(x['tempo']),
                       f'<span class="tag {_e(x["valor"])}">{_e(x["valor"])}</span>' if x['valor'] != '—' else '—']
                      for x in linhas]))
    for x in linhas:
        if not (x['descricao'] or x['como'] or x['excecoes'] or x['documentos']):
            continue
        H.append(f'<div class="det"><b>{_e(x["n"])} · {_e(x["atividade"])}</b>')
        if x['descricao']:
            H.append(f'<p>{_e(x["descricao"])}</p>')
        if x['como']:
            H.append('<p class="muted">Como fazer:</p><ol>' + ''.join(f'<li>{_e(y)}</li>' for y in x['como']) +
                     '</ol>')
        if x['excecoes']:
            H.append('<p class="muted">Exceções:</p><ul>' + ''.join(f'<li>{_e(y)}</li>' for y in x['excecoes']) +
                     '</ul>')
        if x['documentos']:
            H.append(f'<p class="muted">Documentos e modelos: {_e(_lista(x["documentos"]))}</p>')
        H.append('</div>')
    # 6 decisões e regras
    secao(6)
    decs = c.de_tipo('decisao', 'inclusivo', 'corrida')
    if decs:
        H.append(_tabela(['Decisão', 'Quem decide', 'Caminhos', 'Regras'],
                         [[_e(e['nome']), _e(c.nome_papel(e['papel'])),
                           '<br>'.join(_e(caminho_txt(c, e, f)) for f in c.saidas[e['id']]),
                           _e(', '.join(e['regras']) or '—')] for e in decs if len(c.saidas[e['id']]) > 1]))
    if c.regras:
        H.append(_tabela(['Regra', 'Texto', 'Fonte', 'Onde se aplica'],
                         [[_e(rid), _e(r.get('texto', '')), _e(r.get('fonte', '')),
                           _e(', '.join(c.nome(e['id']) for e in c.elementos.values() if rid in e['regras']))]
                          for rid, r in c.regras.items()]))
    elif not decs:
        H.append('<p class="muted">Nenhuma decisão ou regra registrada.</p>')
    # 7 RACI
    secao(7, '<p class="muted">R = executa · A = responde pelo resultado (aprova) · C = é consultado antes · '
             'I = é informado depois. Uma atividade tem um só A.</p>')
    cab, linhas_raci = _raci(c, d)
    H.append(_tabela(['Nº', 'Atividade'] + cab, [[_e(n), _e(nome)] + [_e(x) for x in cel]
                                                 for n, nome, cel in linhas_raci], 'raci'))
    sem_a = [e for e in d['ativ'] if not e['raci']['A']]
    if sem_a:
        H.append(f'<p class="muted">{len(sem_a)} atividade(s) sem "A" declarado: a carta ainda não diz quem '
                 'responde pelo resultado delas (pendência para o dono do processo).</p>')
    # 8 indicadores
    secao(8)
    if c.indicadores:
        H.append(_tabela(['Indicador', 'Fórmula', 'Hoje (linha de base)', 'Meta', 'Polaridade', 'Periodicidade',
                          'Fonte', 'Dono'],
                         [[_e(i.get('nome')), _e(i.get('formula')), _e(i.get('atual') or 'a medir'), _e(i.get('meta')),
                           _e(i.get('polaridade')), _e(i.get('periodicidade')), _e(i.get('fonte')), _e(i.get('dono'))]
                          for i in c.indicadores]))
    else:
        H.append('<p class="muted">Nenhum indicador definido ainda.</p>')
    # 9 análise
    secao(9)
    t = an['tempos']
    efic = pct_txt(t)
    for a in an.get('alertas') or []:
        H.append(f'<div class="aviso">{_e(a[0].upper() + a[1:])}.</div>')
    if not t['execucao'] and not t['espera']:
        H.append('<div class="aviso">Ainda não há tempo por atividade: lead time e eficiência não são calculados. '
                 + (f'Prazo informado pela pessoa: <b>{_e(p.get("prazo_informado"))}</b>.'
                    if p.get('prazo_informado') else '') + '</div>')
    cartoes = [(formatar_minutos(t['lead_time']), 'lead time do caminho feliz'),
               (formatar_minutos(t['lead_time_esperado']), 'lead time esperado (com exceções, retrabalho e todos os desfechos)'),
               ] + ([(' / '.join(formatar_minutos(t['percentis'][k]) for k in ('p50', 'p80', 'p90')),
                      'prazo em que terminam 50% / 80% / 90% dos casos')]
                    if t.get('percentis') else []) + [
               (formatar_minutos(t['execucao']), 'esforço (tempo de execução)'),
               (efic, 'eficiência do ciclo (execução ÷ lead time)'),
               (str(len(an['passagens_caminho'])), 'passagens de bastão no caso típico'),
               (str(len(an['retrabalho'])), 'laços de retrabalho')]
    H.append('<div class="nums">' + ''.join(f'<div class="num"><b>{_e(v)}</b><span>{_e(r)}</span></div>'
                                            for v, r in cartoes) + '</div>')
    passos = [x for x in an['caminho_feliz'] if c.elementos[x]['tipo'] not in PORTAS]
    H.append('<h3>Caminho feliz (o caso mais comum)</h3><p>' + ' → '.join(
        f'<b>{_e(d["nums"][x])}</b> {_e(c.nome(x))}' if x in d['nums'] else _e(c.nome(x)) for x in passos) + '</p>')
    if an['paralelos']:
        H.append('<p class="muted">Em paralelo, no mesmo caso: ' + _e(', '.join(
            c.nome(x) for x in an['paralelos'] if c.elementos[x]['tipo'] not in ('paralelo',))) + '</p>')
    if not an['caminho_completo']:
        H.append('<div class="aviso">O caminho feliz não chegou a um fim: confira o fluxo e os percentuais.</div>')
    if t['decisoes_sem_percentual'] and t['lead_time_esperado'] is not None:
        H.append(f'<p class="muted">{len(t["decisoes_sem_percentual"])} decisão(ões) sem percentual: no lead time '
                 'esperado, os caminhos delas contam com peso igual.</p>')
    if an['passagens_caminho']:
        H.append('<p><b>Passagens de bastão no caso típico:</b> ' + _e('; '.join(
            f'{c.nome_papel(c.raia_de(a))} → {c.nome_papel(c.raia_de(b))} ({c.nome(b)})'
            for a, b in an['passagens_caminho'])) + '</p>')
    if an['gargalos']:
        H.append('<p><b>Maiores esperas:</b> ' + _e('; '.join(f'{c.nome(eid)}: {formatar_minutos(m)}'
                                                             for eid, m in an['gargalos'])) + '</p>')
    cg = an.get('carga')
    if cg:
        H.append('<h3>Carga de trabalho (capacidade)</h3>' + _tabela(
            ['Papel', 'Horas por mês', 'Pessoas equivalentes (160 h/mês)'],
            [[_e(c.nome_papel(p)), _e(numero_br(h)), _e(numero_br(n, 1))] for p, h, n in cg['por_papel']] +
            [['<b>Total</b>', f'<b>{_e(numero_br(cg["horas_mes"]))}</b>', f'<b>{_e(numero_br(cg["pessoas"], 1))}</b>']]))
        H.append(f'<p class="muted">{_e(numero_br(cg["casos_mes"]))} casos por mês (do volume informado) × quantas vezes '
                 'cada atividade roda por caso × tempo de execução. Jornada cheia, sem descontar pausas e reuniões: é '
                 'o mínimo de gente.' + (f' {cg["sem_tempo"]} atividade(s) sem tempo ficam de fora.' if cg['sem_tempo']
                                          else '') + '</p>')
    if t.get('espera_sem_tempo'):
        H.append(f'<p class="muted">Sem tempo de resposta: {_e(", ".join(c.nome(x) for x in t["espera_sem_tempo"]))} '
                 '(a espera por quem está de fora conta zero: o lead time real é maior).</p>')
    if t['sem_tempo']:
        H.append(f'<p class="muted">Sem tempo informado: {_e(", ".join(c.nome(x) for x in t["sem_tempo"]))} '
                 '(os totais estão subestimados).</p>')
    v = an['valor']
    total = sum(x['atividades'] for x in v.values()) or 1
    H.append(_tabela(['Classificação', 'Atividades', '%', 'Tempo de execução'],
                     [[(f'<span class="tag {k}">{k}</span> {_e(VALORES[k])}' if k in VALORES else
                        'Sem classificação'),
                       str(v[k]['atividades']), f'{v[k]["atividades"] / total:.0%}',
                       _e(formatar_minutos(v[k]['execucao']))] for k in ('VA', 'NAV-N', 'NAV', 'sem')
                      if v[k]['atividades']]))
    H.append('<p class="muted">Os tempos são estimativas da entrevista, não medição.</p>')
    if an['oportunidades']:
        H.append('<h3>Oportunidades que o mapa mostra</h3>')
        H.append(_tabela(['#', 'Desperdício', 'Oportunidade'],
                         [[str(i), _e(o['desperdicio']), _e(o['texto'])] for i, o in
                          enumerate(an['oportunidades'], 1)]))
    # 10 dores, melhorias, riscos
    cmp_ = comparacao_asis(c)
    if cmp_:
        base, mudancas, tabela = cmp_
        H.append(f'<h3>AS-IS x TO-BE (contra {_e(base)})</h3>' + _tabela(
            ['Medida', 'AS-IS', 'TO-BE', 'Diferença'], [[_e(x) for x in t] for t in tabela]))
        if mudancas:
            H.append('<p><b>O que muda no fluxo:</b></p><ul>' + ''.join(f'<li>{_e(m)}</li>' for m in mudancas)
                     + '</ul>')
    secao(10)
    if c.dores:
        H.append('<h3>Dores</h3>' + _tabela(['Id', 'Dor', 'Onde', 'Impacto', 'Frequência'],
                                            [[_e(x.get('id')), _e(x.get('descricao')),
                                              _e(', '.join(c.nome(r) for r in x.get('elementos') or [])),
                                              _e(x.get('impacto')), _e(x.get('frequencia'))] for x in c.dores]))
    if c.melhorias:
        H.append('<h3>Plano de ação (melhorias)</h3>' + _tabela(
            ['Id', 'Ação', 'Resolve', 'Impacto', 'Esforço', 'Responsável', 'Prazo', 'Situação'],
            [[_e(x['id']), _e(x['acao']), _e(x['resolve']), _e(x['impacto']), _e(x['esforco']), _e(x['responsavel']),
              _e(x['prazo']), _e(x['situacao'])] for x in plano(c)]))
    if c.riscos:
        H.append('<h3>Riscos e controles</h3>' + _tabela(
            ['Id', 'Risco', 'Onde', 'Probabilidade × impacto', 'Nível', 'Controle', 'Tipo de controle'],
            [[_e(x.get('id')), _e(x.get('descricao')), _e(', '.join(c.nome(r) for r in x.get('elementos') or [])),
              _e(f'{x.get("probabilidade") or "?"} × {x.get("impacto") or "?"}'), _e(nivel_risco(x)[1]),
              _e(x.get('controle') or 'SEM CONTROLE'), _e(x.get('tipo_controle'))] for x in riscos_ordenados(c)]))
    if not (c.dores or c.melhorias or c.riscos):
        H.append('<p class="muted">Nada registrado ainda.</p>')
    # 11 glossário, normas, pendências
    secao(11)
    if c.glossario:
        H.append('<h3>Glossário</h3>' + _tabela(['Termo', 'Definição'], [[_e(g.get('termo')), _e(g.get('definicao'))]
                                                                         for g in c.glossario]))
    if p.get('normas'):
        H.append('<h3>Normas e referências</h3><ul>' + ''.join(f'<li>{_e(x)}</li>' for x in como_lista(p['normas']))
                 + '</ul>')
    if c.sistemas:
        H.append('<h3>Sistemas</h3><ul>' + ''.join(f'<li><b>{_e(s["nome"])}</b> {_e(s["descricao"])}</li>'
                                                   for s in c.sistemas.values()) + '</ul>')
    pend = [(x.get('pergunta') or x.get('descricao', ''), x.get('para', '')) for x in c.pendencias]
    if pend:
        H.append('<h3>Pendências</h3>' + _tabela(['Pendência', 'Com quem'], [[_e(a), _e(b)] for a, b in pend]))
    abertas = [q for q in d['lacunas'] if q.prioridade in (1, 3)]
    if abertas:
        H.append('<h3>Ainda sem resposta na carta</h3><ul>' + ''.join(f'<li>{_e(q.texto)}</li>' for q in abertas)
                 + '</ul>')
    # 12 participantes e histórico
    secao(12)
    if c.participantes:
        H.append(_tabela(['Nome', 'Papel', 'Data'], [[_e(x.get('nome')), _e(x.get('papel')), _e(x.get('data'))]
                                                     for x in c.participantes]))
    if c.historico:
        H.append(_tabela(['Versão', 'Data', 'Autor', 'Mudança'],
                         [[_e(x.get('versao')), _e(x.get('data')), _e(x.get('autor')), _e(x.get('mudanca'))]
                          for x in c.historico]))
    if aceites(c):
        H.append('<h3>Aceites do dono do processo</h3>' + _tabela(['Versão', 'Quando', 'Por', 'Observação'],
                                                                  [[_e(x) for x in a] for a in aceites(c)]))
    H.append(f'<p><span class="selo {d["status"]}">{_e(d["texto_status"])}</span></p>')
    H.append('<p class="muted">Gerado pelo Senku a partir do carta.json. Para mudar, edite a carta e gere de novo: '
             'não edite este arquivo.</p></main></body></html>')
    return '\n'.join(H)


# ====================================================================== Markdown
def _md_tab(cab, linhas):
    def cel(x):
        return str(x if x not in (None, '') else '—').replace('|', '\\|').replace('\n', ' ')
    out = ['| ' + ' | '.join(cab) + ' |', '|' + '---|' * len(cab)]
    out += ['| ' + ' | '.join(cel(x) for x in ln) + ' |' for ln in linhas]
    return '\n'.join(out) + '\n'


def markdown_documento(c, d=None, arquivo_svg=None):
    from . import mermaid
    d = d or montar(c)
    p = c.processo
    an = d['an']
    M = [f'# {c.titulo()}', '', f'Mapeamento de processo · {c.cenario().upper()} · versão {p.get("versao", "—")}  ',
         f'**{d["texto_status"]}**', '', '## 1. Ficha do processo', '']
    M.append(_md_tab(['Campo', 'Valor'], [
        ('Dono do processo', p.get('dono')), ('Área', p.get('area')), ('Macroprocesso', p.get('macroprocesso')),
        ('Objetivo', p.get('objetivo')), ('Gatilho', p.get('gatilho')), ('Resultado', p.get('resultado')),
        ('Frequência / volume', ' · '.join(x for x in (p.get('frequencia'), p.get('volume')) if x))]))
    esc = p.get('escopo') or {}
    M += ['## 2. Escopo', '', f'- **Começa em:** {esc.get("inicio") or "—"}', f'- **Termina em:** {esc.get("fim") or "—"}']
    if esc.get('inclui'):
        M.append(f'- **Inclui:** {_lista(esc["inclui"], "; ")}')
    if esc.get('nao_inclui'):
        M.append(f'- **Não inclui:** {_lista(esc["nao_inclui"], "; ")}')
    s = c.sipoc
    M += ['', '## 3. SIPOC', '', _md_tab(['Fornecedores', 'Entradas', 'Processo', 'Saídas', 'Clientes'], [[
        _lista(s.get('fornecedores'), '<br>'), _lista(s.get('entradas'), '<br>'),
        '<br>'.join(_sipoc_processo(c, d)), _lista(s.get('saidas'), '<br>'), _lista(s.get('clientes'), '<br>')]])]
    M += ['## 4. Fluxograma', '']
    if arquivo_svg:
        M += [f'![Fluxograma]({arquivo_svg})', '']
    M += ['```mermaid', mermaid.gerar(c).rstrip(), '```', '']
    M += ['## 5. Descrição das atividades', '', _md_tab(
        ['Nº', 'Atividade', 'Responsável', 'Sistema', 'Entradas', 'Saídas', 'Regras', 'Tempo', 'Valor'],
        [[x['n'], x['atividade'], x['responsavel'], x['sistema'], x['entradas'], x['saidas'], x['regras'], x['tempo'],
          x['valor']] for x in _linhas_atividades(c, d)])]
    for x in _linhas_atividades(c, d):
        if x['descricao'] or x['como'] or x['excecoes']:
            M.append(f'**{x["n"]} · {x["atividade"]}**  ')
            if x['descricao']:
                M.append(x['descricao'] + '  ')
            M += [f'{i}. {y}' for i, y in enumerate(x['como'], 1)]
            M += [f'- Exceção: {y}' for y in x['excecoes']]
            M.append('')
    M += ['## 6. Decisões e regras de negócio', '']
    decs = [e for e in c.de_tipo('decisao', 'inclusivo', 'corrida') if len(c.saidas[e['id']]) > 1]
    if decs:
        M.append(_md_tab(['Decisão', 'Quem decide', 'Caminhos', 'Regras'], [
            [e['nome'], c.nome_papel(e['papel']),
             '<br>'.join(caminho_txt(c, e, f) for f in c.saidas[e['id']]),
             ', '.join(e['regras'])] for e in decs]))
    if c.regras:
        M.append(_md_tab(['Regra', 'Texto', 'Fonte'], [[rid, r.get('texto', ''), r.get('fonte', '')]
                                                       for rid, r in c.regras.items()]))
    cab, linhas_raci = _raci(c, d)
    M += ['## 7. Matriz RACI', '', _md_tab(['Nº', 'Atividade'] + cab, [[n, nome] + cel for n, nome, cel in linhas_raci])]
    M += ['## 8. Indicadores', '']
    M.append(_md_tab(['Indicador', 'Fórmula', 'Hoje (linha de base)', 'Meta', 'Polaridade', 'Periodicidade',
                      'Fonte', 'Dono'],
                     [[i.get('nome'), i.get('formula'), i.get('atual') or 'a medir', i.get('meta'), i.get('polaridade'),
                       i.get('periodicidade'), i.get('fonte'), i.get('dono')] for i in c.indicadores])
             if c.indicadores else '_Nenhum indicador definido._\n')
    t = an['tempos']
    efic = pct_txt(t)
    passos = [c.nome(x) for x in an['caminho_feliz'] if c.elementos[x]['tipo'] not in PORTAS]
    M += ['## 9. Análise do processo', '',
          f'- Caminho feliz (o caso mais comum): {" → ".join(passos)}',
          f'- Lead time do caminho feliz: **{formatar_minutos(t["lead_time"])}** (esforço '
          f'{formatar_minutos(t["execucao"])}, eficiência do ciclo {efic})',
          f'- Lead time esperado, com exceções, retrabalho e todos os desfechos (inclusive recusas): **{formatar_minutos(t["lead_time_esperado"])}**'
          + (f' · 50% dos casos até {formatar_minutos(t["percentis"]["p50"])}, 80% até '
             f'{formatar_minutos(t["percentis"]["p80"])}, 90% até {formatar_minutos(t["percentis"]["p90"])}'
             if t.get('percentis') else ''),
          f'- Passagens de bastão no caso típico: {len(an["passagens_caminho"])} · laços de retrabalho: '
          f'{len(an["retrabalho"])}',
          '- Os tempos são estimativas da entrevista, não medição.'] + (
          [f'- Sem tempo de resposta (a espera conta zero, o lead time real é maior): '
           f'{", ".join(c.nome(x) for x in t["espera_sem_tempo"])}'] if t.get('espera_sem_tempo') else []) + ['']
    cg = an.get('carga')
    if cg:
        M += ['### Carga de trabalho (capacidade)', '', _md_tab(
            ['Papel', 'Horas por mês', 'Pessoas equivalentes (160 h/mês)'],
            [[c.nome_papel(p_), numero_br(h), numero_br(n, 1)] for p_, h, n in cg['por_papel']] +
            [['**Total**', f'**{numero_br(cg["horas_mes"])}**', f'**{numero_br(cg["pessoas"], 1)}**']]),
            f'_{numero_br(cg["casos_mes"])} casos por mês × vezes que cada atividade roda × execução; jornada '
            'cheia, é o mínimo de gente._', '']
    M += ['### Oportunidades', '']
    M += [f'{i}. [{o["desperdicio"]}] {o["texto"]}' for i, o in enumerate(an['oportunidades'], 1)]
    cmp_ = comparacao_asis(c)
    if cmp_:
        M += ['', f'### AS-IS x TO-BE (contra {cmp_[0]})', '',
              _md_tab(['Medida', 'AS-IS', 'TO-BE', 'Diferença'], [list(t) for t in cmp_[2]])]
        M += [f'- {m}' for m in cmp_[1]]
    M += ['', '## 10. Dores, melhorias e riscos', '']
    if c.dores:
        M.append(_md_tab(['Id', 'Dor', 'Onde', 'Impacto'], [[x.get('id'), x.get('descricao'),
                                                              ', '.join(c.nome(r) for r in x.get('elementos') or []),
                                                              x.get('impacto')] for x in c.dores]))
    if c.melhorias:
        M.append(_md_tab(['Id', 'Ação', 'Resolve', 'Esforço', 'Responsável', 'Prazo', 'Situação'],
                         [[x['id'], x['acao'], x['resolve'], x['esforco'], x['responsavel'], x['prazo'], x['situacao']]
                          for x in plano(c)]))
    if c.riscos:
        M.append(_md_tab(['Id', 'Risco', 'Onde', 'Nível', 'Controle', 'Tipo'], [
            [x.get('id'), x.get('descricao'), ', '.join(c.nome(r) for r in x.get('elementos') or []),
             nivel_risco(x)[1], x.get('controle') or 'SEM CONTROLE', x.get('tipo_controle')]
            for x in riscos_ordenados(c)]))
    M += ['## 11. Glossário, normas e pendências', '']
    if c.glossario:
        M.append(_md_tab(['Termo', 'Definição'], [[g.get('termo'), g.get('definicao')] for g in c.glossario]))
    if como_lista(p.get('normas')):
        M += ['', '**Normas e referências**', '']
    M += [f'- {x}' for x in como_lista(p.get('normas'))]
    M += [f'- [ ] {x.get("pergunta") or x.get("descricao", "")}' for x in c.pendencias]
    abertas = [q for q in d['lacunas'] if q.prioridade in (1, 3)]
    if abertas:
        M += ['', '**Ainda sem resposta na carta:**', ''] + [f'- [ ] {q.texto}' for q in abertas]
    M += ['', '## 12. Participantes e histórico', '']
    if c.participantes:
        M.append(_md_tab(['Nome', 'Papel', 'Data'], [[x.get('nome'), x.get('papel'), x.get('data')]
                                                     for x in c.participantes]))
    if c.historico:
        M.append(_md_tab(['Versão', 'Data', 'Autor', 'Mudança'],
                         [[x.get('versao'), x.get('data'), x.get('autor'), x.get('mudanca')] for x in c.historico]))
    if aceites(c):
        M += ['', '**Aceites do dono do processo**', '',
              _md_tab(['Versão', 'Quando', 'Por', 'Observação'], [list(a) for a in aceites(c)])]
    M.append(f'_{d["texto_status"]}. Gerado pelo Senku a partir do carta.json._')
    return '\n'.join(M) + '\n'


# ====================================================================== planilha
def csv_atividades(c, d=None):
    """CSV com ; e BOM: o Excel em português abre com acento e coluna certos."""
    d = d or montar(c)
    cab = ['Nº', 'Id', 'Atividade', 'Responsável', 'Sistema', 'Entradas', 'Saídas', 'Regras', 'Tempo', 'Valor',
           'Descrição', 'Como fazer', 'Exceções', 'A (aprova)', 'C (consultado)', 'I (informado)', 'Segue para']

    def q(x):
        x = str(x if x is not None else '')
        if x[:1] in ('=', '+', '-', '@', '\t', '\r'):
            x = "'" + x                                  # o Excel não executa como fórmula
        return '"' + x.replace('"', '""') + '"' if any(ch in x for ch in ';"\n') else x
    linhas = [';'.join(cab)]
    for x in _linhas_atividades(c, d):
        segue = ' | '.join(f'{r}: {n}' if r else n for r, n in x['segue'])
        raci = c.elementos[x['id']]['raci']
        papeis = [', '.join(c.nome_papel(p) for p in raci.get(k, [])) for k in ('A', 'C', 'I')]
        linhas.append(';'.join(q(v) for v in (x['n'], x['id'], x['atividade'], x['responsavel'], x['sistema'],
                                              x['entradas'], x['saidas'], x['regras'], x['tempo'], x['valor'],
                                              x['descricao'], ' | '.join(x['como']), ' | '.join(x['excecoes']),
                                              *papeis, segue)))
    return '\r\n'.join(linhas) + '\r\n'
