# CogWatch — Human Context Rot Detector with Persona Advisory

> **Track:** Always-On Agents (Tensorlake + InsForge)  
> **Date:** 2026-05-09  
> **Status:** Approved Design  

---

## Goal

Build a background agent that detects when a human is losing cognitive coherence — contradicting past decisions, re-asking solved questions, or abandoning threads — and proactively surfaces multi-persona advisory grounded in the user's own history.

## Core Thesis

Humans are agents too. We context rot. Just as LLM agents degrade across long conversations, humans lose coherence across days, projects, and life domains. CogWatch is a "Third Brain" — not a note-taking system (Second Brain), but an active cognitive facilitator that catches drift before it costs you.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│  Obsidian Vault (git-synced) ─┐                                 │
│  GitHub Repo (PRs, commits) ──┼──► Tensorlake Cron Agent        │
│  Claude Code Sessions (.claude/) ┘  (every 15 min)              │
│                                        │                        │
│                                        ▼                        │
│                              Decision Extraction                │
│                              (pattern + LLM classification)     │
│                                        │                        │
│                                        ▼                        │
│                              InsForge PostgreSQL + pgvector      │
│                              (structured decision records       │
│                               with embeddings)                  │
│                                        │                        │
│                                        ▼                        │
│                              Contradiction Detection            │
│                              (cosine similarity → LLM confirm)  │
│                                        │                        │
│                                        ▼ (when rot detected)    │
│                              Multi-Persona Advisory             │
│                              (configurable, defaults:           │
│                               Elon Musk + Jensen Huang)         │
│                                        │                        │
│                                        ▼                        │
│                              Web Dashboard (InsForge)            │
│                              Alert feed + decision timeline     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    OFFLINE EVAL (separate)                       │
│  MLflow: LLM-as-Judge benchmark                                 │
│  - Agent correctness (detection accuracy, groundedness,         │
│    false positive rate)                                         │
│  - Model viability (open model vs proprietary baseline)         │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Background execution | Tensorlake Applications SDK (Python) | Cron-scheduled durable agent |
| Database + Auth + Hosting | InsForge | PostgreSQL, auth, edge functions, deployment |
| Vector search | pgvector (via InsForge PostgreSQL) | Embedding similarity for detection |
| Embeddings | OpenRouter → open embedding model (or nemotron completion-based) | Generate decision record vectors |
| LLM inference | OpenRouter → `nvidia/nemotron-3-super-120b-a12b:free` | Privacy-preserving, zero-cost inference |
| Eval framework | MLflow + LLM-as-Judge | Agent correctness + model viability benchmark |
| Data sources | Obsidian (git), GitHub API, local `.claude/` files | Decision extraction |

## Component Details

### 1. Ingestion Layer (Tensorlake Cron)

A `@function()` decorated Python app deployed to Tensorlake, scheduled via cron (every 15 minutes).

**Three extractors:**

| Source | Access Method | Extracts |
|--------|--------------|----------|
| Obsidian Vault | Git clone/pull from synced repo | Notes with decision language, questions, TODOs |
| GitHub Repo | GitHub API (commits, PRs, review comments) | Design decisions, rationale in PR descriptions |
| Claude Code Sessions | Read `.claude/` directory | Memory files, session summaries, captured decisions |

**Output:** Structured Decision Records stored in InsForge DB:

```python
{
    "id": "uuid",
    "source": "obsidian|github|claude_session",
    "content": "Decided to use PostgreSQL over MongoDB because...",
    "context": "Working on auth system for project X",
    "timestamp": "2026-05-01T10:30:00Z",
    "embedding": [float],  # generated via open model or embedding endpoint
    "tags": ["architecture", "database"],
    "status": "active|superseded|stale"
}
```

### 2. Detection Engine

Triggered on each new ingestion. Process:

1. Generate embedding for new item
2. Query DB for top-5 most similar past decisions (cosine similarity via pgvector)
3. If similarity > 0.75 threshold, pass pair to LLM for confirmation:

```
Given these two statements from the same person:
- OLD ({date}): "{old_decision}"
- NEW ({date}): "{new_activity}"

Are these contradictory? If so, what's the nature of the contradiction?
Respond as JSON: {is_contradiction: bool, explanation: str, severity: "low"|"medium"|"high"}
```

4. If contradiction confirmed → trigger Advisory Engine

**Detection types:**
- **Direct contradiction** — stated A, now doing not-A
- **Forgotten resolution** — re-asking a question already answered
- **Stale thread** — deferred decision never revisited (age + "TODO"/"later" markers)

### 3. Advisory Engine (Configurable Personas)

When contradiction detected, configurable personas respond.

**Default personas:** Elon Musk + Jensen Huang

**Persona implementation:** Configurable via system prompts. Implementation may range from simple prompt engineering to more sophisticated approaches (noted for iteration). Each persona prompt is stored in the DB and editable via the dashboard.

**Context provided to each persona:**
- The contradicting pair (old decision + new activity)
- 3-5 related decisions from user's history (retrieved via embedding similarity)
- Source context (which note, PR, or session)

**Prompt structure:**
```
You are {persona_name}. {persona_system_prompt}

The user made this decision on {old_date}:
"{old_decision}"
Context: {old_context}

Now they appear to be doing the opposite:
"{new_activity}"
Context: {new_context}

Related past decisions by this person:
{related_decisions}

Provide your perspective in 2-3 sentences. Reference their specific history.
Stay in character. Be direct.
```

**Output stored** in DB and surfaced as alert cards on dashboard.

### 4. Web Dashboard (InsForge)

Deployed via InsForge with built-in auth.

**Pages:**
- **Alert Feed** — chronological list of detected contradictions with persona responses. Each card shows: contradiction summary, both persona responses, source links, action buttons (Acknowledge / Old was right / New is right)
- **Decision Timeline** — all extracted decisions across sources, filterable by source and tags
- **Settings** — manage personas (add/edit/remove, edit system prompts), configure detection threshold, manage connected data sources (repo URLs, vault path)

**Auth:** InsForge built-in (email/password, sufficient for hackathon demo)

### 5. MLflow Eval (Offline Benchmark)

**Purpose:** Ground the agent in reality. Validate that:
1. Detection is accurate (true contradictions flagged, non-contradictions skipped)
2. Advisory is grounded (personas reference real history, don't hallucinate)
3. Severity classification is correct
4. Open model (`nemotron-3-super-120b-a12b:free`) performs adequately vs proprietary baseline

**Dataset:** 10-20 labeled scenarios:
- Known contradictions → agent SHOULD flag
- Similar-but-not-contradictory decisions → agent should NOT flag
- Advisory outputs checked for hallucination against provided context

**Judge:** Proprietary model (e.g., Claude) scores outputs on:
- Detection accuracy (binary: correct/incorrect)
- Relevance (1-5: is the advisory relevant to the contradiction?)
- Groundedness (1-5: does it reference real history vs hallucinate?)
- Actionability (1-5: can the user act on this advice?)

**Execution:** Python script run before demo. Results logged to MLflow, shown as a dashboard tab or presentation slide.

## Required Agent Skills

The following skills are available and should be used during implementation:

| Skill | Purpose |
|-------|---------|
| `tensorlake` | Tensorlake SDK — sandboxes, durable workflow orchestration, cron scheduling, deployment. Use for building the background agent. Always WebFetch `https://docs.tensorlake.ai/llms.txt` first. |
| `insforge` | InsForge backend platform — database, auth, storage, edge functions, deployment. Use for building the web dashboard, API, and PostgreSQL decision store. |

## Key Design Decisions

1. **Background + memory are both load-bearing** — remove the cron and detection never triggers; remove the decision store and the agent has no history to compare against
2. **Personas are configurable** — not hardcoded; stored as editable prompts in DB
3. **Detection is cheap** — embedding similarity is fast, LLM only called on high-similarity pairs
4. **Eval is separate from runtime** — doesn't slow down the agent, but validates the same logic
5. **Privacy-first** — open model via OpenRouter, data in user-controlled infra, can run locally if needed
6. **Pre-seeded data for demo** — realistic Obsidian notes + GitHub activity to show detection working immediately

## Demo Flow (3 minutes)

1. **Show the agent is running** — Tensorlake dashboard showing cron executions, last run timestamp
2. **Show a detected contradiction** — "2 weeks ago you decided REST, now you're going GraphQL. Here's what Elon and Jensen think."
3. **Show the decision timeline** — all your decisions across sources, unified
4. **Show MLflow results** — "The open model scores 4.2/5 on groundedness — good enough, and your data never left your infra"
5. **Show configurability** — swap a persona prompt live, re-run advisory

## Success Criteria

- [ ] Agent runs on Tensorlake cron without human prompting
- [ ] Decisions persist across sessions (removing memory breaks demo)
- [ ] At least one real contradiction detected from pre-seeded data
- [ ] Persona advisory references actual user history
- [ ] Dashboard deployed and accessible (not localhost)
- [ ] MLflow eval shows detection accuracy > 80% on test scenarios
- [ ] All inference via open model (no proprietary model in production path)
