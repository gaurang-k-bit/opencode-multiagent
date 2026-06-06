# import requests
# import subprocess
# import time
# import json
# import csv
# import os
# from datetime import datetime, timezone

# BASE_URL = "http://localhost:4096"
# TESTS_FILE = "tests.csv"
# RESULTS_FILE = "results.json"


# def start_server() -> subprocess.Popen:
#     proc = subprocess.Popen(
#         "opencode serve",
#         shell=True,
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL
#     )
#     print("Waiting for OpenCode server to start...")
#     for _ in range(15):
#         try:
#             resp = requests.get(f"{BASE_URL}/global/health", timeout=2)
#             if resp.status_code == 200:
#                 print("OpenCode server ready.\n")
#                 return proc
#         except requests.ConnectionError:
#             pass
#         time.sleep(2)
#     raise RuntimeError("OpenCode server failed to start after 30 seconds.")


# def run_query(query: str, timeout: int = 300) -> tuple[str, list, float]:
#     """
#     Sends a query to the router agent and returns:
#       - detected_agent: which subagent was actually invoked ("pdf-agent", "markdown-agent", or "none")
#       - agents_invoked: list of all subagents that were spawned
#       - duration: time taken in seconds

#     Detection uses SubtaskPart from the message history — these only appear
#     when a subagent is genuinely spawned via the Task tool, never from text mentions.
#     """
#     start = time.time()

#     # 1. Create a new session
#     session_resp = requests.post(f"{BASE_URL}/session").json()
#     session_id = session_resp["id"]

#     # 2. Send query to router — this call blocks until the response is complete
#     requests.post(
#         f"{BASE_URL}/session/{session_id}/message",
#         json={
#             "parts": [{"type": "text", "text": query}],
#             "agent": "router"
#         },
#         timeout=timeout
#     )

#     duration = round(time.time() - start, 2)

#     # 3. Fetch message history and look for SubtaskParts
#     # SubtaskPart.agent is only set when the Task tool actually invokes a subagent
#     messages_resp = requests.get(
#         f"{BASE_URL}/session/{session_id}/message"
#     ).json()

#     children_resp = requests.get(
#     f"{BASE_URL}/session/{session_id}/children"
#     ).json()

#     # print("CHILDREN SESSIONS:", json.dumps(children_resp, indent=2)[:1000])
#     # print("RAW MESSAGES:", json.dumps(messages_resp, indent=2)[:2000])

#     # for message in messages_resp:
#     #     for part in message.get("parts", []):
#     #         print(f"  PART TYPE: {part.get('type')} | KEYS: {list(part.keys())}")

#     agents_invoked = []
#     for message in messages_resp:
#         for part in message.get("parts", []):
#             if part.get("type") == "tool" and part.get("tool") == "task":
#                 state = part.get("state", {})
#                 inp = state.get("input", {})
#                 agent = inp.get("subagent_type", "") or inp.get("agent", "")
#                 if agent and agent not in agents_invoked:
#                     agents_invoked.append(agent)

#     # Fallback: check child sessions directly
#     if not agents_invoked:
#         children = requests.get(f"{BASE_URL}/session/{session_id}/children").json()
#         for child in children:
#             agent = child.get("agent", "")
#             if agent and agent not in agents_invoked:
#                 agents_invoked.append(agent)

#     # Determine the primary detected agent
#     detected_agent = "none"
#     for agent in agents_invoked:
#         if agent in ("pdf-agent", "markdown-agent"):
#             detected_agent = agent
#             break

#     return detected_agent, agents_invoked, duration


# def load_test_cases(filepath: str) -> list[dict]:
#     if not os.path.exists(filepath):
#         raise FileNotFoundError(
#             f"Test file '{filepath}' not found. "
#             "Please create a tests.csv with columns: query, expected_agent"
#         )
#     test_cases = []
#     with open(filepath, newline="", encoding="utf-8") as f:
#         reader = csv.DictReader(f)
#         for i, row in enumerate(reader, start=1):
#             if "query" not in row or "expected_agent" not in row:
#                 raise ValueError("CSV must have 'query' and 'expected_agent' columns.")
#             test_cases.append({
#                 "index": i,
#                 "query": row["query"].strip(),
#                 "expected": row["expected_agent"].strip().lower()
#             })
#     return test_cases


# def run_evaluation():
#     server = start_server()

#     try:
#         print("Loading test cases...")
#         test_cases = load_test_cases(TESTS_FILE)
#         print(f"Found {len(test_cases)} test cases.\n")

#         results = []
#         passed = 0
#         failed = 0

#         for case in test_cases:
#             index = case["index"]
#             query = case["query"]
#             expected = case["expected"]

#             print(f"[{index}/{len(test_cases)}] Running: \"{query}\"")

#             # Use a longer timeout for PDF queries
#             timeout = 600 if "pdf" in query.lower() else 180

#             try:
#                 actual, agents_invoked, duration = run_query(query, timeout=timeout)
#             except requests.Timeout:
#                 print(f"  TIMED OUT\n")
#                 actual, agents_invoked, duration = "none", [], float(timeout)

#             did_pass = actual == expected
#             status = "PASS" if did_pass else "FAIL"
#             if did_pass:
#                 passed += 1
#             else:
#                 failed += 1

#             print(f"  Agents invoked: {agents_invoked}")
#             print(f"  Expected: {expected} | Actual: {actual} | {status} | {duration}s\n")

#             results.append({
#                 "index": index,
#                 "query": query,
#                 "expected": expected,
#                 "actual": actual,
#                 "agents_invoked": agents_invoked,
#                 "passed": did_pass,
#                 "duration_seconds": duration
#             })

#     finally:
#         print("Shutting down OpenCode server...")
#         server.terminate()

#     total = len(test_cases)
#     accuracy = round((passed / total) * 100, 1) if total > 0 else 0.0

#     output_data = {
#         "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
#         "total": total,
#         "passed": passed,
#         "failed": failed,
#         "accuracy": accuracy,
#         "results": results
#     }

#     with open(RESULTS_FILE, "w", encoding="utf-8") as f:
#         json.dump(output_data, f, indent=2)

#     print("=" * 50)
#     print(f"Evaluation complete.")
#     print(f"Total:    {total}")
#     print(f"Passed:   {passed}")
#     print(f"Failed:   {failed}")
#     print(f"Accuracy: {accuracy}%")
#     print(f"Results saved to {RESULTS_FILE}")
#     print("=" * 50)


# if __name__ == "__main__":
#     run_evaluation()












import requests
import subprocess
import time
import json
import csv
import os
from datetime import datetime, timezone

BASE_URL = "http://localhost:4096"
TESTS_FILE = "tests.csv"
RESULTS_FILE = "results.json"


def start_server() -> subprocess.Popen:
    proc = subprocess.Popen(
        "opencode serve",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("Waiting for OpenCode server to start...")
    for _ in range(15):
        try:
            resp = requests.get(f"{BASE_URL}/global/health", timeout=2)
            if resp.status_code == 200:
                print("OpenCode server ready.\n")
                return proc
        except requests.ConnectionError:
            pass
        time.sleep(2)
    raise RuntimeError("OpenCode server failed to start after 30 seconds.")


def get_router_response_text(messages_resp: list) -> str:
    """Extract the final text response from the router."""
    for message in reversed(messages_resp):
        if message.get("info", {}).get("role") == "assistant":
            for part in message.get("parts", []):
                if part.get("type") == "text" and part.get("text"):
                    return part["text"].strip().lower()
    return ""


def evaluate_routing(messages_resp: list, children: list) -> tuple[str, bool]:
    """
    Layer 1: Did the router select the correct agent?
    Returns (actual_agent, routing_passed).
    Checks tool parts first, then falls back to child sessions.
    """
    # Check tool parts for Task tool invocations
    for message in messages_resp:
        for part in message.get("parts", []):
            if part.get("type") == "tool" and part.get("tool") == "task":
                state = part.get("state", {})
                inp = state.get("input", {})
                agent = inp.get("subagent_type", "") or inp.get("agent", "")
                if agent in ("pdf-agent", "markdown-agent"):
                    return agent, True

    # Fallback: check child sessions
    # The fallback exists because of a timing issue: the POST /session/{sessionID}/message call 
    # might return before the child session is fully registered, meaning the tool part might not yet appear in the message history when we fetch it
    for child in children:
        agent = child.get("agent", "")
        if agent in ("pdf-agent", "markdown-agent"):
            return agent, True

    # Check for fallback phrase (none case)
    router_text = get_router_response_text(messages_resp)

    print(f"  Router text: '{router_text[:100]}'")

    if "sorry. i cannot help you with that" in router_text:
        return "none", True

    return "none", False


def evaluate_completion(
    expected: str,
    actual_agent: str,
    children: list,
    messages_resp: list
) -> tuple[bool, str]:
    """
    Layer 2: Did the selected agent successfully complete the task?
    Returns (completion_passed, evidence).
    """
    # For none cases, just verify the fallback phrase was returned
    if expected == "none":
        router_text = get_router_response_text(messages_resp)
        if "sorry. i cannot help you with that" in router_text:
            return True, "Router correctly returned fallback phrase"
        return False, "Router did not return expected fallback phrase"

    # For agent cases, routing must have succeeded first
    if actual_agent != expected:
        return False, f"Wrong agent invoked: expected {expected}, got {actual_agent}"

    # Find the child session for the invoked agent
    child_session = next(
        (c for c in children if c.get("agent") == actual_agent), None
    )

    if not child_session:
        return False, "Child session not found for invoked agent"

    # Check the child session completed without error
    child_id = child_session["id"]
    child_messages = requests.get(
        f"{BASE_URL}/session/{child_id}/message"
    ).json()

    # Look for any error parts in child messages
    for message in child_messages:
        if message.get("info", {}).get("error"):
            error = message["info"]["error"]
            return False, f"Agent error: {error.get('name', 'unknown')}"

    # Check files were actually created/modified
    summary = child_session.get("summary", {})
    files_changed = summary.get("files", 0)
    additions = summary.get("additions", 0)

    if files_changed > 0 or additions > 0:
        return True, f"Task completed: {files_changed} file(s) modified, {additions} line(s) added"

    # Final fallback: check child session has meaningful token usage
    tokens = child_session.get("tokens", {})
    output_tokens = tokens.get("output", 0)
    if output_tokens > 50:
        return True, f"Task completed: agent produced {output_tokens} output tokens"

    return False, "No files created or modified by agent"


def run_query(query: str, timeout: int = 300) -> dict:
    """
    Runs a query and returns a result dict with separate routing and completion evaluations.
    """
    start = time.time()

    # 1. Create a new session
    session_resp = requests.post(f"{BASE_URL}/session").json()
    session_id = session_resp["id"]

    # 2. Send query to router - blocks until complete
    try:
        requests.post(
            f"{BASE_URL}/session/{session_id}/message",
            json={
                "parts": [{"type": "text", "text": query}],
                "agent": "router"
            },
            timeout=timeout
        )
    except requests.Timeout:
        duration = round(time.time() - start, 2)
        return {
            "routing": {"actual": "none", "passed": False},
            "completion": {"passed": False, "evidence": "Request timed out"},
            "duration_seconds": duration
        }

    duration = round(time.time() - start, 2)

    # 3. Fetch message history and child sessions
    messages_resp = requests.get(
        f"{BASE_URL}/session/{session_id}/message"
    ).json()
    children = requests.get(
        f"{BASE_URL}/session/{session_id}/children"
    ).json()

    return {
        "messages": messages_resp,
        "children": children,
        "duration_seconds": duration
    }


def load_test_cases(filepath: str) -> list[dict]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Test file '{filepath}' not found. "
            "Please create a tests.csv with columns: query, expected_agent"
        )
    test_cases = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            if "query" not in row or "expected_agent" not in row:
                raise ValueError("CSV must have 'query' and 'expected_agent' columns.")
            test_cases.append({
                "index": i,
                "query": row["query"].strip(),
                "expected": row["expected_agent"].strip().lower()
            })
    return test_cases


def run_evaluation():
    server = start_server()

    try:
        print("Loading test cases...")
        test_cases = load_test_cases(TESTS_FILE)
        print(f"Found {len(test_cases)} test cases.\n")

        results = []
        routing_passed = 0
        completion_passed = 0

        for case in test_cases:
            index = case["index"]
            query = case["query"]
            expected = case["expected"]

            print(f"[{index}/{len(test_cases)}] Running: \"{query}\"")

            timeout = 600 if "pdf" in query.lower() else 180

            raw = run_query(query, timeout=timeout)

            # Handle timeout case
            if "routing" in raw:
                actual_agent = raw["routing"]["actual"]
                routing_ok = raw["routing"]["passed"]
                completion_ok = raw["completion"]["passed"]
                completion_evidence = raw["completion"]["evidence"]
            else:
                messages_resp = raw["messages"]
                children = raw["children"]
                duration = raw["duration_seconds"]

                actual_agent, routing_ok = evaluate_routing(messages_resp, children)
                completion_ok, completion_evidence = evaluate_completion(
                    expected, actual_agent, children, messages_resp
                )

            duration = raw.get("duration_seconds", 0)

            # Overall pass requires both routing and completion to pass
            overall_passed = routing_ok and completion_ok
            if routing_ok:
                routing_passed += 1
            if completion_ok:
                completion_passed += 1

            routing_status = "PASS" if routing_ok else "FAIL"
            completion_status = "PASS" if completion_ok else "FAIL"

            print(f"  Routing:    Expected={expected} | Actual={actual_agent} | {routing_status}")
            print(f"  Completion: {completion_status} - {completion_evidence}")
            print(f"  Duration:   {duration}s\n")

            results.append({
                "index": index,
                "query": query,
                "expected": expected,
                "routing": {
                    "actual": actual_agent,
                    "passed": routing_ok
                },
                "completion": {
                    "passed": completion_ok,
                    "evidence": completion_evidence
                },
                "overall_passed": overall_passed,
                "duration_seconds": duration
            })

    finally:
        print("Shutting down OpenCode server...")
        server.terminate()

    total = len(test_cases)
    overall_passed_count = sum(1 for r in results if r["overall_passed"])
    accuracy = round((overall_passed_count / total) * 100, 1) if total > 0 else 0.0
    routing_accuracy = round((routing_passed / total) * 100, 1) if total > 0 else 0.0
    completion_accuracy = round((completion_passed / total) * 100, 1) if total > 0 else 0.0

    output_data = {
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": total,
        "overall_passed": overall_passed_count,
        "overall_accuracy": accuracy,
        "routing_accuracy": routing_accuracy,
        "completion_accuracy": completion_accuracy,
        "results": results
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print("=" * 50)
    print(f"Evaluation complete.")
    print(f"Total:               {total}")
    print(f"Overall passed:      {overall_passed_count}")
    print(f"Overall accuracy:    {accuracy}%")
    print(f"Routing accuracy:    {routing_accuracy}%")
    print(f"Completion accuracy: {completion_accuracy}%")
    print(f"Results saved to {RESULTS_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    run_evaluation()