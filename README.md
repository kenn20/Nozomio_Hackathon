# CogWatch

**Human Context Rot Detector with Multi-Persona Advisory**

> Humans are agents too — we context rot. CogWatch is a "Third Brain" that detects when you're losing cognitive coherence and proactively surfaces personalized multi-persona advice drawn from your own history.

## What It Does

CogWatch is an always-on background agent that:

1. **Ingests** your activity from Obsidian notes, GitHub repos, Claude Code sessions, and **Gmail** (via Hyperspell)
2. **Detects** when you're contradicting past decisions, re-asking solved questions, or abandoning threads
3. **Advises** via configurable personas (default: Elon Musk + Jensen Huang) grounded in YOUR specific history
4. **Surfaces** alerts on a web dashboard with actionable resolution options

## Architecture

```
Data Sources (Obsidian, GitHub, Claude Sessions, Gmail via Hyperspell)
    → Tensorlake Cron Agent (every 15 min)
    → Decision Extraction (pattern + LLM classification)
    → InsForge PostgreSQL + pgvector (decision records with embeddings)
    → Contradiction Detection (cosine similarity → LLM confirm + Hyperspell memory search)
    → Multi-Persona Advisory (configurable personas, enriched with Gmail context)
    → InsForge Web Dashboard (alert feed + decision timeline + account connection + memory search)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Background execution | Tensorlake Applications SDK (Python) |
| Database + Auth + Hosting | InsForge |
| Vector search | pgvector (via InsForge PostgreSQL) |
| LLM inference | OpenRouter → `nvidia/nemotron-3-super-120b-a12b:free` |
| Embeddings | OpenRouter embedding model |
| Eval framework | MLflow + LLM-as-Judge |
| Memory platform | Hyperspell (Gmail, Google Drive, GitHub ingestion) |

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for InsForge CLI)
- Tensorlake API key ([console.tensorlake.ai](https://console.tensorlake.ai))
- InsForge account ([insforge.dev](https://insforge.dev))
- OpenRouter API key ([openrouter.ai](https://openrouter.ai))
- Hyperspell API key ([app.hyperspell.com](https://app.hyperspell.com/api-keys))

### Install Dependencies

```bash
pip install -e .
```

### Environment Variables

```bash
export TENSORLAKE_API_KEY=your-key
export OPENROUTER_API_KEY=your-key
export ANTHROPIC_API_KEY=your-key  # for MLflow eval only
export HYPERSPELL_API_KEY=your-key  # for Gmail/Drive ingestion via Hyperspell
```

### InsForge Setup

```bash
npx @insforge/cli login --email
npx @insforge/cli create  # or link to existing project
```

### Deploy Agent

```bash
tl deploy cogwatch/agent/main.py
```

## Project Structure

```
cogwatch/
├── agent/              # Tensorlake cron agent
│   ├── main.py         # Entry point (@application + @function)
│   └── extractors/     # Obsidian, GitHub, Claude session, Gmail (Hyperspell) extractors
├── detection/          # Contradiction detection engine
├── advisory/           # Multi-persona advisory engine
├── dashboard/          # InsForge web dashboard
│   ├── functions/      # Edge functions (API)
│   └── web/            # Frontend
├── eval/               # MLflow evaluation
│   └── scenarios/      # Test scenarios
└── seed/               # Pre-seeded demo data
```

## Demo

1. Show Tensorlake dashboard — cron agent running every 15 min
2. Show detected contradiction — "2 weeks ago you decided REST, now going GraphQL"
3. Show persona advisory — Elon and Jensen weigh in with context-aware advice
4. Show decision timeline — unified view across all sources
5. Show MLflow results — detection accuracy on benchmark scenarios
6. Swap persona live — edit prompt, re-run advisory
7. Connect Gmail — OAuth flow via Hyperspell, search memories from email

## License

MIT
