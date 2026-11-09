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
- Implement success oracles + eval runner against `attacks/dataset.yaml`, then MCP demo tools for E4/E5.

---

## 2026-11-09 — Attack dataset as eval contracts

### What we built
- `attacks/dataset.yaml` v1: C1/C2/C3/C6 runnable cases + deferred C4/C5 placeholders.

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
