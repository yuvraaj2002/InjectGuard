from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "data" / "synthetic" / "docs"
POLICY_ACCESS_PATH = PROJECT_ROOT / "data" / "synthetic" / "policy_access.json"
DISPUTES_PATH = PROJECT_ROOT / "data" / "synthetic" / "disputes" / "disputes.json"
ACCOUNTS_PATH = PROJECT_ROOT / "data" / "synthetic" / "accounts" / "accounts.json"
PAYEES_PATH = PROJECT_ROOT / "data" / "synthetic" / "payees" / "payees.json"
TRANSFER_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "transfer_sink.jsonl"
REFUND_SINK_PATH = PROJECT_ROOT / "data" / "synthetic" / "refund_sink.jsonl"

# Stand-in for "resolved from auth token" until real auth exists.
DEFAULT_USER_ID = "op-001"

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

# S1 toggles — user-message gate is always on; enable later stages after that lands.
GUARD_RETRIEVED_CONTEXT = False  # TODO: score search_policies / read_dispute / … before re-entry
GUARD_TOOL_OUTPUT = False  # TODO: score transfer/refund confirmations before re-entry
# When retrieved/tool content is flagged: "drop" (replace) or "flag" (log only)
GUARD_CONTENT_ACTION = "drop"

SEARCH_TOP_K = 5
MAX_TOOL_ROUNDS = 4

# S2 privileged planner (P-LLM) — plans before reading untrusted content
PLANNER_MODEL = OLLAMA_MODEL
MAX_PLAN_STEPS = 6

# S2 quarantined extractor (Q-LLM) — schema-only, no tools
QUARANTINE_MODEL = OLLAMA_MODEL
QUARANTINE_MAX_INPUT_CHARS = 8000
