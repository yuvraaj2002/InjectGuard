import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines into the environment. Existing vars win. Never logs values."""
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(PROJECT_ROOT / ".env")
DOCS_DIR = PROJECT_ROOT / "data" / "synthetic" / "docs"
POLICY_ACCESS_PATH = PROJECT_ROOT / "data" / "synthetic" / "policy_access.json"
DISPUTES_PATH = PROJECT_ROOT / "data" / "synthetic" / "disputes" / "disputes.json"
ACCOUNTS_PATH = PROJECT_ROOT / "data" / "synthetic" / "accounts" / "accounts.json"
PAYEES_PATH = PROJECT_ROOT / "data" / "synthetic" / "payees" / "payees.json"
TRANSFER_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "transfer_sink.jsonl"
REFUND_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "refund_sink.jsonl"

# Stand-in for "resolved from auth token" until real auth exists.
DEFAULT_USER_ID = "op-001"

# Chat models (planner, quarantine extractor, answer writer, baseline loop).
# Groq() reads GROQ_API_KEY from the environment loaded above.
GROQ_MODEL = "qwen/qwen3.8-27b"
GROQ_TEMPERATURE = 0.6
GROQ_MAX_COMPLETION_TOKENS = 2048
GROQ_TOP_P = 0.95
# "none" keeps day-to-day chats off the reasoning token budget.
GROQ_REASONING_EFFORT = "none"

# Legacy S1 decision LLM (System One) still talks to a local Ollama-compatible host.
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "lfm2.5-thinking:latest"

# S1 input classifier — Meta Llama Prompt Guard 2 (local mDeBERTa encoder, not an LLM).
# HF-gated: accept the model license, then `huggingface-cli login` (or set HF_TOKEN).
# Labels: BENIGN / MALICIOUS (or LABEL_0 / LABEL_1). Top label decides; score is logged only.
INPUT_CLASSIFIER_MODEL = "meta-llama/Llama-Prompt-Guard-2-86M"
INPUT_CLASSIFIER_MAX_LENGTH = 512

# Legacy S1 decision LLM (Ollama System One) — kept in decision_model_inference.py for ablation.
DECISION_MODEL = "tev1:0.8b"
DECISION_MODEL_TIMEOUT_S = 30.0
INJECTION_THRESHOLD = 0.45  # only used by DecisionModel (System One noul)

# One policy document per search while iterating, so the extractor is not handed five full files.
SEARCH_TOP_K = 1
MAX_TOOL_ROUNDS = 4

# S2 privileged planner (P-LLM) — plans before reading untrusted content
PLANNER_MODEL = GROQ_MODEL
MAX_PLAN_STEPS = 6

# S2 quarantined extractor (Q-LLM) — schema-only, no tools
QUARANTINE_MODEL = GROQ_MODEL
QUARANTINE_MAX_INPUT_CHARS = 8000
# Facts are a small JSON object. A large cap lets the extractor rewrite the whole document.
QUARANTINE_MAX_COMPLETION_TOKENS = 512
