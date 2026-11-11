---
name: injectguard-learning
description: >-
  Maintains InjectGuard Lab learning.md with interview-ready notes on prompt
  injection, RAG/agents, tool calling, defenses, and evals. Use proactively
  while building this project after meaningful implementations, explanations,
  or design decisions — not only when the user asks to document. Also use when
  the user mentions learning.md, interview prep, or documenting takeaways.
---

# InjectGuard learning log

## Goal

Keep `learning.md` at the repo root as a **job-interview study log**, not a commit changelog. Capture concepts Yuvraj should be able to explain in an AI-engineer / LLM-security interview.

## When to update (proactive)

After any of these, **read this skill and update `learning.md` without waiting to be asked**:

- A new component ships (tool, defense layer, eval, attack case, MCP piece)
- A design trade-off is chosen (keyword vs embeddings, Dual-LLM vs ReAct, etc.)
- A security concept is clarified (trust boundary, indirect injection, taint, HITL)
- A failure mode or bypass is observed while testing
- The user asks "how does X work?" and the answer is reusable in interviews

**Skip** pure chores: renames, formatting, dependency bumps, "commit/push", logging tweaks with no new concept.

## Before writing

1. Read `learning.md` (and skim `PRD.md` § learning objectives if unsure what matters).
2. Deduplicate: extend an existing **thematic** section if the topic already exists; do not add a new dated diary entry for the same idea.
3. Prefer **one sharp entry** over many tiny ones.
4. If `learning.md` is drifting into a changelog (“what we built” per commit), **merge into concept sections** instead of appending. Drop OpsPilot/email leftovers; keep BankOps + interview angles.
5. Target a lean file (~one screen of core concepts + a few interview prompts). Link to `PRD.md` / code for implementation detail.

## Entry format

Append under a dated `##` heading (ISO date). Use this shape:

```markdown
## YYYY-MM-DD — Short title

### What we built
- Bullet of concrete change (optional if the session was conceptual only)

### Concepts worth remembering
- Concept in plain language; include *why it matters* for agents/security

### Interview angle
> One question an interviewer might ask, plus a 2–4 sentence answer sketch

### Pitfalls / limitations
- What breaks, what we deliberately left vulnerable, or known bypasses

### Open / next to learn
- Optional: the next concept this unlocks
```

Omit empty subsections. Keep entries concise (roughly 8–20 lines).

## What counts as "worth learning"

Prioritize (aligned with this lab):

- Threat modeling: assets, entry points (E1–E6), trust boundaries
- Direct vs **indirect** prompt injection; why tool-using agents raise blast radius
- Tool-calling loop (model proposes → app executes → results re-enter context)
- Retrieval: keyword vs semantic; untrusted retrieved text as an attack surface
- Defense layers from the PRD: detection/spotlighting, isolation (Dual-LLM / plan-then-execute), action controls (allowlist, taint, HITL, output filter, MCP pinning)
- Eval metrics: ASR, false-block, utility, latency, cost; ablation thinking
- Honest limitations and bypasses (interviewers value this)

Frame notes so they help **next jobs**: explainable system design, not "we edited file X".

## How to tell the user

After updating, mention briefly that `learning.md` was updated and name the section title. Do not dump the whole entry unless asked.

## Do not

- Commit or push unless the user asks
- Put secrets, real credentials, or private personal data in `learning.md`
- Turn the file into a full architecture dump — link to `PRD.md` / code instead
