# InjectGuard Lab — Learning Log

Interview-ready concepts only. Prefer explaining *why* over listing every file change. Details live in `PRD.md` and the code.

---

## What this lab is about

BankOps = a **tool-calling banking ops agent** that is intentionally vulnerable first, then hardened.

**Portfolio story:** business need → dangerous agent → attacks that work (measured) → layered defenses → honest trade-offs.

**Focus order (learning priority):**
1. Threat model (entry points, read vs write blast radius)
2. Indirect injection + sink oracles (prove ASR)
3. S1 detector limits
4. S3 action policy on money movers (survives adaptive agents)
5. Eval / ablation
6. S2 isolation as *one* pattern — not “always pin the full plan”

---

## Threat model (memorize this)

| | |
|---|---|
| **E1** | Operator message (direct jailbreak) |
| **E2** | Retrieved policy text (RAG) |
| **E3** | Dispute / customer text |
| **Reads** | Import poison into context (`search_policies`, `read_dispute`, …) |
| **Writes** | Cause damage (`transfer_funds`, `issue_refund`) — watch sinks |

- **Authorization ≠ prompting.** Session `user_id` is injected by the app; never trust a model-supplied tenant id (confused deputy).
- **Structured fields vs body text:** prefer dispute `account_id` over numbers that appear only in free-text instructions.
- **Payees** = approved beneficiaries → natural allowlist for transfers.

---

## Tool-calling agents

- Loop in `BaselineAgent.chat`: Ollama gets tool schemas → model may emit `tool_calls` → app runs handlers → **S1 scores the output** → append (possibly dropped) `role=tool` results → call model again until a plain reply (or max rounds).
- The model only *proposes* tools; **your code** executes them and feeds results back into context.
- That re-entry is why agents are riskier than Q&A RAG: untrusted tool output can be treated like instructions.
- S1 now covers three boundaries: **user message** (block), **retrieved context** from read tools (always drop), **other tool outputs** (always drop).
- Keyword RAG is enough here — the lesson is *after retrieval*, not retrieval quality.

---

## Eval: oracles, sinks, ASR

- An attack case = **payload + setup + success_oracle** (a contract, not a vibe).
- Prefer deterministic oracles (sink fields, canary, regex) over LLM-as-judge for exfil / unauthorized money moves.
- **Oracle ≠ defense** — it only measures after the fact.
- Use **sink deltas** (rows appended this run), or old attacker lines pollute ASR.
- **ASR** = share of attack cases where the bad outcome happened. Baseline ASR should be high; defenses should drive it down. Report **per entry point**, not one vanity %.

---

## S1 — Detection

- **Input classifier (current):** Meta Llama Prompt Guard 2 (86M) — small **encoder** (mDeBERTa), not an LLM. Binary top label: BENIGN vs MALICIOUS (+ score). Block on MALICIOUS; no threshold yet. Lives under `app/guardrails/`.
- Why not a decision LLM for this gate? Latency/cost/variance. A classifier is deterministic and cheap enough to run on every user message (and later on retrieved/tool text).
- Same scorer, different actions: **block** user input; **drop** retrieved/tool text (replace with a short block notice) before it re-enters the model.
- Detectors still fail: paraphrases / tokenization tricks slip through; false blocks hurt utility. Pair with S2/S3.
- Fail-open on scorer errors is a product choice — call it out in reviews.
- Legacy: Ollama System One (`noul`) lives in `decision_model_inference.py` for ablation — not on the hot path.

---

## Two regimes (how to think about agent security)

**Regime A — plan is knowable up front**  
User goal + schemas already imply the tool sequence. Pin the plan → **your code** executes tools → Q-LLM may extract typed fields from untrusted text (**no tools** for that model). Poison can become data; it cannot pick the next `transfer_funds`.

**Regime B — plan is not knowable up front**  
Next step depends on what you learn (search refine, branch on status, missing ids). You still must not hand free tool choice to a model that just read raw poison. Safer variants: adaptive **reads** only; re-plan from **structured extracts**; **HITL / allowlists** on writes. S3 matters even more here.

Shared rule for both: **untrusted text must not get the steering wheel on privileged actions.**

---

## S2 — Isolation (Regime A pattern)

- **S1:** “Is this text evil?” **S2:** “Even if poison arrives, can it choose what we do?”
- **Chat path now:** S1 user gate → **P-LLM** plan → **executor** runs tools and calls the **Q-LLM** for `$fields` and for typed facts → a separate **answer model** writes the reply. A blocked user message never reaches the planner.
- The answer model is on the privileged side: no tools, and it sees the user request plus extracted facts only. The Q-LLM must not write the reply, because it just read the untrusted text and could repeat an instruction from it. The planner must not see tool output either.
- **Privileged LLM** (`privileged_llm_inference.py`): user request + tool **schemas** only. Returns a pinned `AgentPlan`. Bank tools fetch text (`save_as` names the raw blob). A `$field` is not a tool; the executor sends the blob to the Q-LLM and uses only the typed field. Raw blobs are not substituted into later tool args.
- **Quarantined LLM** (`quarantined_llm_inference.py`): untrusted text, **no tools**, JSON for a caller-supplied Pydantic model or JSON schema.
- CaMeL blocks *indirect* steering (poison in retrieved/tool text cannot pick the next tool). A jailbreak in the **user message** can still steer the P-LLM. Writes still need S3.
- Pitfall: a small model may wrap the plan under a schema name (`PlanStep`). Pydantic ignores that extra key and fills defaults, so the API shows `valid: true` with **zero steps**. Ask for a flat `{goal, steps, notes}` object, and unwrap one nested object that actually contains `steps`.

---

## S3 — Action policy (do this next)

Assume injection sometimes wins. Limit damage on writes:

- Payee allowlist: `to_account ∈ list_payees(from)`
- Amount caps / role profiles
- HITL before transfer/refund
- Output filters (canary / PII / markdown exfil)

Interview line: *Reads bring poison in; writes let poison out. Detection helps reads; capability policy is mandatory for writes.*

---

## App wiring (short)

- **Chat helper:** `ContentGuard` on the user message, then `PrivilegedLLM.plan`. Baseline tool loop is still in `baseline.py` and is not this path.
- **AppContainer:** load classifier once at FastAPI lifespan; inject into handlers. Process-scoped services ≠ request-scoped `user_id`.
- Classifier weights download from Hugging Face on first `open()` (Prompt Guard is gated — accept license + login once).

---

## Interview prompts to practice

> Walk through how your agent uses tools.  
> Model proposes → app executes → results re-enter context → final answer. Name trust boundaries (input gate, content filter, write allowlist/HITL).

> Why is a write-capable agent riskier than RAG Q&A?  
> Bad answers vs irreversible side effects when untrusted content hijacks tool choice.

> Should the LLM pass `user_id`?  
> No — resolve identity outside the model and inject in the tool runner.

> How do you prove exploitation without real banking APIs?  
> Mock sinks + deterministic oracles on sink deltas (`to_account == attacker`).

> Does plan-then-execute solve agents?  
> No. It teaches isolation. Adaptive work still needs structured re-planning and hard write policy; detectors and planners both fail sometimes.
