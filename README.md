# OpenCode Multi-Agent Routing System

A multi-agent routing system built with OpenCode that automatically delegates user queries to specialized subagents, with an automated evaluation pipeline and CI/CD integration via GitHub Actions.

---

## System Architecture

The system follows a hub-and-spoke routing pattern:

```
User Query
    │
    ▼
┌─────────┐
│  Router  │  ← default agent, never performs tasks directly
└─────────┘
    │
    ├──── PDF query ──────► ┌───────────┐
    │                       │ pdf-agent │ → creates/reads PDF files
    │                       └───────────┘
    │
    ├──── Markdown query ──► ┌────────────────┐
    │                        │ markdown-agent │ → creates/reads .md files
    │                        └────────────────┘
    │
    └──── Neither ────────► "Sorry. I cannot help you with that."
```

**Router** — the default primary agent. Analyzes every query and delegates to the appropriate subagent. Never performs any actions itself. Strictly limited to invoking pdf-agent or markdown-agent only.

**PDF Agent** — subagent that handles all PDF creation and reading using Python with reportlab.

**Markdown Agent** — subagent that handles all Markdown file creation and reading.

---

## Evaluation System

The evaluator runs two distinct layers of assessment per query:

**Layer 1 — Routing Evaluation**: Did the router select the correct agent for the given input? Detected via Task tool call inspection in message parts, with child session fallback.

**Layer 2 — Completion Evaluation**: Did the selected agent successfully fulfill the task? Assessed by inspecting the child session for errors, file changes, and output tokens.

---

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── eval.yml              # CI/CD pipeline
├── .opencode/
│   └── agents/
│       ├── pdf-agent.md          # PDF subagent definition
│       └── markdown-agent.md    # Markdown subagent definition
├── opencode.json                 # Router agent + model config
├── evaluate.py                   # Evaluation runner
├── tests.csv                     # Test cases
├── results.json                  # Evaluation output (generated)
├── pyproject.toml                # Python dependencies (uv)
├── uv.lock                       # Locked dependency versions
└── README.md
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Evaluation runner |
| Node.js | 18+ | Required by OpenCode |
| OpenCode CLI | Latest | Multi-agent framework |
| uv | Latest | Python package manager |
| OpenCode Zen | — | Model provider (free tier available) |

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/gaurang-k-bit/opencode-multiagent.git
cd opencode-multiagent
```

### 2. Install uv

On Windows:
```bash
pip install uv
```

If `uv` is not recognized after install, use `python -m uv` instead, or install via the official installer at [astral.sh/uv](https://astral.sh/uv) which handles PATH automatically.

### 3. Install Python dependencies

```bash
uv sync
```

### 4. Install OpenCode

```bash
npm install -g opencode-ai
```

### 5. Set up OpenCode Zen

OpenCode Zen is the model provider used by all agents in this project.

> **Note:** OpenCode Zen requires an account and billing details at signup, even for free models. No charges are made for free tier usage.

1. Go to [opencode.ai/auth](https://opencode.ai/auth) and sign in
2. Add your billing details and copy your API key
3. In your terminal, from the project directory, run:
   ```bash
   opencode
   ```
4. Inside the TUI, run `/connect`, select **OpenCode Zen**, and paste your API key
5. Exit the TUI (`Ctrl+C`)

### 6. Verify setup

```bash
opencode run "What is the capital of France?"
```

You should see the router respond with `"Sorry. I cannot help you with that."` since this query doesn't match any subagent.

---

## Running Locally

```bash
uv run python evaluate.py
```

This will:
1. Start an OpenCode server on port 4096
2. Load test cases from `tests.csv`
3. Run each query through the router via the HTTP API
4. Evaluate routing and completion separately per query
5. Write results to `results.json`
6. Shut down the server

Results are printed to the terminal as the evaluation runs:

```
[1/13] Running: "Generate a 1 page PDF on the history of NASA"
  Routing:    Expected=pdf-agent | Actual=pdf-agent | PASS
  Completion: PASS - Task completed: 1 file(s) modified, 245 line(s) added
  Duration:   56.32s
```

---

## CI/CD Workflow

The GitHub Actions workflow (`.github/workflows/eval.yml`) runs automatically on every push to `main`, or can be triggered manually.

### Required GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** and add:

| Secret | Value |
|---|---|
| `OPENCODE_ZEN_API_KEY` | Your key from `opencode.ai/auth` |
| `EMAIL_USERNAME` | Your Gmail address |
| `EMAIL_APP_PASSWORD` | Gmail App Password (see below) |

`EMAIL_TO` is not required as a secret — when triggering manually you'll be prompted to enter a recipient email directly in the GitHub Actions UI.

### Getting a Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com) → **Security**
2. Ensure **2-Step Verification** is enabled
3. Search for **"App Passwords"** and open it
4. Enter any app name (e.g. `opencode-evaluator`) and click **Create**
5. Copy the 16-character password and add it as `EMAIL_APP_PASSWORD`

### Triggering manually

1. Go to your repo → **Actions** → **Multi-Agent Evaluation**
2. Click **Run workflow**
3. Enter the recipient email address
4. Click **Run workflow**

On completion, results are emailed to the specified address and uploaded as an artifact in the Actions run. The email includes overall accuracy, routing accuracy, and completion accuracy.

---

## Implemented Requirements

- ✅ Router agent that delegates to subagents and never acts itself
- ✅ Strict routing — router can only invoke pdf-agent or markdown-agent, all other agents denied
- ✅ PDF subagent that creates and reads PDF files using reportlab
- ✅ Markdown subagent that creates and reads Markdown files
- ✅ Explicit predefined execution steps for both subagents
- ✅ Fallback response for out-of-scope queries
- ✅ Two-layer evaluation: routing accuracy and completion accuracy measured independently
- ✅ Evaluation system reading from CSV with 13 test cases
- ✅ Results written to `results.json` with per-query routing and completion results
- ✅ GitHub Actions workflow triggered on push to main and manually
- ✅ Email results on completion with `results.json` attached
- ✅ Reproducible Python environment managed with uv
- ✅ Fully runnable locally without GitHub Actions

## Unimplemented Requirements

- ❌ Locally running model (bonus) — all agents use OpenCode Zen cloud models

---

## Challenges

**Agent detection** — OpenCode's SubtaskPart (which would indicate subagent invocation) was not appearing in message history. Detection was moved to Task tool call inspection in message parts and child session inspection, which are reliable structured signals rather than text parsing.

**Custom subagent invocation** — Custom agents defined in `opencode.json` with `mode: subagent` are not exposed in the Task tool's available agents list (known OpenCode bug). Fix was to define subagents exclusively as markdown files in `.opencode/agents/`.

**Router hallucination** — Early versions of the router would narrate delegating to a subagent without actually doing it. Fixed by making the router system prompt explicitly forbid the router from taking any actions and restricting task permissions to only pdf-agent and markdown-agent.

**Windows subprocess encoding** — OpenCode outputs UTF-8 including TUI characters that Windows cp1252 can't decode. Fixed by explicitly passing `encoding="utf-8"` and `errors="replace"` to subprocess calls.

**PDF frontmatter parsing** — Em dashes in the pdf-agent markdown file caused OpenCode to fail parsing the YAML frontmatter, resulting in the agent being registered with `mode: all` and no description. Fixed by replacing em dashes with plain hyphens.

**Windows PATH with uv** — `pip install uv` doesn't automatically add uv to PATH on Windows. Use `python -m uv` locally or install via the official installer at [astral.sh/uv](https://astral.sh/uv) to avoid PATH issues. In GitHub Actions, the `astral-sh/setup-uv` action handles PATH automatically.