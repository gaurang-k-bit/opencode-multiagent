import subprocess
import time
import json
import csv
import os
from datetime import datetime, timezone

import platform

OPENCODE_CMD = "opencode.cmd" if platform.system() == "Windows" else "opencode"


TESTS_FILE = "tests.csv"
RESULTS_FILE = "results.json"

def detect_agent(output: str) -> str:
    lower = output.lower()

    # Check if a subagent was explicitly invoked by name
    if "@pdf-agent" in lower or "→ pdf-agent" in lower or "pdf-agent" in lower:
        return "pdf-agent"
    if "@markdown-agent" in lower or "→ markdown-agent" in lower or "markdown-agent" in lower:
        return "markdown-agent"

    # Check what file types were actually created/written
    if any(x in lower for x in ["wrote", "write", "created", "generating"]):
        if any(x in lower for x in [".pdf", "pdf report", "pdf file"]):
            return "pdf-agent"
        if any(x in lower for x in [".md", "readme", "markdown"]):
            return "markdown-agent"

    # Fallback message
    if "sorry. i cannot help you with that" in lower:
        return "none"

    return "none"


def run_query(query: str) -> tuple[str, str, float]:
    """
    Runs a query through OpenCode and returns (detected_agent, raw_output, duration).
    """
    start = time.time()
    result = subprocess.run(
        f'opencode run "{query}"',  # string instead of list
        capture_output=True,
        text=True,
        shell=True,
        timeout=240,
        encoding="utf-8",        # force UTF-8 instead of Windows cp1252
        errors="replace"         # replace undecodable characters instead of crashing
    )
    duration = round(time.time() - start, 2)

    output = ((result.stdout or "") + (result.stderr or "")).lower()

    agent = detect_agent(output)

    return agent, result.stdout.strip(), duration


def load_test_cases(filepath: str) -> list[dict]:
    """
    Loads test cases from a CSV file with columns: query, expected_agent
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Test file '{filepath}' not found. "
            "Please create a tests.csv file with columns: query, expected_agent"
        )

    test_cases = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            if "query" not in row or "expected_agent" not in row:
                raise ValueError(
                    "CSV must have 'query' and 'expected_agent' columns."
                )
            test_cases.append({
                "index": i,
                "query": row["query"].strip(),
                "expected": row["expected_agent"].strip().lower()
            })

    return test_cases


def run_evaluation():
    print("Loading test cases...")
    test_cases = load_test_cases(TESTS_FILE)
    print(f"Found {len(test_cases)} test cases.\n")

    results = []
    passed = 0
    failed = 0

    for case in test_cases:
        index = case["index"]
        query = case["query"]

        expected = case["expected"]

        print(f"[{index}/{len(test_cases)}] Running: \"{query}\"")

        actual, output, duration = run_query(query)
        did_pass = actual == expected

        if did_pass:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"  Expected: {expected} | Actual: {actual} | {status} | {duration}s\n")

        results.append({
            "index": index,
            "query": query,
            "expected": expected,
            "actual": actual,
            "passed": did_pass,
            "duration_seconds": duration
        })

    total = len(test_cases)
    accuracy = round((passed / total) * 100, 1) if total > 0 else 0.0

    output_data = {
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "accuracy": accuracy,
        "results": results
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print("=" * 50)
    print(f"Evaluation complete.")
    print(f"Total:    {total}")
    print(f"Passed:   {passed}")
    print(f"Failed:   {failed}")
    print(f"Accuracy: {accuracy}%")
    print(f"Results saved to {RESULTS_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    run_evaluation()