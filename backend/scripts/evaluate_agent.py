"""Run the bilingual live-agent acceptance corpus against a running API.

Requires AGENT_EVAL_TOKEN. Example:
    uv run python scripts/evaluate_agent.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import httpx


DEFAULT_CASES = Path(__file__).parents[1] / "evals" / "sales_agent_cases.json"


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and all(item in actual for item in expected)
    return actual == expected


def _turn_passed(payload: dict[str, Any], expected: dict[str, Any]) -> bool:
    message = str(payload.get("message") or "")
    has_markdown_table = any(
        line.strip().startswith("|") and line.strip().endswith("|")
        for line in message.splitlines()
    )
    if has_markdown_table:
        return False

    expected_tool = expected.get("tool")
    calls = payload.get("tool_calls") or []
    analytics = [call for call in calls if call.get("tool_name") != "resolve_product"]
    if expected_tool is None:
        tool_ok = not analytics
    else:
        call = next(
            (item for item in analytics if item.get("tool_name") == expected_tool),
            None,
        )
        tool_ok = call is not None and _contains(
            call.get("arguments") or {},
            expected.get("args") or {},
        )
    if not tool_ok:
        return False
    render_as = expected.get("render_as")
    if render_as is not None:
        return any(
            display.get("render_as") == render_as
            for display in payload.get("displays") or []
        )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--followup-threshold", type=float, default=0.90)
    args = parser.parse_args()

    token = os.getenv("AGENT_EVAL_TOKEN", "").strip()
    if not token:
        raise SystemExit("AGENT_EVAL_TOKEN is required")
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    results: list[tuple[str, str, bool]] = []

    with httpx.Client(
        base_url=args.base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=90,
    ) as client:
        for case in cases:
            conversation_id = None
            passed = True
            for turn in case["turns"]:
                response = client.post(
                    "/agent/query",
                    json={
                        "message": turn["message"],
                        "conversation_id": conversation_id,
                        "language": case["language"],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                conversation_id = payload["conversation_id"]
                passed = passed and _turn_passed(payload, turn)
            results.append((case["id"], case["group"], passed))
            print(f"{'PASS' if passed else 'FAIL'} {case['id']}")

    core = [passed for _, group, passed in results if group == "core"]
    followups = [passed for _, group, passed in results if group == "followup"]
    core_rate = sum(core) / len(core) if core else 0.0
    followup_rate = sum(followups) / len(followups) if followups else 0.0
    print(f"core={core_rate:.1%} ({sum(core)}/{len(core)})")
    print(f"followup={followup_rate:.1%} ({sum(followups)}/{len(followups)})")
    return 0 if core_rate == 1.0 and followup_rate >= args.followup_threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
