"""Apoio comum: erro de uso, leitura de JSON, tempos e textos."""

import json
import os
import sys
import re
import unicodedata


class ErroDeUso(Exception):
    """Erro que a pessoa resolve (arquivo errado, JSON quebrado, opção que falta): sai sem traceback."""


def ler_json(caminho):
    if not os.path.exists(caminho):
        raise ErroDeUso(f'arquivo não encontrado: {caminho}')
    with open(caminho, 'rb') as f:
        bruto = f.read()
    try:
        texto = bruto.decode('utf-8-sig')
    except UnicodeDecodeError:
        # salvo em ANSI (Bloco de Notas antigo, Set-Content do PowerShell 5.1): lê como Windows-1252
        texto = bruto.decode('cp1252', errors='replace')
        print(f'! {caminho} não está em UTF-8: lido como ANSI (Windows-1252). Salve em UTF-8 para evitar '
              'acento trocado.', file=sys.stderr)
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        linhas = texto.splitlines()
        trecho = linhas[e.lineno - 1] if 0 < e.lineno <= len(linhas) else ''
        raise ErroDeUso(f'JSON quebrado em {caminho}, linha {e.lineno}, coluna {e.colno}: {e.msg}\n'
                        f'    {trecho.strip()}')


def gravar_json(caminho, dados):
    pasta = os.path.dirname(os.path.abspath(caminho))
    os.makedirs(pasta, exist_ok=True)
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write('\n')


def gravar_texto(caminho, texto, bom=False):
    pasta = os.path.dirname(os.path.abspath(caminho))
    os.makedirs(pasta, exist_ok=True)
    with open(caminho, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='\n') as f:
        f.write(texto)


def sem_acento(texto):
    n = unicodedata.normalize('NFKD', str(texto))
    return ''.join(c for c in n if not unicodedata.combining(c))


def slug(texto, maximo=40):
    s = re.sub(r'[^a-z0-9]+', '-', sem_acento(texto).lower()).strip('-')
    return s[:maximo].strip('-') or 'processo'


def como_lista(valor):
    if valor is None or valor == '':
        return []
    if isinstance(valor, (list, tuple)):
        return [v for v in valor if v not in (None, '')]
    return [valor]


# ---------------------------------------------------------------- tempos
# Uma unidade só para somar: minutos ÚTEIS (de expediente). "h" é hora de expediente, "d" é dia útil (8 h),
# "sem" é semana (5 dias úteis), "mes" são 20 dias úteis. Quem mede em tempo corrido escreve "dc" (dia
# corrido) ou "hc" (hora corrida): um dia corrido vale 5/7 de dia útil (a semana tem 7 dias e 5 úteis), então
# "3dc" e "2 d" dão quase o mesmo prazo, como na vida real.
DIA_UTIL = 480
DIA_CORRIDO = DIA_UTIL * 5 / 7
_UNIDADES = {
    'seg': 1 / 60, 's': 1 / 60, 'segundo': 1 / 60, 'segundos': 1 / 60,
    'min': 1, 'mins': 1, 'minuto': 1, 'minutos': 1, 'm': 1,
    'h': 60, 'hr': 60, 'hrs': 60, 'hs': 60, 'hora': 60, 'horas': 60, 'hora util': 60, 'horas uteis': 60,
    'hc': DIA_CORRIDO / 24, 'hora corrida': DIA_CORRIDO / 24, 'horas corridas': DIA_CORRIDO / 24,
    'd': DIA_UTIL, 'du': DIA_UTIL, 'dia': DIA_UTIL, 'dias': DIA_UTIL, 'dia util': DIA_UTIL, 'dias uteis': DIA_UTIL,
    'dc': DIA_CORRIDO, 'dia corrido': DIA_CORRIDO, 'dias corridos': DIA_CORRIDO,
    'sem': 5 * DIA_UTIL, 'semana': 5 * DIA_UTIL, 'semanas': 5 * DIA_UTIL,
    'mes': 20 * DIA_UTIL, 'meses': 20 * DIA_UTIL,
}
_TEMPO = re.compile(r'(\d+(?:[.,]\d+)?)\s*([a-z ]*)')


EXTENSO = {'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3, 'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7,
            'oito': 8, 'nove': 9, 'dez': 10, 'onze': 11, 'doze': 12, 'treze': 13, 'quatorze': 14, 'catorze': 14,
            'quinze': 15, 'dezesseis': 16, 'dezessete': 17, 'dezoito': 18, 'dezenove': 19, 'vinte': 20,
            'trinta': 30, 'quarenta': 40, 'cinquenta': 50, 'sessenta': 60, 'setenta': 70, 'oitenta': 80,
            'noventa': 90, 'cem': 100, 'cento': 100, 'duzentos': 200, 'duzentas': 200, 'trezentos': 300,
            'trezentas': 300, 'quatrocentos': 400, 'quatrocentas': 400, 'quinhentos': 500, 'quinhentas': 500,
            'seiscentos': 600, 'seiscentas': 600, 'setecentos': 700, 'setecentas': 700, 'oitocentos': 800,
            'oitocentas': 800, 'novecentos': 900, 'novecentas': 900}
_NUMEROS = EXTENSO


def _compor_extenso(t):
    """Junta número por extenso composto: "quarenta e cinco" -> "45", "cento e vinte" -> "120" (só quando o
    segundo é menor, então "2 e 3" fica como está)."""
    nomes = '|'.join(sorted(EXTENSO, key=len, reverse=True))
    padrao = re.compile(rf'\b({nomes})\s+e\s+({nomes})\b')
    anterior = None
    while anterior != t:
        anterior = t
        t = padrao.sub(lambda m: str(EXTENSO[m.group(1)] + EXTENSO[m.group(2)])
                       if EXTENSO[m.group(2)] < EXTENSO[m.group(1)] else m.group(0), t)
        t = re.sub(rf'\b(\d+)\s+e\s+({nomes})\b', lambda m: str(int(m.group(1)) + EXTENSO[m.group(2)])
                   if EXTENSO[m.group(2)] < int(m.group(1)) and int(m.group(1)) % 10 == 0 else m.group(0), t)
    return t


def _normalizar_tempo(texto):
    t = sem_acento(str(texto)).lower().strip().rstrip('.')
    t = t.replace('–', '-').replace('—', '-')
    # duração ISO 8601, como vem de modelador ("PT2H", "P3D", "P1DT4H"): é tempo de relógio
    iso = re.fullmatch(r'p(?:(\d+)d)?(?:t(?:(\d+)h)?(?:(\d+)m)?)?', t)
    if iso and any(iso.groups()):
        d, h, m = (int(x or 0) for x in iso.groups())
        total_h = d * 24 + h + m / 60
        t = f'{total_h:g}hc' if total_h < 24 else f'{total_h / 24:g}dc'
    t = re.sub(r'(\d)\.(\d{3})\b', r'\1\2', t)                     # 1.000 min = mil minutos
    t = re.sub(r'^(\+/-|\+-|±|~)\s*', '', t)                           # "+/- 2h"
    t = re.sub(r'\bd\.?\s*u\.?(?=\s|$)', 'du', t)                      # "10 d.u."
    t = re.sub(r'\b(semanas?)\s+corridas?\b', r'\1 corrida', t)
    t = re.sub(r'^(\d+(?:[.,]\d+)?|uma?)\s+semanas?\s+corridas?$',
               lambda m: f'{7 * (1 if m.group(1) in ("um", "uma") else float(m.group(1).replace(",", "."))):g}dc', t)
    t = re.sub(r'^(um|o|1)?\s*trimestres?$', '3 meses', t)
    t = re.sub(r'^(um|o|1)?\s*semestres?$', '6 meses', t)
    t = _compor_extenso(t)                                          # "quarenta e cinco minutos"
    t = re.sub(r"^(\d+)\s*'$", r'\1min', t)                       # 45'
    t = re.sub(r'\bmeio expediente\b', '4h', t)
    for palavra in sorted(_NUMEROS, key=len, reverse=True):          # "duas horas", "dez minutos"
        t = re.sub(rf'\b{palavra}\b(?=\s+(?:e\s+meia\s+)?[a-z])', str(_NUMEROS[palavra]), t)
    t = re.sub(r'^entre\s+(\S+)\s+e\s+', r'\1 a ', t)                 # entre 2 e 3 dias
    t = re.sub(r'^(\d+(?:[.,]\d+)?)?\s*quinzenas?$',
               lambda m: f'{float((m.group(1) or "1").replace(",", ".")) * 10:g} dias uteis', t)
    t = re.sub(r'^(no\s+|o\s+|ate\s+o\s+)?(dia seguinte|proximo dia util|proximo dia)$', '1 dia util', t)
    t = re.sub(r'(\d)\s*d\s+uteis\b', r'\1 dias uteis', t)                   # 5d úteis
    t = re.sub(r'\b(semanas?)\s+e\s+meia\b', r'\1 2.5 dias uteis', t)         # 1 semana e meia
    t = re.sub(r'\b(mes|meses)\s+e\s+meio\b', r'\1 10 dias uteis', t)          # um mês e meio
    t = re.sub(r'\b(\d+(?:[.,]\d+)?)\s*h\s+e\s+meia\b', r'\1h 30min', t)  # 2h e meia
    t = re.sub(r'\b(\d+(?:[.,]\d+)?)\s*h\s+corridas?\b', r'\1 horas corridas', t)  # 48h corridas
    t = re.sub(r'\b(\d+(?:[.,]\d+)?)\s*(anos?)\b', lambda m: f'{float(m.group(1).replace(",", ".")) * 12:g} meses', t)
    t = re.sub(r'^(~|cerca de|aprox\.?|aproximadamente|ate|em media|uns|umas|mais ou menos|de)\s*', '', t)
    t = re.sub(r'^(imediato|imediatamente|na hora|instantaneo|nenhuma|nenhum|zero)$', '0min', t)
    t = re.sub(r'^(no )?mesmo dia$', '4h', t)                          # D+0: meio dia útil, em média
    t = re.sub(r'^d\s*\+\s*(\d+)(?:\s*(uteis|util|corridos?))?$',
               lambda m: f'{m.group(1)} dias {"corridos" if m.group(2) and "corr" in m.group(2) else "uteis"}', t)
    t = re.sub(r'\bmeia hora\b', '30min', t)
    t = re.sub(r'\bmeio dia\b', '4h', t)
    t = re.sub(r'\b(horas?)\s+e\s+meia\b', r'\1 30min', t)
    t = re.sub(r'\b(horas?)\s+e\s+(\d+)$', r'\1 \2min', t)               # "1 hora e 15"
    t = re.sub(r'\b(horas?)\s+e\s+(' + '|'.join(sorted(EXTENSO, key=len, reverse=True)) + r')$',
               lambda m: f'{m.group(1)} {EXTENSO[m.group(2)]}min', t)            # "uma hora e quinze"
    t = re.sub(r'\b(dias?(?: uteis)?)\s+e\s+meio\b', r'\1 4h', t)
    t = re.sub(r'\b(\d+):(\d{2})\b', r'\1h \2min', t)                    # 1:30
    t = re.sub(r'\b(\d+)h(\d+)\b', r'\1h \2min', t)                       # 2h30
    t = re.sub(r'\s+e\s+', ' ', t)                                        # 2h e 30min
    return t


def _somar(texto):
    total, achou, pos = 0.0, False, 0
    for m in _TEMPO.finditer(texto):
        if texto[pos:m.start()].strip():
            return None                                                   # sobrou texto que não é tempo
        pos = m.end()
        uni = m.group(2).strip() or 'min'
        fator = _UNIDADES.get(uni) or _UNIDADES.get(uni.rstrip('s'))
        if fator is None:
            return None
        valor = float(m.group(1).replace(',', '.'))
        if fator == DIA_CORRIDO / 24 and valor < 24:
            # "4 horas corridas", "PT4H": prazo curto corre dentro do dia de trabalho, hora a hora. Só a partir
            # de um dia o relógio passa por noite e fim de semana (a média de 5/7 de 8/24)
            fator = _UNIDADES['h']
        total += valor * fator
        achou = True
    if texto[pos:].strip():
        return None
    return total if achou else None


def minutos(valor):
    """Minutos úteis: '15min' -> 15; '1h30' e '1:30' -> 90; '1,5 dias' -> 720; '3dc' -> 3 dias corridos;
    '2 a 4h' -> 180 (média). Número puro = minutos. None se não der para ler (ou se for negativo)."""
    if valor is None or valor == '' or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor >= 0 else None
    texto = _normalizar_tempo(valor)
    if not texto or texto.startswith('-'):
        return None
    partes = [p for p in re.split(r'\s*(?:-|\ba\b|\bou\b)\s*', texto) if p.strip()]
    if len(partes) > 1:                                                   # faixa: a unidade vem no fim
        unidade = re.sub(r'^[\d.,\s]+', '', partes[-1])
        vals = [_somar(p if re.search(r'[a-z]', p) else f'{p} {unidade}') for p in partes]
        if any(v is None for v in vals):
            return None
        return sum(vals) / len(vals)
    return _somar(texto)


def faixa_minutos(valor):
    """(menor, maior) em minutos úteis quando o tempo é uma faixa ("2 a 4h", "1-3 dias"); None se é um valor só.
    A simulação sorteia dentro da faixa: é o que faz os percentis (P80, P90) refletirem a variação."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    texto = _normalizar_tempo(valor)
    if not texto or texto.startswith('-'):
        return None
    partes = [p for p in re.split(r'\s*(?:-|\ba\b|\bou\b)\s*', texto) if p.strip()]
    if len(partes) < 2:
        return None
    unidade = re.sub(r'^[\d.,\s]+', '', partes[-1])
    vals = [_somar(p if re.search(r'[a-z]', p) else f'{p} {unidade}') for p in partes]
    if any(v is None for v in vals):
        return None
    return min(vals), max(vals)


def formatar_minutos(m):
    """Minutos úteis em texto: 45 min · 2,5 h · 1 d útil · 3,5 d úteis."""
    if m is None:
        return '—'
    if m < 60:
        return f'{m:.0f} min'
    if m < DIA_UTIL:
        return f'{m / 60:.1f} h'.replace('.', ',').replace(',0 h', ' h')
    d = round(m / DIA_UTIL, 1)
    texto = f'{d:.1f}'.replace('.', ',').replace(',0', '')
    return f'{texto} d útil' if d == 1 else f'{texto} d úteis'


def numero_br(n, casas=0):
    s = f'{n:,.{casas}f}'
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def quebrar(texto, largura):
    """Quebra o texto em linhas de até `largura` caracteres, sem cortar palavra (a não ser que ela não caiba)."""
    palavras = str(texto).split()
    linhas, atual = [], ''
    for p in palavras:
        while len(p) > largura:
            if atual:
                linhas.append(atual)
                atual = ''
            linhas.append(p[:largura - 1] + '-')
            p = p[largura - 1:]
        if not atual:
            atual = p
        elif len(atual) + 1 + len(p) <= largura:
            atual += ' ' + p
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas or ['']
