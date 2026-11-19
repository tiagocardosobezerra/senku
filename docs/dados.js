/* Gerado por ferramentas/gerar_site.py a partir de exemplos/compras/carta.json. Não edite à mão. */
window.SENKU = {
 "versao": "1.14.0",
 "processo": {
  "codigo": "SUP-01",
  "nome": "Compra de materiais indiretos",
  "dono": "Gerente de Suprimentos",
  "volume": "cerca de 120 requisições por mês",
  "prazo_informado": "de 10 a 15 dias úteis (prazo combinado: 10 dias úteis)"
 },
 "contagem": {
  "atividades": 14,
  "decisoes": 2,
  "paralelos": 2,
  "eventos": 2,
  "raias": 6,
  "sistemas": 3,
  "fins": 1
 },
 "tempos_dias": {
  "execucao_h": 5.2,
  "espera": 13.5,
  "lead_time": 14.1,
  "esperado": 15.0,
  "eficiencia_pct": 4,
  "p50": 14.1,
  "p80": 17.2,
  "p90": 18.4
 },
 "casos": 4000,
 "histograma": [
  [
   14,
   3115
  ],
  [
   17,
   482
  ],
  [
   18,
   256
  ],
  [
   20,
   67
  ],
  [
   21,
   32
  ],
  [
   23,
   34
  ],
  [
   24,
   7
  ],
  [
   26,
   4
  ],
  [
   27,
   3
  ]
 ],
 "passagens_caso": 7,
 "retrabalho": [
  {
   "de": "a1b",
   "para": "a2",
   "rotulo": "",
   "percentual": 15.0
  },
  {
   "de": "a7r",
   "para": "a8",
   "rotulo": "",
   "percentual": 8.0
  }
 ],
 "valor": {
  "VA": 5,
  "NAV-N": 5,
  "NAV": 4
 },
 "carga": {
  "casos_mes": 120.0,
  "horas_mes": 406,
  "pessoas": 2.5,
  "por_papel": [
   [
    "Comprador",
    240,
    1.5
   ],
   [
    "Almoxarifado",
    79,
    0.5
   ],
   [
    "Solicitante",
    34,
    0.2
   ],
   [
    "Fiscal / Contas a pagar",
    30,
    0.2
   ],
   [
    "Gestor da área",
    24,
    0.1
   ]
  ]
 },
 "oportunidades": [
  {
   "desperdicio": "Espera",
   "texto": "Espera de 3 d úteis antes de \"Cotar com fornecedores\": o que segura? (fila, alçada, lote, agenda). Prazo combinado (SLA) ou gatilho automático ajudam."
  },
  {
   "desperdicio": "Defeitos (retrabalho)",
   "texto": "Retrabalho: de \"Corrigir requisição\" volta para \"Analisar requisição\" (15% das vezes; 0,18 volta por caso). Ataque a causa na origem (checklist, campo obrigatório, validação no sistema) em vez de conferir depois."
  },
  {
   "desperdicio": "Espera",
   "texto": "Prazo de 5 d úteis de quem é de fora em \"Entregar material e nota fiscal\": dá para combinar prazo em contrato (SLA), pedir antes ou acompanhar com lembrete?"
  },
  {
   "desperdicio": "Espera",
   "texto": "Espera de 2 d úteis antes de \"Analisar requisição\": o que segura? (fila, alçada, lote, agenda). Prazo combinado (SLA) ou gatilho automático ajudam."
  },
  {
   "desperdicio": "Defeitos (retrabalho)",
   "texto": "Retrabalho: de \"Reenviar material\" volta para \"Conferir material recebido\" (8% das vezes; 0,09 volta por caso). Ataque a causa na origem (checklist, campo obrigatório, validação no sistema) em vez de conferir depois."
  }
 ],
 "validar_ok": "Carta: SUP-01 · Compra de materiais indiretos  (20 elementos, 22 fluxos, 6 raias)\n✓ Nenhum problema. Próximo: python senku.py lacunas <carta> (o que falta perguntar) ou python senku.py desenhar <carta>",
 "validar_quebrado": "Carta: SUP-01 · Compra de materiais indiretos  (20 elementos, 21 fluxos, 6 raias)\n\n✗ ERROS (o desenho sai errado; corrija antes do aceite): 1\n  [a1b] \"Corrigir requisição\" não segue para lugar nenhum: depois dela, o que acontece? (ou ligue a um fim)  (M&S)\n\nTotal: 1 erro(s), 0 aviso(s), 0 dica(s).\nPróximo: corrija os erros no carta.json e rode validar de novo.",
 "nos": [
  "a1",
  "a10",
  "a11",
  "a1b",
  "a2",
  "a3",
  "a4",
  "a5",
  "a6",
  "a7",
  "a7r",
  "a8",
  "a9",
  "d1",
  "d2",
  "f_cot",
  "fim",
  "inicio",
  "p1",
  "p2"
 ]
};
