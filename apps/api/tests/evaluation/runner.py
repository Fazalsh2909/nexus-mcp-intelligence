"""Evaluation runner.

Executes every scenario in scenarios.py through the real orchestration
engine and scores each one on (a) which tools it requested and (b) whether
the final answer contains the expected phrases. Writes a human-readable
report to stdout and returns a non-zero exit code when any scenario fails.

Usage:
    python -m tests.evaluation.runner          # all scenarios
    python -m tests.evaluation.runner slack_   # scenarios whose name starts with the arg
"""

import asyncio
import sys
from typing import Any, Dict, List

from sqlalchemy import select
from uuid import uuid4

from app.db.session import async_session
from app.models.models import ChatSession, User
from app.orchestration.engine import orchestrate
from tests.evaluation.scenarios import EVALUATION_SCENARIOS


def _matches(name: str, filters: List[str]) -> bool:
    return not filters or any(name.startswith(f) for f in filters)


def _score_scenario(
    scenario: Dict[str, Any], events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    requested = {
        e["tool"] for e in events if e["type"] in ("tool_start", "confirmation_request")
    }
    answered_tokens = "".join(
        e["content"] for e in events if e["type"] == "token"
    ).lower()
    confirmed = any(e["type"] == "confirmation_request" for e in events)

    checks: List[str] = []
    failures: List[str] = []

    for expected in scenario.get("expected_tools", []):
        if expected in requested:
            checks.append(f"tool {expected} requested")
        else:
            failures.append(f"expected tool {expected} was not requested")

    if scenario.get("expected_confirmation"):
        if confirmed:
            checks.append("write action intercepted for confirmation")
        else:
            failures.append("expected a confirmation request for the write action")

    for phrase in scenario.get("expected_answer_contains", []):
        if phrase.lower() in answered_tokens:
            checks.append(f'answer contains "{phrase}"')
        else:
            failures.append(f'answer missing "{phrase}"')

    return {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "requested": sorted(requested),
        "confirmed": confirmed,
    }


async def _run_scenario(
    scenario: Dict[str, Any], user: User, org_id: str
) -> Dict[str, Any]:
    async with async_session() as db:
        session = ChatSession(
            id=uuid4(), user_id=user.id, organization_id=org_id, title=scenario["name"]
        )
        db.add(session)
        await db.flush()
        await db.commit()

        events: List[Dict[str, Any]] = []
        async for event in orchestrate(
            scenario["question"],
            str(session.id),
            str(user.id),
            org_id,
            db,
        ):
            events.append(event)

        result = _score_scenario(scenario, events)
        result["events"] = events
        return result


async def main(filters: List[str]) -> int:
    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.email == "uitest@example.com")
        )
        user = result.scalar_one_or_none()
        if user is None:
            result = await db.execute(
                select(User).where(User.email == "fazal@example.com")
            )
            user = result.scalar_one_or_none()
        if user is None:
            print("No test user found; cannot run evaluation.")
            return 2
        org_id = str(user.organization_id)

    scenarios = [s for s in EVALUATION_SCENARIOS if _matches(s["name"], filters)]
    print(f"Running {len(scenarios)} scenarios as {user.email}...\n")

    passed = 0
    for scenario in scenarios:
        try:
            outcome = await _run_scenario(scenario, user, org_id)
        except Exception as exc:  # orchestrate raised outright
            print(f"[ERROR] {scenario['name']}: {type(exc).__name__}: {exc}")
            continue

        status = "PASS" if outcome["pass"] else "FAIL"
        passed += 1 if outcome["pass"] else 0
        print(f"[{status}] {scenario['name']} ({scenario['category']})")
        print(f"    tools requested: {', '.join(outcome['requested']) or '(none)'}")
        for check in outcome["checks"]:
            print(f"    + {check}")
        for failure in outcome["failures"]:
            print(f"    - {failure}")
        if scenario["name"] in ("write_confirmation", "hubspot_note_confirmation"):
            print(f"    confirmation intercepted: {outcome['confirmed']}")

    print(f"\n{passed}/{len(scenarios)} scenarios passed")
    return 0 if passed == len(scenarios) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
