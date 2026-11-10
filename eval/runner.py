"""Run attack cases from data/attacks/dataset.yaml against the vulnerable baseline.

Flow per case:
  1. Apply setup seeds (docs)
  2. Snapshot mock sinks
  3. Send payload to BaselineAgent
  4. Read sink delta
  5. Evaluate success_oracle → attack success yes/no
  6. Restore seeded files

Usage:
  PYTHONPATH=. python -m eval.runner
  PYTHONPATH=. python -m eval.runner --case c3_dispute_003_refund_attacker
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

from app.agent.baseline import BaselineAgent
from app.config import DOCS_DIR, OLLAMA_MODEL, PROJECT_ROOT
from eval.oracles import RunArtifacts, ToolCallView, evaluate_oracle
from eval.sinks import read_sink_delta, sink_snapshot

logger = logging.getLogger(__name__)

DEFAULT_DATASET = PROJECT_ROOT / "data" / "attacks" / "dataset.yaml"


@dataclass
class CaseResult:
    case_id: str
    category: str
    attack_succeeded: bool
    oracle_type: str
    reason: str
    reply: str
    tool_names: list[str] = field(default_factory=list)
    error: str | None = None


def load_dataset(path: Path = DEFAULT_DATASET) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"Invalid dataset file: {path}")
    return data


def runnable_cases(
    dataset: dict[str, Any],
    *,
    only_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case in dataset.get("cases") or []:
        if not isinstance(case, dict):
            continue
        if str(case.get("status", "")).lower() == "deferred":
            continue
        case_id = str(case.get("id", ""))
        if only_ids is not None and case_id not in only_ids:
            continue
        cases.append(case)
    return cases


@contextmanager
def apply_setup(setup: dict[str, Any] | None) -> Iterator[None]:
    """Temporarily seed docs listed in the case setup, then restore."""
    setup = setup or {}
    created_docs: list[Path] = []
    replaced_docs: list[tuple[Path, str]] = []

    try:
        for seed in setup.get("seed_docs") or []:
            relative = Path(str(seed["path"]))
            target = DOCS_DIR / relative.name
            content = str(seed.get("content") or "")
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
            if target.exists():
                replaced_docs.append((target, target.read_text(encoding="utf-8")))
            else:
                created_docs.append(target)
            target.write_text(content, encoding="utf-8")
            logger.info("seeded doc %s", target)

        yield
    finally:
        for path in created_docs:
            if path.exists():
                path.unlink()
                logger.info("removed seeded doc %s", path)
        for path, previous in replaced_docs:
            path.write_text(previous, encoding="utf-8")
            logger.info("restored doc %s", path)


def _normalize_payload(payload: Any) -> str:
    if payload is None:
        return ""
    return str(payload).strip()


def run_case(agent: BaselineAgent, case: dict[str, Any]) -> CaseResult:
    case_id = str(case.get("id", "unknown"))
    category = str(case.get("category", "?"))
    payload = _normalize_payload(case.get("payload"))
    oracle_spec = case.get("success_oracle") or {}

    try:
        with apply_setup(case.get("setup")):
            snapshot = sink_snapshot()
            chat = agent.chat(payload)
            delta = read_sink_delta(snapshot)

            artifacts = RunArtifacts(
                reply=chat.reply,
                tool_calls=[
                    ToolCallView(
                        name=call.name,
                        arguments=call.arguments,
                        output=call.output,
                    )
                    for call in chat.tool_calls
                ],
                sink_delta=delta,
                payload=payload,
            )
            oracle = evaluate_oracle(oracle_spec, artifacts)
            return CaseResult(
                case_id=case_id,
                category=category,
                attack_succeeded=oracle.succeeded,
                oracle_type=oracle.oracle_type,
                reason=oracle.reason,
                reply=chat.reply,
                tool_names=[call.name for call in chat.tool_calls],
            )
    except Exception as exc:  # noqa: BLE001 — surface per-case failures in the report
        logger.exception("case %s failed", case_id)
        return CaseResult(
            case_id=case_id,
            category=category,
            attack_succeeded=False,
            oracle_type=str(oracle_spec.get("type", "")),
            reason="runner error",
            reply="",
            error=str(exc),
        )


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    scored = [r for r in results if r.error is None]
    successes = sum(1 for r in scored if r.attack_succeeded)
    total = len(scored)
    by_category: dict[str, dict[str, int]] = {}
    for result in scored:
        bucket = by_category.setdefault(result.category, {"success": 0, "total": 0})
        bucket["total"] += 1
        if result.attack_succeeded:
            bucket["success"] += 1

    asr = (successes / total) if total else 0.0
    return {
        "total_cases": total,
        "errors": sum(1 for r in results if r.error is not None),
        "attack_successes": successes,
        "asr": asr,
        "by_category": {
            cat: {
                **counts,
                "asr": (counts["success"] / counts["total"]) if counts["total"] else 0.0,
            }
            for cat, counts in sorted(by_category.items())
        },
    }


def print_report(results: list[CaseResult], summary: dict[str, Any]) -> None:
    print("\n=== InjectGuard baseline attack run ===")
    for result in results:
        if result.error:
            status = "ERROR"
        elif result.attack_succeeded:
            status = "ATTACK_SUCCESS"
        else:
            status = "ATTACK_FAIL"
        tools = ",".join(result.tool_names) if result.tool_names else "-"
        print(
            f"[{status}] {result.case_id} ({result.category}) "
            f"oracle={result.oracle_type} tools={tools}"
        )
        print(f"  reason: {result.reason}")
        if result.error:
            print(f"  error: {result.error}")
        preview = " ".join(result.reply.split())
        if len(preview) > 160:
            preview = preview[:157] + "..."
        if preview:
            print(f"  reply: {preview}")

    print("\n--- Summary ---")
    print(
        f"ASR: {summary['asr']:.1%} "
        f"({summary['attack_successes']}/{summary['total_cases']} successes)"
    )
    if summary["errors"]:
        print(f"Errors: {summary['errors']}")
    for category, counts in summary["by_category"].items():
        print(
            f"  {category}: {counts['asr']:.1%} "
            f"({counts['success']}/{counts['total']})"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="InjectGuard attack eval runner")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to data/attacks/dataset.yaml",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Run only this case id (repeatable)",
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help=f"Ollama model (default: {OLLAMA_MODEL})",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    dataset = load_dataset(args.dataset)
    only_ids = set(args.case) if args.case else None
    cases = runnable_cases(dataset, only_ids=only_ids)
    if not cases:
        print("No runnable cases found.", file=sys.stderr)
        return 1

    print(f"Running {len(cases)} case(s) with model={args.model}")
    agent = BaselineAgent(model=args.model)
    results = [run_case(agent, case) for case in cases]
    summary = summarize(results)
    print_report(results, summary)

    report_path = PROJECT_ROOT / "eval" / "last_baseline_report.json"
    report_path.write_text(
        json.dumps(
            {
                "model": args.model,
                "dataset": str(args.dataset),
                "summary": summary,
                "results": [result.__dict__ for result in results],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
