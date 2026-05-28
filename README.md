# OpenCode Multi-Agent Routing System

A multi-agent routing system built with OpenCode that automatically delegates user queries to specialized subagents, with an automated evaluation pipeline and CI/CD integration via GitHub Actions.

---

## System Architecture

The system follows a router and subagent routing pattern:

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

**Router** — the default primary agent. Analyzes every query and delegates to the appropriate subagent. Never performs any actions itself.

**PDF Agent** — subagent that handles all PDF creation and reading using Python with reportlab.

**Markdown Agent** — subagent that handles all Markdown file creation and reading.

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
├── requirements.txt              # Python dependencies
└── README.md
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Evaluation runner |
| Node.js | 18+ | Required by OpenCode |
| OpenCode CLI | Latest | Multi-agent framework |
| OpenCode Zen | — | Model provider (free tier available) |

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/gaurang-k-bit/opencode-multiagent.git
cd opencode-multiagent
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install OpenCode

```bash
npm install -g opencode-ai
```

### 4. Set up OpenCode Zen

OpenCode Zen is the model provider used by all agents in this project.

> **Note:** OpenCode Zen requires an account and billing details to be added at signup, even for free models. No charges are made for free tier usage.

1. Go to [opencode.ai/auth](https://opencode.ai/auth) and sign in
2. Add your billing details and copy your API key
3. In your terminal, from the project directory, run:
   ```bash
   opencode
   ```
4. Inside the TUI, run `/connect`, select **OpenCode Zen**, and paste your API key
5. Exit the TUI (`Ctrl+C`)

### 5. Verify setup

```bash
opencode run "What is the capital of France?"
```

You should see the router respond with `"Sorry. I cannot help you with that."` since this query doesn't match any subagent.

---

## Running Locally

```bash
python evaluate.py
```

This will:
1. Load test cases from `tests.csv`
2. Run each query through OpenCode
3. Detect which subagent was invoked
4. Compare actual vs expected agent
5. Write results to `results.json`

Results are printed to the terminal as the evaluation runs:

```
[1/13] Running: "Generate a 1 page PDF on the history of NASA"
  Expected: pdf-agent | Actual: pdf-agent | PASS | 56.32s
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

On completion, results are emailed to the specified address and uploaded as an artifact in the Actions run.

---

## Implemented Requirements

- ✅ Router agent that delegates to subagents and never acts itself
- ✅ PDF subagent that creates and reads PDF files
- ✅ Markdown subagent that creates and reads Markdown files
- ✅ Fallback response for out-of-scope queries
- ✅ Evaluation system reading from CSV with 13 test cases
- ✅ Results written to `results.json` with accuracy, pass/fail, and duration
- ✅ GitHub Actions workflow triggered on push to main and manually
- ✅ Email results on completion with `results.json` attached
- ✅ Fully runnable locally without GitHub Actions

## Unimplemented Requirements

- ❌ Locally running model (bonus) — all agents use OpenCode Zen cloud models

---

## Challenges

**Agent detection** — OpenCode's output format isn't structured, so detecting which subagent was invoked relies on parsing stdout for agent name mentions. This is fragile if OpenCode changes its output format.

**Router hallucination** — Early versions of the router would narrate delegating to a subagent without actually doing it. Fixed by making the router system prompt explicitly forbid the router from taking any actions itself.

**Windows subprocess encoding** — OpenCode outputs UTF-8 including TUI characters that Windows cp1252 can't decode. Fixed by explicitly passing `encoding="utf-8"` and `errors="replace"` to subprocess.

**Timeout on complex queries** — PDF generation can take 2+ minutes. Fixed by adding a configurable per-query timeout with a higher default for PDF queries. Added explicit PDF generation instructions to PDF subagent to reduce thinking on how to generate. 
