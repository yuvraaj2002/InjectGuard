# InjectGuard Lab — Learning Log

Running notes while building this project. Prefer **interview-ready** takeaways: concepts you can explain, design trade-offs, and failure modes — not a diary of every file edit.

---

## 2026-11-09 — Vulnerable baseline: FastAPI + tool-calling agent

### What we built
- FastAPI skeleton with `GET /health` and `POST /chat`.
- Keyword `search_docs` over synthetic markdown (no vector DB yet).
- Naive agent loop via Ollama (`lfm2.5-thinking`) with one tool round-trip.
- Info logging for request → tool selection → tool result → final answer.

### Concepts worth remembering
- **Tool calling is an LLM suggestion + your executor.** The model returns a tool name and args; *your code* runs the function and feeds the result back. The model never magically executes tools.
- **Typical loop:** system + user (+ tool schemas) → model → optional tool_calls → execute tools → append tool results → model again → final answer.
- **Keyword retrieval (this lab's first RAG stand-in):** tokenize query → score docs by token overlap (optional title/filename boost) → return top-k. Cheap and inspectable; weak on paraphrase/synonyms vs embeddings.
- **Why the baseline is vulnerable (intentional):** retrieved doc text is concatenated into context with **no** input/content guard, spotlighting, isolation, or action policy. Untrusted text can become instructions.

### Interview angle
> "Walk me through how your agent uses tools."  
> Answer with the loop above, then say what you would add at each trust boundary (guard on tool output, plan-then-execute, allowlists on write tools).

### Open / next to learn
- Implement success oracles + eval runner against `data/attacks/dataset.yaml`, then MCP demo tools for E4/E5.

---

## 2026-11-09 — Attack dataset as eval contracts

### What we built
- `data/attacks/dataset.yaml`: BankOps benign + C1/C2/C3/C6 cases + deferred C4/C5 placeholders.

### Concepts worth remembering
- An attack case is a **contract**: trigger (`payload`) + world state (`setup`) + measurable win condition (`success_oracle`). Without the oracle, you only have anecdotes.
- Prefer **deterministic oracles** (sink fields, canary substrings, regex) over LLM-as-judge when the goal is exfil/unauthorized action.
- Categories (C1–C8) and entry points (E1–E6) let you report **per-surface ASR**, not one misleading overall %.

---

## 2026-11-09 — Success oracles (eval layer, not a defense)

### What we built
- `eval/oracles.py` + `eval/sinks.py`: given oracle spec + reply/tool traces/sink delta → `OracleResult(succeeded, reason, signals)`.
- Unit tests cover `reply_contains`, `reply_regex`, `sink_match`, `unauthorized_write_tool`, `canary_anywhere`.

### Concepts worth remembering
- **Oracle vs defense:** the oracle only *measures* attack success after the fact; it does not block the agent.
- **Sink delta matters:** check only rows appended during the case, or prior `attacker@evil.test` lines pollute ASR.
- **Optional signals** (e.g. canary in email body) enrich the report; required `match` fields decide pass/fail for `sink_match`.

---

## 2026-11-09 — Eval runner turns cases into baseline ASR

### What we built
- `eval/runner.py`: load dataset → seed setup → snapshot sinks → run `BaselineAgent` → delta → oracle → ASR report (`eval/last_baseline_report.json`).

### Concepts worth remembering
- **ASR (Attack Success Rate)** = share of attack cases where the oracle says the bad outcome happened. Higher ASR on the *baseline* is good for a lab (proves vulnerability); defenses should drive it down.
- Seed/restore of docs/emails keeps cases isolated without permanently polluting synthetic data.
- Report per category: overall ASR can hide a surface that is still wide open.

---

## 2026-11-09 — Baseline ASR proven (indirect injection)

### What we observed
- Triggering `read_email` on `email-003` caused the agent to call `send_email` to `attacker@evil.test` (visible in `email_sink.jsonl` and the UI tool trace).
- Same pattern applies to `ticket-003` → write-tool side effects without any defense layer on.

### Concepts worth remembering
- **G1 is the point of a lab:** defenses are meaningless until you show the unprotected agent *does* take the malicious action. Sinks + tool traces are the oracle.
- **Instruction hierarchy failure:** tool output is *data*, but a naive ReAct loop concatenates it into the same context as system/user instructions, so the model may obey the email/ticket body.
- **Success condition for this attack:** not “model said something weird” — it’s **side effect in the sink** (wrong recipient / wrong ticket assignee / canary in body).

### Interview angle
> "How do you know your agent is actually vulnerable?"  
> Run planted indirect payloads through the real tool loop; assert on sink artifacts (exfil recipient, canary leak), not on free-text judgment alone.

---

## 2026-11-09 — Email tools raise blast radius

### What we built
- `read_email` / `send_email` in `app/tools/email_tool.py` with Ollama tool schemas imported into the baseline agent.
- Synthetic inbox + mock JSONL sink (no real SMTP).
- Multi-round tool loop so the model can read then act.

### Concepts worth remembering
- **Read tools vs write tools:** `read_email` mainly expands *context* with untrusted text (indirect injection surface). `send_email` turns text into an *action* — that is where blast radius becomes real.
- **Indirect injection (E3):** a malicious email body can instruct the agent to call write tools. In a vulnerable baseline, tool output is trusted like data but the model may treat it like instructions.
- **Mock sinks are part of the threat model for labs:** success oracles later check whether `send_email` wrote to a non-allowlisted recipient (e.g. `attacker@evil.test`), without ever touching real mail.

### Interview angle
> "Why is a RAG chatbot safer than an agent that can send email?"  
> Q&A-only RAG mostly risks bad answers or leakage in text. An agent with write tools can exfiltrate or take irreversible actions when untrusted content hijacks the plan — so you need action policy / HITL, not only better prompting.

### Pitfalls / limitations
- Baseline has **no** recipient allowlist, HITL, or content guard on email bodies yet — by design.
- Small models may invent bad tool args (e.g. `query="recent"`). Prefer clearer tool descriptions + a stronger tool-calling model over hacking the tool with aliases.

---

## 2026-11-09 — Tool schemas are part of the UX for the model

### Concepts worth remembering
- The model only “knows” how to call a tool from the **schema + description + system prompt**. Vague wording → wrong args → empty results that look like app bugs.
- Debugging agent tools: log the exact `tool_calls` args before blaming retrieval.

---

## 2026-11-09 — Ticket tools mirror the email trust pattern

### What we built
- `read_ticket` / `create_ticket` in `app/tools/ticket_tools.py` with synthetic tickets + JSONL sink.

### Concepts worth remembering
- Same split as email: **read** expands untrusted context (E3); **create** is a write action later constrained by allowlists / HITL / taint policy.
- Keeping tool schemas next to implementations makes the agent a thin dispatcher — easier to toggle defenses per tool later.

---

## 2026-11-09 — Observability UI for tool-calling demos

### What we built
- Chat API now returns `tool_calls` (name, args, output) plus `GET /tools`.
- Notion-style React lab UI in `ui/` for LinkedIn/X demos.

### Concepts worth remembering
- For agent demos, the **trace is the product**: without tool I/O in the API response, a chat box cannot explain *why* an answer appeared (or an attack succeeded).
- CORS + a thin `/tools` catalog lets a separate frontend inspect the same surface the model sees.

---

## 2026-11-09 — S1 decision: guard model over heuristics-first

### Concepts worth remembering
- **S1 primary path (locked in PRD):** a decision/guard model scores user + tool/doc text before it enters context (`score(text) -> Verdict`), then block/drop/redact.
- Heuristics and spotlighting are useful extras; they are not the main 2026-quality detector.
- Still pair with **action policy (S3)** — no classifier is perfect.

---

## 2026-11-09 — System One `noul` as the injection verdict

### What we built
- `defenses/s1_detection/decision_model_inference.py` calling Ollama `POST /v1/systemone` with model `tev1:0.8b`.

### Concepts worth remembering
- System One is a **decision API**, not chat: you pass `state` + typed `questions`; for yes/no use `type: noul` and read `answers.*.noul` ∈ [0, 1] = P(true).
- Map to our Verdict: `confidence = noul`, `injection = noul >= threshold` (config `INJECTION_THRESHOLD`).
- Same scorer can run on **user input**, **retrieved docs**, and **tool outputs** — only the `source` label and the action (block vs drop) change.

---

## 2026-11-09 — Three S1 choke points + visualizing them

### What we built
- `ContentGuard` wired in the agent: block on user input; drop/flag on retrieved context (`search_docs` / `read_email` / `read_ticket`) and other tool outputs.
- API returns `guard_events` + `blocked`; UI shows an SVG **node/edge flow graph** (user → decision model → yes/block or no/continue → later gates).

### Concepts worth remembering
- **Same detector, different actions:** input → refuse the request; untrusted content → withhold from context (drop) so the planner never “sees” the poison.
- Demo UX matters for security labs: a readable trust-boundary graph teaches architecture better than a binary “blocked” toast (or an overbuilt 3D scene).

---

## 2026-11-10 — Level 2 after S1: architectural isolation (not another detector)

### Concepts worth remembering
- **S1 is probabilistic.** A clever paraphrase can slip past `noul`. Level 2 assumes some poison still reaches the system and asks: *can that text steal the steering wheel?*
- **Dual-LLM / Plan-Then-Execute:**
  - **P-LLM (privileged):** sees user intent + tool schemas only → writes a fixed **plan** (`read_email` then `send_email` with `$summary`) *before* untrusted data is read.
  - **Q-LLM (quarantined):** sees email/doc/ticket text, has **no tools**, may only return **schema-valid structured facts** (summary, fields). Instruction-looking text becomes data extraction, not tool calls.
  - **Executor (code):** runs the plan, binds `$vars`, attaches **taint**, and blocks tainted values from sensitive args (`to`, `assignee`) unless allowlisted/HITL.
- Interview line: “S1 asks *is this text evil?* S2 asks *even if it is, can it choose what we do?*”
- **P-LLM has schemas, not live tools.** It outputs a JSON plan; the executor calls tools. That stops *indirect* injection from rewriting control flow (plan is fixed before email/doc text is read).
- **Direct user malice is different:** a user can still ask for a bad plan. S2 doesn’t replace allowlists/HITL (S3) or S1 on user input — it mainly stops *retrieved/tool text* from steering the agent.

---

## 2026-11-10 — Privileged planner (P-LLM) scaffold

### What we built
- `defenses/s2_isolation/`: `schema.py` (`AgentPlan` / `PlanStep`), `prompt.py`, `planner.py` (`PlannerLLM`).
- Planner input = user request + tool schemas only → JSON plan with optional `$variables`. No tool execution.
- UI defense graph now shows **S1 detect → S2 planner → pinned plan → execute → S1 content filters**.

### Concepts worth remembering
- Pinning control flow means a **validated plan object**, not vibes: known tools only, step cap, parseable JSON.
- `$email_summary`-style placeholders are slots for the future quarantined extractor / executor — not live tool results inside the planner.
- Visual teaching order: S1 asks “is this text evil?”; S2 answers “even if poison arrives later, it cannot rewrite the plan.”

---

## 2026-11-10 — Next after planner: executor + Q-LLM; read vs write risk

### What we built
- `defenses/s2_isolation/executor.py`: `PlanExecutor` walks `AgentPlan` steps, resolves `$vars`, calls real tool functions, stores `save_as` outputs. No LLM in the executor.

### Concepts worth remembering
- **Next build order (S2):** (1) deterministic **executor** runs the pinned plan with real tool functions ✅, (2) **Q-LLM** extracts typed fields from untrusted text (no tools) ✅, (3) bind `$vars` + **taint** into the executor loop, (4) wire into the agent/UI. S1 decision model still sits on retrieved text as defense-in-depth.

---

## 2026-11-10 — Quarantined LLM (Q-LLM) extractor

### What we built
- `defenses/s2_isolation/quarantine.py` + `ExtractedContent` schema: untrusted text → validated JSON fields (`summary`, `key_points`, …). No tools.

### Concepts worth remembering
- Q-LLM’s job is **data extraction under a schema**, not “answer helpfully.” Jailbreak text in an email should become summary noise, not a `send_email` call.
- `to_variables(prefix=…)` turns the struct into executor `$slots` (e.g. `email_summary`) — still without taint labels until the next wiring step.
- **Read tools** (`search_docs`, `read_email`, `read_ticket`) are mostly a *data* risk: they can pull poisoned instructions into context. Mitigate with S1 filter + Q-LLM schema extract so poison becomes fields, not new tool calls.
- **Write tools** (`send_email`, `create_ticket`) are an *action* risk: one bad call exfils or escalates. Mitigate with **scoped params** — tainted values must not fill `to` / `assignee` (allowlist / HITL = S3). Body/summary can still be tainted content under an output filter.
- Interview line: “Reads bring poison in; writes let poison out. Detection helps reads; capability policy is mandatory for writes.”

---

## 2026-11-10 — Why a domain theme (prefer banking ops)

### Concepts worth remembering
- A themed agent makes trust boundaries obvious: untrusted *customer/vendor messages* vs privileged *money-moving tools*.
- **Best lab theme for prompt injection:** internal **banking / payments ops** assistant (not a public chatbot). Stakes are intuitive; write tools map cleanly to policy (`transfer.to_account`, `amount`, `payee`).
- Theme helps S3: allowlists, HITL, and oracles (“did funds leave to attacker account?”) beat vague “email was sent.”
- Keep it synthetic (`*.test` accounts, local sinks) — never real banking APIs.

---

## 2026-11-10 — PRD as portfolio problem statement (BankOps)

### What we built
- Rewrote `PRD.md` v0.3: **problem first** → AI Engineer build plan → **P1–P10 problems to solve** → S1/S2/S3 → eval/portfolio pitch.
- Locked simplicity: **keyword RAG, no vector DB**.

### Concepts worth remembering
- Portfolio narrative: *business need → dangerous agent → attacks that work → layered defenses → measured trade-offs*.
- Multiple problems beat a single “add a guardrail” story: threat model, oracles, detection limits, isolation, write-tool policy, ablation.

---

## 2026-11-10 — BankOps policies + `search_policies`

### What we built
- Replaced OpsPilot IT docs with ~9 synthetic banking SOPs (refund, dispute, KYC, transfer, payee, holds, fraud, privacy/canary, chargeback).
- Replaced `search_docs` with `search_policies`: keyword overlap → score → top-5 ranked policy text.
- Kept tool modules flat (one main function per tool) so the lab stays easy to read.

### Concepts worth remembering
- **Keyword RAG is still RAG:** retrieved policy text re-enters the model context and is an **indirect injection** surface — even when the “corpus” is trusted-looking SOPs.
- Overlap score = shared tokens (+ light title/filename boost). Easy to debug and to poison in evals; weak on paraphrase vs embeddings.
- Tool APIs that return a **formatted string** (not a hit list + formatter) match how the agent actually consumes tool output.

### Interview angle
> Why skip a vector DB in this lab?
> Because the security lesson is about *what happens after retrieval*, not retrieval quality. Keyword top-k is inspectable, deterministic enough for oracles, and still lets you plant poisoned docs.

### Pitfalls / limitations
- Attack dataset still mostly OpsPilot-shaped (email/ticket); banking write tools + dispute oracles come next.
- Keyword search can miss synonyms (“chargeback” vs “refund”) or over-rank docs that share common ops words.

---

## 2026-11-10 — Session `user_id` + `read_dispute` ACL

### What we built
- `POST /chat` accepts `user_id` (mock stand-in for token→identity). Agent carries it for the whole turn.
- `read_dispute`: list / `dispute_id` / `query`, scoped to `assignee == user_id`.
- `search_policies` filtered by `policy_access.json` (user → allowed policy ids = markdown stems).
- Tool schemas do **not** expose `user_id`; the executor injects session identity and ignores model-supplied ids.

### Concepts worth remembering
- **Authorization ≠ prompting.** “Only read your queue” must be enforced in tool code, or a jailbreak/poisoned doc can widen access by inventing another `user_id`.
- Two retrieval modes: **id** (deterministic eval/demo) vs **query** (ops UX). Same ACL applies to both.
- Disputes are the main **indirect injection** surface; policy ACL is a separate least-privilege lesson on RAG corpora.

### Interview angle
> Should the LLM pass `user_id` into tools?
> No. Resolve identity outside the model (auth/session), inject it in the tool runner, and never trust tool args for tenancy. Otherwise the agent is a confused deputy.

### Open / next to learn
- Wire real auth later; keep the same injection point.
- Next BankOps tools: `list_payees`, money-moving writes.

---

## 2026-11-10 — `get_account` + dispute→account chain

### What we built
- Synthetic accounts JSON + `get_account(account_id)` read tool.
- Disputes already expose structured `account_id`; prompt tells the agent to prefer that field over free-text numbers in the body.

### Concepts worth remembering
- **Tool chaining** is how ops agents work: dispute → account_id → balance/status → (later) refund/transfer.
- Structured fields vs body text is a trust lesson: poisoned body may say `ACCT-9999`, while the case’s real `account_id` is still `ACCT-1001`. Prefer structured ids until S3 taint/HITL exists.
- Open `get_account` by id is over-privileged on purpose for now; ACL can come later (book-of-business or dispute-linked only).

---

## 2026-11-10 — `list_payees` as transfer allowlist seed

### What we built
- `payees.json`: account_id → list of `{payee_id, name, account_number, bank_name}`.
- `list_payees(account_id)` read tool; attacker destinations (`ACCT-9999`) are intentionally not saved payees.

### Concepts worth remembering
- Payees = **approved beneficiaries**. Later S3 can require `transfer_funds.to_account ∈ list_payees(from_account)`.
- This is how you teach **allowlists** without a vector DB: deterministic JSON, easy oracles (“did money leave to a non-payee?”).
- Empty payee books (e.g. `ACCT-2001`) are useful demos: no legitimate outbound destination until one is added.

---

## 2026-11-10 — Write tools: `transfer_funds` + `issue_refund`

### What we built
- Removed OpsPilot email/ticket tools and their synthetic JSON.
- BankOps write tools append to local sinks: `transfer_sink.jsonl`, `refund_sink.jsonl` (no real rails).
- Agent tool surface is now the six BankOps tools only.

### Concepts worth remembering
- **Write tools are the damage surface.** Reads import poison; writes move money (even if mocked). ASR oracles should watch sink `to_account` / `amount`.
- Sensitive args: `to_account`, `amount` (and refund `dispute_id` linkage). S3 later: payee allowlist + HITL + taint.
- Vulnerable-by-default is intentional: baseline will happily refund to `ACCT-9999` if a poisoned dispute says so.

### Interview angle
> How do you prove a money-moving agent was exploited without real banking APIs?
> Append-only mock sinks + deterministic oracles on the delta (`to_account == attacker`). Same pattern as email sinks, clearer blast radius for a portfolio story.

---

## 2026-11-10 — Chat helper: S1 on user message first

### What we built
- `app/agent/chat_helper.py` → `handle_chat`: decision model scores the operator message before `BaselineAgent` runs.
- Confidence gate: System One `noul` ≥ `INJECTION_THRESHOLD` ⇒ block; otherwise allow and continue.
- Retrieved-context / tool-output S1 toggles left **off** for now (same detector, later choke points).

### Concepts worth remembering
- **First choke point is E1 (user input).** Direct jailbreaks never need RAG — stop them before the tool loop starts.
- `noul` is P(true) for “is this injection?” — not a separate confidence channel. Thresholding that probability *is* the confidence filter.
- Put the gate in a **chat helper** (API → helper → agent), not only inside the agent, so the trust boundary is obvious and later stages can be added beside it.

### Interview angle
> Where do you put an input injection classifier in a tool-calling agent?
> Before the agent loop. Score the user message; on block return a refusal + guard event and never call tools. Reuse the same scorer later on retrieved/tool text with a different action (drop vs refuse).

### Pitfalls / limitations
- Probabilistic: paraphrases can slip under the threshold; false blocks hurt utility. Pair with S2/S3.
- Fail-open on decision-model errors today (availability over fail-closed) — call that out in reviews.

---

## 2026-11-10 — AppContainer: boot once, pass shared services

### What we built
- `AppContainer` holds long-lived services (`decision_model`, `content_guard`).
- FastAPI **lifespan** builds it at startup, stores `app.state.container`, closes on shutdown.
- Routers `Depends(get_container)` → `handle_chat(..., container=...)` reuses the opened HTTP client.

### Concepts worth remembering
- Name for this pattern: **application / service container** (composition root). Not a DI framework — a small object you assemble at boot and hand down.
- **Why:** avoid re-init cost (HTTP clients, model handles) on every request; one place to see what the process owns.
- **What belongs:** process-scoped clients/scorers. **What does not:** per-request identity (`user_id`) or per-turn agent state — those stay on the request/agent.
- Interview phrasing: “We wire dependencies at startup and inject the container; handlers call `container.decision_model`, they don’t construct it.”

### Interview angle
> How do you avoid creating a new guard-model client on every chat request?
> Build an app container in the FastAPI lifespan, open the client once, put it on `app.state`, and inject it into the chat helper via Depends. Close it on shutdown.
