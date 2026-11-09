from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "data" / "synthetic" / "docs"
EMAILS_PATH = PROJECT_ROOT / "data" / "synthetic" / "emails" / "emails.json"
EMAIL_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "email_sink.jsonl"
TICKETS_PATH = PROJECT_ROOT / "data" / "synthetic" / "tickets" / "tickets.json"
TICKET_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "ticket_sink.jsonl"

OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "lfm2.5-thinking:latest"

SEARCH_TOP_K = 3
MAX_TOOL_ROUNDS = 4
