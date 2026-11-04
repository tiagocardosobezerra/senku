"""
Gestão: nota de risco (probabilidade x impacto) e o plano de ação das melhorias.

Probabilidade e impacto aceitam 1 a 5 ou palavras (muito baixa, baixa, média, alta, muito alta). A nota é o
produto (1 a 25) e vira nível: baixo (até 4), médio (5 a 9), alto (10 a 16), crítico (17 ou mais), a matriz
5x5 usada em gestão de riscos (ISO 31000 / COSO). É o risco inerente; a falta de controle aparece ao lado.
"""

import re

from .util import sem_acento

_ESCALA = {'muito baixa': 1, 'muito baixo': 1, 'rara': 1, 'raro': 1, 'insignificante': 1, 'irrelevante': 1,
           'baixa': 2, 'baixo': 2, 'improvavel': 2, 'leve': 2, 'pequeno': 2, 'pequena': 2,
           'media': 3, 'medio': 3, 'moderada': 3, 'moderado': 3, 'possivel': 3, 'relevante': 3,
           'alta': 4, 'alto': 4, 'provavel': 4, 'grave': 4, 'severo': 4, 'severa': 4, 'significativo': 4,
           'muito alta': 5, 'muito alto': 5, 'quase certa': 5, 'quase certo': 5, 'certo': 5, 'certa': 5,
           'critico': 5, 'critica': 5, 'altissimo': 5, 'altissima': 5, 'catastrofico': 5, 'catastrofica': 5,
           'gravissimo': 5, 'gravissima': 5, 'frequente': 5,
           'remota': 1, 'remoto': 1, 'muito rara': 1, 'ocasional': 3, 'eventual': 3,
           'muito provavel': 5, 'medio alto': 4, 'media alta': 4, 'medio baixo': 2, 'media baixa': 2,
           'alto medio': 4, 'alta media': 4, 'baixo medio': 2, 'baixa media': 2}


def _de_chance(p):
    """Chance (0 a 1) na escala 1-5: até 10% rara, 30% improvável, 50% possível, 70% provável, acima quase certa."""
    return 1 if p <= 0.1 else 2 if p <= 0.3 else 3 if p <= 0.5 else 4 if p <= 0.7 else 5


def _nota(v):
    if v in (None, ''):
        return None
    t = sem_acento(str(v)).strip().lower()
    pct = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*%', t)
    if pct:                                                   # "70%": chance
        return _de_chance(float(pct.group(1).replace(',', '.')) / 100)
    try:
        x = float(t.replace(',', '.'))
        if 0 < x < 1:                                         # 0,5: chance, não nota
            return _de_chance(x)
        n = int(x + 0.5)                                      # 4,7 é 5 (arredonda, não corta)
        return n if 1 <= n <= 5 else None
    except ValueError:
        pass
    inicio = re.match(r'([1-5])\s*[-–:.)]', t)                 # "3 - média"
    if inicio:
        return int(inicio.group(1))
    t = re.sub(r'[-/]', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    return _ESCALA.get(t)


def nivel_risco(r):
    """(nota 1-25 ou None, nível em texto). É o risco INERENTE (antes do controle): probabilidade x impacto
    como a pessoa avaliou. A falta de controle aparece ao lado, sem mexer na nota."""
    p, i = _nota(r.get('probabilidade')), _nota(r.get('impacto'))
    if p is None or i is None:
        faltam = [k for k, v in (('probabilidade', r.get('probabilidade')), ('impacto', r.get('impacto')))
                  if v not in (None, '') and _nota(v) is None]
        return None, ('a avaliar' if not faltam else f'a avaliar ({", ".join(faltam)} fora da escala 1-5)')
    n = p * i
    nivel = 'baixo' if n <= 4 else 'médio' if n <= 9 else 'alto' if n <= 16 else 'crítico'
    return n, nivel + ('' if r.get('controle') else ' · sem controle')


def riscos_ordenados(c):
    return sorted(c.riscos, key=lambda r: -(nivel_risco(r)[0] or 0))


def plano(c):
    """Melhorias com responsável, prazo e situação (o plano de ação), na ordem da carta."""
    return [{'id': m.get('id'), 'acao': m.get('descricao'), 'resolve': ', '.join(m.get('resolve') or []),
             'responsavel': m.get('responsavel') or 'a definir', 'prazo': m.get('prazo') or 'a definir',
             'situacao': m.get('status') or m.get('situacao') or 'proposta', 'impacto': m.get('impacto'),
             'esforco': m.get('esforco')} for m in c.melhorias]
