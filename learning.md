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
- Ticket tools (`read_ticket`, `create_ticket`) and MCP demo tools for E4/E5.

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
