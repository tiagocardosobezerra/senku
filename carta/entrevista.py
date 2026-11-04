"""
O roteiro de entrevista, por bloco. Quem conduz não lê a lista inteira para a pessoa: escolhe as
perguntas que a carta ainda não responde (o `lacunas` aponta quais) e faz poucas por vez.
Técnica e exemplos de condução: referencias/entrevista.md.
"""

BLOCOS = [
    ('abertura', 'Identificação e escopo', [
        'Qual é o nome que vocês usam para este processo? Ele faz parte de um processo maior?',
        'Para que ele serve: que resultado entrega, e para quem?',
        'O que dispara o processo (um pedido, uma data, um evento)? Quantas vezes acontece por dia/mês?',
        'Onde ele começa e onde termina? O que fica de fora (o vizinho que não vamos mapear agora)?',
        'Quem é o dono: o cargo que responde pelo resultado e aprova o mapa?',
        'Existe norma, política, procedimento ou exigência legal que ele precisa seguir?',
    ]),
    ('sipoc', 'Visão de alto nível (SIPOC)', [
        'O que o processo recebe para começar (documento, dado, material) e de quem?',
        'Em 5 a 7 grandes passos, como o trabalho anda do começo ao fim?',
        'O que ele entrega no final, e quem recebe cada entrega?',
    ]),
    ('passos', 'O caminho principal, passo a passo', [
        'Pense no último caso que você atendeu. O que aconteceu primeiro? E depois?',
        'Quem faz esse passo (cargo ou área)? Em que sistema, planilha ou e-mail?',
        'O que a pessoa precisa ter em mãos para começar este passo? O que ela produz no final?',
        'Depois deste passo, quem recebe o trabalho? Como fica sabendo que chegou a vez dela?',
    ]),
    ('decisoes', 'Decisões e exceções', [
        'Aqui alguém decide alguma coisa? Qual é a pergunta? Quais são as respostas possíveis?',
        'Qual é o critério (valor, prazo, documento, alçada)? Está escrito em algum lugar?',
        'O que acontece quando a resposta é "não"? O caso volta, é cancelado ou segue outro caminho?',
        'De cada 100 casos, quantos voltam ou vão pelo caminho de exceção?',
        'O que acontece quando falta um documento, o sistema cai ou a pessoa está de férias?',
        'Tem coisa que acontece ao mesmo tempo, em paralelo, por pessoas diferentes?',
    ]),
    ('tempos', 'Tempos e volumes', [
        'Quanto tempo leva este passo quando a pessoa está de fato fazendo?',
        'Quanto tempo o trabalho fica parado esperando antes (fila, aprovação, resposta)?',
        'Do começo ao fim, quanto tempo o cliente espera? Qual é o prazo combinado?',
        'Tem pico (fim de mês, safra, fechamento)?',
    ]),
    ('gestao', 'Indicadores, dores e riscos', [
        'Como vocês sabem se o processo vai bem? Que número acompanham? Tem meta?',
        'O que mais atrasa, gera retrabalho ou reclamação?',
        'Onde se digita a mesma informação duas vezes, ou se confere o que já foi conferido?',
        'O que pode dar errado de grave (multa, perda, fraude, cliente sem atendimento)? Que conferência existe?',
        'Se você pudesse mudar uma coisa amanhã, o que seria?',
    ]),
    ('tobe', 'Redesenho (TO-BE)', [
        'Qual dor resolvemos primeiro, e qual resultado mostra que resolveu (indicador e meta)?',
        'Que passo pode deixar de existir? Qual pode ser feito por quem já está com o trabalho na mão?',
        'Que decisão pode virar regra automática no sistema?',
        'O que precisa mudar além do fluxo (sistema, norma, treinamento, cargo) para o TO-BE funcionar?',
    ]),
]


def imprimir(bloco=None):
    escolhidos = [b for b in BLOCOS if bloco in (None, b[0])]
    if not escolhidos:
        nomes = ', '.join(b[0] for b in BLOCOS)
        print(f'Bloco "{bloco}" não existe. Blocos: {nomes}')
        return 1
    for chave, titulo, perguntas in escolhidos:
        print(f'\n[{chave}] {titulo}')
        for p in perguntas:
            print(f'  - {p}')
    print('\nNão leia a lista: pergunte poucas por vez, com as palavras da pessoa, e grave na carta. '
          'O "lacunas" diz o que ainda falta.')
    return 0
