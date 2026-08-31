# AI Defense Lab 

**Mastercard Innovation Challenge @ GFF 2026 — Team Bias Bros**

A unified, closed-loop **Identify → Generate → Defend** framework spanning four independently built GenAI-powered payment fraud vectors, plus a React + FastAPI web console for running and exploring all four live.

Every vector follows the same shape: identify a real attack surface, generate realistic synthetic attacks at scale, train a purpose-built detector against them, and feed every miss the detector makes back into the next generation — a genuine closed loop, not a one-time train/test split.

> **Sandboxed simulation throughout.** No real payment rails, no live cards, no customer data, anywhere in this repository.

<table>
  <tr>
    <td width="50%"><img src="https://github.com/user-attachments/assets/5e57d933-8776-484e-8e29-750f6c455e42" width="100%" alt="Screenshot 2026-08-31 at 5 22 31 PM" /></td>
    <td width="50%"><img src="https://github.com/user-attachments/assets/b1457601-9c66-434d-88d2-5386f9fe24a4" width="100%" alt="Screenshot 2026-08-31 at 5 22 58 PM" /></td>
  </tr>
</table>

---

## Table of contents

- [What's in this repo](#whats-in-this-repo)
- [The four vectors](#the-four-vectors)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Web console](#web-console)
- [Setup](#setup)
- [Running a vector from the CLI](#running-a-vector-from-the-cli)
- [Running the web console](#running-the-web-console)
- [Notes & limitations](#notes--limitations)
- [Team](#team)

---

## What's in this repo

| Piece | What it is |
|---|---|
| `vectors/prompt_injection/` | Indirect prompt injection into agentic commerce surfaces — a MAP-Elites red team vs. a 3-tier fused detector |
| `vectors/token_replay/` | Agentic-token replay & consent-flow abuse on the Agent Pay trust chain — a 2-layer deterministic + ML verifier |
| `vectors/merchant_fraud/` | Synthetic merchant-onboarding fraud — CTGAN-driven adversarial hard-negative mining |
| `vectors/graph_fraud/` | Mule networks & cross-rail laundering — a dual-head heterogeneous graph transformer, hardened over real adversarial epochs |
| `web/` | A React (Vite + TypeScript) frontend and FastAPI backend that run any vector's CLI as a live job and visualize its real output — no fixtures, no fabricated numbers |
| `main.py` | A thin dispatcher at the repo root: `python main.py <vector> <args...>` forwards straight to that vector's own CLI |

Each vector is deliberately **not** merged into a shared package — they resolve imports and file paths differently (see `main.py`'s own docstring for why), so each one runs in its own working directory and stays independently correct.

---

## The four vectors

<!-- TODO: one architecture-diagram screenshot per vector, e.g. from each page's "Show arch" flip card -->

### 1. Prompt Injection — checkout decision
An AI shopping agent reads reviews, receipts, and tool responses, then calls checkout APIs on the user's behalf. The attack space is decomposed into a **288-niche archive** (6 commerce surfaces × 6 evasion techniques × 8 financial objectives). A local **Qwen3-8B** model mutates payloads inside a MAP-Elites quality-diversity search; the defense fuses three tiers — content rules, a provenance graph, and a delegated-scope check — into one risk score, judged against ground truth by a **deterministic outcome checker that never calls an LLM** (so it can't itself be prompt-injected).

### 2. Token Replay — consent & token issuance
Targets Mastercard's Agent Pay trust chain directly. Four sub-types (T1–T4) are cloned from real legitimate sessions, each corrupted in exactly one labelled way. **Layer 1** is a deterministic zero-trust verifier (nonce registry + context-hash binding) that catches same-context and cross-context replay outright; **Layer 2** is a LightGBM risk scorer that catches the leakage-based cases Layer 1 structurally cannot see.

### 3. Merchant Fraud — onboarding
A **CTGAN** generator, trained only on real fraud, produces synthetic fraud candidates steered by evasion, fraud-preservation, and realism objectives together (via a differentiable PyTorch surrogate of the Keras Blue-Team classifier). Three gates — domain validation, a realism discriminator, and hard-negative mining — decide which candidates are trustworthy enough to retrain on.

### 4. Graph Fraud — post-transaction settlement
Two surfaces of one laundering operation: mule accounts (device/IP sharing, PageRank) and cross-rail arbitrage (dwell time, rail sequence). A **Dual-Head Heterogeneous Graph Transformer** is hardened over real adversarial epochs, with an FPR guardrail that automatically penalizes a blue team that only hit its F1 target by over-flagging legitimate traffic.

---

## Architecture

Every vector runs the same shape, with a different real mechanism underneath:

```
  IDENTIFY  →  GENERATE  →  DEFEND
  the real       synthetic     detector trained,
  attack         attacks at    then re-attacked on
  surface        scale         what it just missed
      ↑_____________________________________|
              (the closed loop)
```



---

## Project structure

```
MasterCard AI Garage/
├── main.py                     # dispatcher: python main.py <vector> <args>
├── requirements.txt             # single dependency list for all four vectors
├── vectors/
│   ├── prompt_injection/
│   │   ├── .env.example          # template — copy to .env, optional Gemini keys
│   │   ├── .env                 # local model + optional Gemini keys (gitignored)
│   │   ├── data/seeds/           # 48 seed payloads (adapted from ASB, InjecAgent)
│   │   ├── data/surfaces/        # benign control corpus
│   │   ├── outputs/              # archive.json, coevolution_history.json, models
│   │   ├── src/
│   │   │   ├── agent.py          # the target shopping agent
│   │   │   ├── coevolve.py       # the closed-loop orchestrator
│   │   │   ├── judge.py          # deterministic outcome judge
│   │   │   ├── llm_client.py     # Qwen3 (Ollama) / Gemini model client
│   │   │   ├── red/               # attacker + MAP-Elites archive
│   │   │   └── blue/              # 3-tier detector (content, graph, intent)
│   │   └── main.py               # attack / defend / judge / loop subcommands
│   │
│   ├── token_replay/
│   │   ├── generate/generator.py # synthetic session + T1-T4 attack generator
│   │   ├── defend/                # Layer 1 (rules) + Layer 2 (LightGBM) pipeline
│   │   ├── outputs/results.json
│   │   └── main.py
│   │
│   ├── merchant_fraud/
│   │   ├── generator.py          # CTGAN candidate generator
│   │   ├── blue_team.py          # Keras MLP classifier
│   │   ├── constraints.py        # domain-validation gate
│   │   ├── outputs/
│   │   └── main.py
│   │
│   └── graph_fraud/
│       ├── src/red_team/          # SmartEvolution + LLM Red Team Strategist
│       ├── src/blue_team/         # Dual-Head Heterogeneous Graph Transformer
│       ├── config.py
│       ├── outputs/adversarial_loop_metrics.json
│       └── main.py
│
└── web/
    ├── backend/                  # FastAPI: runs a vector's CLI as a tracked job
    │   └── app/
    │       ├── main.py            # routes: /api/run, /api/jobs, /api/results
    │       ├── jobs.py            # subprocess job manager
    │       ├── results.py         # reads each vector's real output files, fresh
    │       └── vectors.py         # maps a vector slug to its CLI command
    └── frontend/                  # React + TypeScript + Vite + Tailwind + Recharts
        └── src/
            ├── pages/              # Overview, PromptInjection, TokenReplay, ...
            ├── components/         # Panel, MetricCard, TerminalLog, RunPanel, ...
            └── lib/                # API client, live-results polling
```


---

## Web console

The `web/` app lets you start any vector's real CLI from a browser, watch its live terminal output, and see the results — read straight from each vector's own output files on disk, with no caching and no fabricated numbers.

<table>
  <tr>
    <td width="50%"><img src="https://github.com/user-attachments/assets/fa1358d2-e2a7-46da-9ffc-3c40e3406a19" width="100%" alt="Screenshot 2026-08-31 at 5 24 24 PM" /></td>
    <td width="50%"><img src="https://github.com/user-attachments/assets/e58d494c-f117-43eb-bf1f-b58cb2d83f2a" width="100%" alt="Screenshot 2026-08-31 at 5 24 59 PM" /></td>
  </tr>
</table>

Each vector page shows:
- **Run panel** — a live, color-coded terminal box streaming that vector's actual subprocess output, with Start/Stop controls.
- **The loop / funnel / pipeline diagram** — that vector's own Identify → Generate → Defend stages, explained in plain language.
- **Live metrics** — pulled fresh from the vector's own output JSON on every load (and polled automatically every 15s), never hardcoded.
- **Interactive exploration** — e.g. Prompt Injection's attack-configuration browser (pick a surface, technique, and objective, see the real payload the archive produced for it) or Token Replay's sub-class explorer.

---

## Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for the web frontend)
- **[Ollama](https://ollama.com)**, running locally, with `qwen3:8b` pulled — this is the model for Prompt Injection's target agent and attacker:
  ```bash
  ollama pull qwen3:8b
  ```

### Clone and install

```bash
git clone <this-repo-url> "MasterCard AI Garage"
cd "MasterCard AI Garage"

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

`requirements.txt` is grouped by vector and is the single source of truth — there's no per-vector `requirements.txt`. Note in particular:
- `torch-geometric` (Graph Fraud) should be installed **last**, since a mismatched version can break the `torch` that Prompt Injection's Tier 2 GNN also depends on.
- `tensorflow` (Merchant Fraud's Keras Blue-Team MLP) is a large install (~500 MB).

### Using the Gemini API (optional)

Nothing here is required — everything defaults to local `qwen3:8b` and runs with no API key at all. This is only if you want an API-backed model instead. There's no silent fallback either way: `llm_client.py` either calls the model you configured or raises, it never quietly switches providers on failure.

**Prompt Injection** — fully supported via `.env`:

```bash
cd vectors/prompt_injection
cp .env.example .env
# then edit .env and paste in a real key from https://aistudio.google.com/apikey
```

```bash
# vectors/prompt_injection/.env
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_API_KEY_2=...                    # optional — extra keys rotate in on a 429 (daily quota), not for speed
ADL_ATTACKER_MODEL=gemini-2.5-flash     # uncomment to switch the attacker off local Qwen3
```

Setting `ADL_ATTACKER_MODEL` is the entire trigger — with it unset (the default), the attacker calls local Qwen3 like everything else. Only the **attacker** switches; the target agent (`agent.py`) always stays on the local model and isn't wired to read this variable at all, even if you set it.

**Graph Fraud** — needs an actual code change, not just a key. Its Red Team Strategist is hardcoded to mock mode in `main.py`:

```python
llm_controller = LLMRedTeamController(use_mock=True)
```

There's no CLI flag or `.env` variable that changes this — setting `GEMINI_API_KEY` in your shell has no effect on the CLI as it currently stands. To actually enable it, change that line to `use_mock=False`; `config.py` already reads `GEMINI_API_KEY` from the environment once that's done.

---

## Running a vector from the CLI

From the repo root, every vector runs through the same dispatcher:

```bash
python main.py prompt-injection loop --rounds 3 --budget 20
python main.py token-replay --skip-generate
python main.py merchant-fraud --samples 5000
python main.py graph-fraud --epochs 10
```

**Prompt Injection** subcommands:

| Command | What it does |
|---|---|
| `attack --rounds N --budget N` | Phase 1 only — red team evolves payloads against the current archive |
| `defend [--seeds]` | Phase 2 only — retrain Tier 1 + Tier 2 detectors on the archive |
| `judge [--benign]` | Phase 3 only — score the archive and print the scorecard |
| `loop --rounds N --budget N` | The full closed loop — attack, defend, judge, co-evolving |

**Token Replay** flags: `--skip-generate` (reuse existing `data/sessions.csv`), `--skip-save-model`, `--with-mining` (also run the diagnostic false-negative miner).

**Merchant Fraud**: `--samples N` (candidates to generate; the CTGAN batch floor is 200).

**Graph Fraud**: `--epochs N` (adversarial epochs; inner-epoch count auto-scales with graph size).

---

## Running the web console

Two terminals — backend first, frontend second.

**Backend** (FastAPI, port 8000):
```bash
source .venv/bin/activate
pip install -r web/backend/requirements.txt   # fastapi + uvicorn (separate from the root requirements.txt)
cd web/backend
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Vite dev server, port 5173):
```bash
cd web/frontend
npm install
npm run dev
```

Then open `http://localhost:5173`. The frontend polls the backend's `/api/results` endpoint automatically, so results from a run started either through the UI or directly via the CLI both show up without a manual refresh.

---

## Notes & limitations

- **Sandboxed throughout.** No real payment rails, no live cards, no customer data anywhere in this repo — every vector runs against synthetic or clone-and-corrupt data it generates itself.
- **A fifth vector** — deepfake-enabled identity & authentication spoofing, cross-cutting onboarding, consent, and step-up authentication — is in active development and not yet represented in the web console.
- Numbers shown in the web console are read live from each vector's own output files on disk; nothing is fabricated or hardcoded for the demo.

---

## Team

**Team Bias Bros** — Mastercard Innovation Challenge, Global Fintech Fest 2026.
