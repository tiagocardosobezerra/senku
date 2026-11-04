# Senku

[Português](README.md) | **English**

**Describe the process in plain words. Get the swimlane flowchart and the full process map, checked and ready for the owner to sign off.**

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![No dependencies](https://img.shields.io/badge/dependencies-none-2ea44f?style=flat-square)
![BPMN 2.0](https://img.shields.io/badge/BPMN-2.0-A3E635?style=flat-square)
[![Tests](https://github.com/tiagocardosobezerra/senku/actions/workflows/testes.yml/badge.svg)](https://github.com/tiagocardosobezerra/senku/actions/workflows/testes.yml)
![MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)

<img width="100%" alt="Senku: from conversation to flowchart and process map, with proof" src="assets/senku-banner-en.svg" />

Senku is a Claude skill for people who map business processes: process analysts, BPM offices, quality, audit, and anyone who needs to document how the work really flows. You describe the process your way (a conversation, a transcribed recording, a pasted procedure, a spreadsheet or an existing `.bpmn`). Senku runs the interview, writes the **process charter**, asks what is missing, **proves** the flow holds together and delivers the flowchart and the process map. Everything comes from a single file; nothing is drawn by hand.

> Senku speaks and writes in Brazilian Portuguese: the interview, the commands' output and the generated documents are in pt-BR. The process itself can be described in any language Claude understands.

## What it does for you

* **Runs the interview.** Seven blocks of questions (opening, SIPOC, steps, decisions, times, management, TO-BE), in the order a good analyst asks them. It does not wait for a perfect description: it asks for what is missing.
* **Never makes up the process.** Steps, owners, systems, rules, times and percentages come from you. What it infers becomes a question. What nobody answered becomes a **gap**, with a priority, and the document is marked as a draft.
* **Proves the flow ends.** Tokens run down every path: a decision without an exit, a parallel split that never joins, an endless loop or an activity that leads nowhere shows up before the drawing. There are 73 checks, from the 7PMG guidelines to the *BPMN Method and Style* rules.
* **Measures with simulation, not guesswork.** It simulates 4,000 cases with the times and percentages from the interview and reports the typical lead time, the time within which 80% and 90% of cases finish, cycle efficiency, handoffs, rework and each area's workload.
* **Draws the swimlane flowchart.** SVG, PNG, **BPMN 2.0** (opens in Bizagi, bpmn.io, Camunda, ARIS and Signavio), **draw.io** (editable, exports to Visio) and Mermaid. Customers and suppliers can get their own pool, with message flows.
* **Writes the full process map.** Profile, scope, SIPOC, activity descriptions, business rules, RACI matrix, KPIs, times, value added, pain points, risks and controls, prioritized Lean opportunities and glossary, in HTML, Word, Markdown and a CSV of the activities.
* **Gets the owner's sign-off and keeps it.** `aprovar` records who approved, when, and a hash per section. Changed afterwards? `situacao` warns and `comparar` shows what changed, field by field.
* **Redesigns from a baseline.** The TO-BE starts from the approved charter and is compared with the AS-IS, activity by activity.
* **Brings in what you already have.** Imports `.bpmn` from Bizagi, bpmn.io, Camunda, ARIS and Signavio. Exported, edited in the modeler and brought back? Your edits win, and whatever BPMN does not store comes back from the charter.

## What it looks like

> **You:** I want to map the purchasing process. Requests arrive by email, the buyer gets quotes from three suppliers and, above $5k, the manager approves.
>
> **Claude (with Senku):** creates the charter, draws a first draft and asks only what changes the map: "Who approves when the manager is on leave?", "How long does a request wait before quoting?". With the answers, it validates, analyzes and shows the flowchart and the process map: "May I record the Supply Manager's sign-off?"
>
> **Process owner:** approved.
>
> **Claude:** records the sign-off and points out the three biggest opportunities: "the 3-day wait before quoting is the biggest waste; shall we redesign the TO-BE from here?"

No "I think the manager approves afterwards". If it did not come from you, it goes in as a question, not as a step.

## Results

Measured on version 1.13.0, with the repository examples (a fictional purchasing process and a fictional credit process).

| What | Result |
|---|---|
| Automated tests | **206 passing** |
| Modeling checks (7PMG, BPMN Method and Style, times, RACI, deadlines) | **73** |
| Cases simulated per analysis | **4,000** |
| Output formats (SVG, PNG, BPMN 2.0, draw.io, Mermaid, HTML, Word, Markdown, CSV) | **9** |
| Modelers the `.bpmn` can come from | **5** (Bizagi, bpmn.io, Camunda 7 and 8, ARIS, Signavio) |
| BPMN round trip (export, open, import) without changing the flow | **yes**, checked in the tests |
| Dependencies to install | **0** |

## Get started in 3 steps

You need Python 3.8+ (standard library only, nothing to install). Commands run **from the skill folder**; on Windows, use `python` (or `py`) instead of `python3` if needed.

### 1. Install

For all projects:

```bash
git clone https://github.com/tiagocardosobezerra/senku.git ~/.claude/skills/senku
```

```powershell
git clone https://github.com/tiagocardosobezerra/senku.git $HOME\.claude\skills\senku
```

For the current project only, use `.claude/skills/senku` as the destination.

### 2. Describe the process

Ask Claude: "I want to map the expense reimbursement process". It creates the process folder, runs the interview and fills in the charter. Want to see the roadmap first?

```bash
python3 senku.py
python3 senku.py novo C:/processos/reembolso --processo "Reembolso de despesas"
```

### 3. Check, draw and sign off

```bash
python3 senku.py lacunas C:/processos/reembolso/carta.json
python3 senku.py validar C:/processos/reembolso/carta.json
python3 senku.py documentar C:/processos/reembolso/carta.json
python3 senku.py aprovar C:/processos/reembolso/carta.json --por "Finance Manager"
```

Lost track? `python3 senku.py situacao <charter>` tells you the current stage and the next step.

## Going further

### The commands

| Command | What it does |
|---|---|
| `novo` | creates the process folder with an empty charter and the roadmap |
| `entrevista [block]` | the question script: abertura, sipoc, passos, decisoes, tempos, gestao, tobe |
| `lacunas` | what is still missing, highest priority first |
| `validar` | the 73 checks and the token proof |
| `analisar` | times, simulation, workload, value added, handoffs and Lean opportunities |
| `desenhar [--pools]` | the flowchart: SVG, PNG, BPMN 2.0, draw.io and Mermaid |
| `documentar` | the full process map: HTML, Word, Markdown and CSV, plus the drawings |
| `aprovar --por "Name"` | the process owner's sign-off, with a hash per section |
| `situacao` | where the charter stands and what changed after sign-off |
| `comparar [--contra]` | what changed since sign-off, or AS-IS x TO-BE |
| `tobe` | starts the TO-BE from the approved charter |
| `importar FILE.bpmn [--base carta.json]` | brings in an existing map, or a map edited in a modeler |

### What is generated

In a `saida/` folder next to the charter, with the process code and name in each file name:

| File | What for |
|---|---|
| `.svg` / `.png` | the swimlane flowchart, to view and paste into slides |
| `.bpmn` | BPMN 2.0 with diagram, to open and edit in Bizagi, bpmn.io, Camunda, ARIS or Signavio |
| `.drawio` | to edit in diagrams.net and export to Visio |
| `.mmd` | Mermaid, for wikis and Markdown |
| `.html` | the full process map, ready to print to PDF |
| `.docx` | the process map in Word, with table of contents, portrait and landscape sections and a sign-off table |
| `.md` | the process map in Markdown |
| `-atividades.csv` | the activity sheet, for Excel |

### Where the rules come from

* *Seven Process Modeling Guidelines (7PMG)*, by Mendling, Reijers and van der Aalst (2010).
* *BPMN Method and Style*, by Bruce Silver: the drawing style rules.
* BPM CBOK (ABPMP), SIPOC, RACI and the eight Lean wastes.

The sources and the reason for each check are in [`referencias/`](referencias/).

## How it works inside

<img width="100%" alt="How Senku works: interview, charter, proof, flowchart, process map and sign-off" src="assets/senku-fluxo-en.svg" />

| Piece | What it does |
|---|---|
| **Interview** | the question script, block by block (`carta/entrevista.py`) |
| **Charter** | `carta.json`: the whole process in one file, the source of everything (`carta/modelo.py`) |
| **Gaps** | what is still missing, by priority (`carta/lacunas.py`) |
| **Validation** | the 73 modeling checks (`carta/validacao.py`) |
| **Tokens** | the proof: tokens down every path, looking for deadlocks and endless paths (`carta/fichas.py`) |
| **Simulation** | 4,000 cases with the interview's times and percentages (`carta/simulacao.py`) |
| **Analysis** | lead time, percentiles, workload, value added and Lean opportunities (`carta/analise.py`) |
| **Layout** | places lanes, activities and arrows without crossing boxes (`carta/layout.py`) |
| **Outputs** | SVG, PNG, BPMN, draw.io, Mermaid, HTML, Word and Markdown (`saidas/`) |
| **Sign-off** | the owner's "yes", the per-section hash and version comparison (`carta/aprovacao.py`) |
| **Import** | brings `.bpmn` from other modelers and the return of an edited map (`carta/importar.py`) |

To check the installation at any time:

```bash
python3 senku.py status
python3 -m unittest discover -s testes
```

## Repository layout

```
senku/
├── SKILL.md               # What Claude reads: rules, flow and how to run the interview
├── README.md              # README in Portuguese
├── README.en.md           # This file
├── COMO-INSTALAR.md       # Installation, checks and updates
├── AVISO.md               # Process data, privacy and trademarks
├── LICENCAS-DE-TERCEIROS.md  # Animation fonts (OFL) and projects that inspired the design
├── LICENSE                # MIT License
├── senku.py               # Entry point: every command
├── carta/                 # The engine: charter, interview, gaps, validation, tokens, simulation, analysis, layout, sign-off, import
├── saidas/                # The generators: SVG, PNG, BPMN, draw.io, Mermaid, HTML, Word and Markdown
├── referencias/           # Guides: charter, interview, notation, style, analysis and document
├── exemplos/              # Complete fictional processes: purchasing (SUP-01) and credit
├── roteiros/              # Scripts for the README animations
├── ferramentas/           # Skill packager, animation generator, fuzz and stress tests
├── assets/                # README animations
└── testes/                # Test suite and regression cases
```

## Credits

**Creator:** Tiago Cardoso Bezerra | [tiagocardosobezerra](https://github.com/tiagocardosobezerra)

Named after Senku, the scientist from Dr. Stone who rebuilds civilization from scratch with method: observe, record, test and only then claim. Here, the observation is the interview, the record is the charter, the test is the token proof and the simulation, and the claim is the approved map.

Design ideas from MIT-licensed Node projects, which is why they are not included: [quickpre/bpmn-skills](https://github.com/quickpre/bpmn-skills) (interview, then a fixed schema, then compilation) and [architawr/claude-bpmn-skill](https://github.com/architawr/claude-bpmn-skill) (the model reasons, the script draws and validates). No code was copied from them.

## Acknowledgements

* My wife **Júlia** and my sons **Arthur** and **Dante**, the safe harbor where I find peace, inspiration and the lightness I need every day.
* **Bruna Cardoso Bezerra** | [brunacbezerra](https://github.com/brunacbezerra), for teaching me everything I know about Claude Code.
* **You**, for using Senku!

## Notice about process data

This repository ships only the engine and fictional examples: no real company process. The maps you make stay outside the repository (in `local/` or another folder), and you agree not to publish them. Details in [`AVISO.md`](AVISO.md).

## License

MIT License, see [LICENSE](LICENSE) for details.

---

<p align="center"><strong>Senku</strong>, doesn't guess the flow. proves it.</p>
