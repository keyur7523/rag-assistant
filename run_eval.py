"""Evaluation harness for the Northwind support agent.

Runs every case in eval_cases.py through the agent and scores two things
independently:

  trajectory - did the agent call the tools it needed?
  outcome    - did the final answer contain the expected facts?

Both matter. An agent that produces the right answer without calling the
right tools got there by guessing, which is a bug even though the text
looks correct.

Usage:
    python run_eval.py                 # run every case
    python run_eval.py chaining        # run only one category
    python run_eval.py chaining action # run several categories
"""

import json
import sys
from collections import defaultdict
from datetime import datetime

from agent import run_agent
from eval_cases import EVAL_CASES

RESULTS_DIR = "eval_results"


def score(case, answer, tool_names, hit_iteration_cap):
    """Return (passed, [reasons]) for a single completed run."""
    reasons = []

    expected_tools = set(case["expect_tools"])
    actual_tools = set(tool_names)

    # An empty expectation is treated strictly: the agent should not have
    # reached for any tool. Answering a greeting with a vector search is
    # wasteful behaviour worth catching, not a free pass.
    if expected_tools:
        missing_tools = expected_tools - actual_tools
        if missing_tools:
            reasons.append(f"missing tools: {sorted(missing_tools)}")
    elif actual_tools:
        reasons.append(f"expected no tool calls, got: {sorted(actual_tools)}")

    # Case-insensitive substring match. Phrasing varies between runs, so the
    # keywords are deliberately short and distinctive rather than full
    # sentences.
    lowered = answer.lower()
    missing_keywords = []
    for k in case["expect_keywords"]:
        if isinstance(k, str):
            if k.lower() not in lowered: 
                missing_keywords.append(k)
        else:
            if not any(i.lower() in lowered for i in k):
                missing_keywords.append(k)

    # missing_keywords = [k for k in case["expect_keywords"] if k.lower() not in lowered]
    if missing_keywords:
        reasons.append(f"missing keywords: {missing_keywords}")

    # Running out of turns is a distinct failure from a wrong answer: the
    # agent never finished, so whatever it produced is partial.
    if hit_iteration_cap:
        reasons.append("hit iteration cap without finishing")

    return (not reasons), reasons


def main():
    categories = set(sys.argv[1:])
    cases = [c for c in EVAL_CASES if not categories or c["category"] in categories]

    if not cases:
        print(f"No cases match {sorted(categories)}")
        return

    print(f"Running {len(cases)} case(s)\n")
    results = []

    for case in cases:
        # Printed before the run so an escaped crash or hang identifies itself.
        print(f"  {case['name']} ... ", end="", flush=True)

        try:
            answer, tools_used, iterations, hit_cap = run_agent(case["message"])
            tool_names = [name for name, _ in tools_used]
            passed, reasons = score(case, answer, tool_names, hit_cap)
        except Exception as e:
            # A test runner must survive anything a case throws, so the broad
            # catch is deliberate here. The error becomes a recorded failure
            # instead of ending the run.
            answer, tool_names, iterations = "", [], 0
            passed, reasons = False, [f"crashed: {type(e).__name__}: {e}"]

        print("PASS" if passed else "FAIL")
        for reason in reasons:
            print(f"      - {reason}")

        results.append(
            {
                "name": case["name"],
                "category": case["category"],
                "message": case["message"],
                "passed": passed,
                "reasons": reasons,
                "tools_called": tool_names,
                "iterations": iterations,
                "answer": answer,
            }
        )

    report(results)
    save(results)


def report(results):
    passed = sum(r["passed"] for r in results)
    total = len(results)

    by_category = defaultdict(lambda: [0, 0])
    for r in results:
        by_category[r["category"]][1] += 1
        if r["passed"]:
            by_category[r["category"]][0] += 1

    print("\n" + "=" * 46)
    print(f"{'OVERALL':<16}{passed:>3}/{total:<3}  {passed / total:.0%}")
    print("-" * 46)
    for category in sorted(by_category):
        got, of = by_category[category]
        print(f"{category:<16}{got:>3}/{of:<3}  {got / of:.0%}")
    print("=" * 46)

    failures = [r for r in results if not r["passed"]]
    if failures:
        print("\nFailed cases:")
        for r in failures:
            print(f"  {r['name']}: {'; '.join(r['reasons'])}")


def save(results):
    """Write the full run to a timestamped file.

    Keeping every run makes changes measurable: after tuning a prompt or the
    chunking strategy, diff the new results against the previous ones instead
    of relying on memory.
    """
    from pathlib import Path

    Path(RESULTS_DIR).mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(RESULTS_DIR) / f"eval-{stamp}.json"
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nFull results: {path}")


if __name__ == "__main__":
    main()
