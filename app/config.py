from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "data" / "synthetic" / "docs"
EMAILS_PATH = PROJECT_ROOT / "data" / "synthetic" / "emails" / "emails.json"
EMAIL_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "email_sink.jsonl"
TICKETS_PATH = PROJECT_ROOT / "data" / "synthetic" / "tickets" / "tickets.json"
TICKET_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "ticket_sink.jsonl"

OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "lfm2.5-thinking:latest"

# S1 decision / guard model (Ollama System One)
DECISION_MODEL = "tev1:0.8b"
DECISION_MODEL_TIMEOUT_S = 30.0
# noul >= threshold ⇒ treat as prompt injection / jailbreak
INJECTION_THRESHOLD = 0.45

# S1 toggles — score before text enters the agent context
GUARD_INPUT = True
GUARD_RETRIEVED_CONTEXT = True  # search_docs / read_email / read_ticket outputs
GUARD_TOOL_OUTPUT = True  # other tool outputs (e.g. send_email / create_ticket)
# When retrieved/tool content is flagged: "drop" (replace) or "flag" (log only)
GUARD_CONTENT_ACTION = "drop"

SEARCH_TOP_K = 3
MAX_TOOL_ROUNDS = 4

# S2 privileged planner (P-LLM) — plans before reading untrusted content
PLANNER_MODEL = OLLAMA_MODEL
MAX_PLAN_STEPS = 6
