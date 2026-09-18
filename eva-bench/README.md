<h1 align="center">Voice-Agent Evaluation with metrics from EVA<br />(End-to-end Framework for Evaluating Voice Agents)</h1>

> *This folder evaluates our voice agent using a selected subset of metrics from
> **EVA**. All of the evaluation metrics used here originate from EVA, and full
> credit for them belongs to the EVA authors and project.*

## 📢 Attribution & Credit

Everything in this folder that scores a conversation — every metric, its judge
prompt, its scoring rubric, and its validation logic — comes from **EVA (a New
End-to-end Framework for Evaluating Voice Agents)**. We did not invent these
metrics; we vendor them from EVA and use a subset of them to evaluate our own
voice agent.

**All credit for the evaluation metrics in this folder goes to EVA.**

- 📄 Paper: [arXiv:2605.13841](https://arxiv.org/abs/2605.13841)
- 🌐 Website: [servicenow.github.io/eva](https://servicenow.github.io/eva/)
- 🏆 Leaderboard: [servicenow.github.io/eva/#results](https://servicenow.github.io/eva/#results)
- 📦 Dataset: [ServiceNow-AI/eva-bench](https://huggingface.co/datasets/ServiceNow-AI/eva-bench)
- 💻 Source: [github.com/ServiceNow/eva](https://github.com/ServiceNow/eva)

If you use the metrics in this folder, please cite and credit EVA. See
[`README.md`](README.md) for the upstream EVA documentation.

---

## What EVA is

**EVA** is an open-source evaluation framework for conversational voice agents
that scores complete, multi-turn spoken conversations across two fundamental
dimensions:

- 🎯 **EVA-A (Accuracy)** — Did the agent complete the task correctly and faithfully?
- ✨ **EVA-X (Experience)** — Was the interaction natural, concise, and appropriate for spoken dialogue?

EVA evaluates agents using a **bot-to-bot audio architecture** — no human
listeners, no text replays. Two conversational AIs speak to each other over a
live connection, producing realistic speech-to-speech interactions that capture
real STT behavior and turn-taking dynamics.

| Component | Role |
|---|---|
| 🎭 **User Simulator** (ElevenLabs or OpenAI Realtime) | Plays the role of a caller with a defined goal and persona |
| 🤖 **Voice Agent** | The system under evaluation — here, our voice agent |
| 🔧 **Tool Executor** | Provides deterministic, reproducible tool responses via custom Python functions |
| ✅ **Validators** | Automated checks that verify conversations are complete and that the user simulator faithfully reproduced its intended goal |
| 📊 **Metrics Engine** | Scores each conversation using the audio recording, transcripts, and tool call logs |

## Why this folder exists

We run our own voice agent through EVA's bot-to-bot evaluation harness. Rather
than reporting EVA's full metric suite, we report a **focused subset** of EVA
metrics that matter most for our use case. The harness, dataset, user simulator,
validation gates, and metric implementations are all EVA's; our additions are the
runner that points EVA at our agent and the configuration that selects which EVA
metrics to report.

## 📊 The EVA metrics we use

We report the following **7 metrics, all from EVA**. Three feed EVA-A (Accuracy),
three feed EVA-X (Experience) — together they supply every component of EVA's
`EVA-A`, `EVA-X`, and `EVA-overall` composite scores — plus one diagnostic:

| Metric | EVA axis | Registered key | Type |
|---|---|---|---|
| **Task Completion** | 🎯 EVA-A · Accuracy | `task_completion` | Deterministic |
| **Faithfulness** | 🎯 EVA-A · Accuracy | `faithfulness` | LLM judge |
| **Agent Speech Fidelity** | 🎯 EVA-A · Accuracy | `agent_speech_fidelity` | Audio LLM judge `BETA` |
| **Conversation Progression** | ✨ EVA-X · Experience | `conversation_progression` | LLM judge |
| **Turn Taking** | ✨ EVA-X · Experience | `turn_taking` | LLM judge `BETA` |
| **Conciseness** | ✨ EVA-X · Experience | `conciseness` | LLM judge |
| **Response Speed** | Diagnostic | `response_speed` | Deterministic |

> Every one of these metrics is EVA's. See EVA's
> [Metrics documentation](docs/metrics/README.md) for the detailed scoring
> rubrics and judge prompts, and [MetricContext documentation](docs/metric_context.md)
> for the data structures they operate on.

EVA's **validation gates** (`conversation_valid_end`, `user_behavioral_fidelity`,
`user_speech_fidelity`) still run — they are part of EVA and ensure only clean,
correctly executed conversations enter evaluation. They run via a separate path
and are independent of the reported-metric selection above.

To restore EVA's full metric set, set `EVA_METRICS=all`.

<details>
<summary><h2>Quick Start</h2></summary>

### Installation

We recommend using [uv](https://docs.astral.sh/uv/) for fast, reliable dependency
management. If you don't have `uv` installed, see the
[uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

This project requires **Python 3.11–3.13** (set via `requires-python` in
`pyproject.toml`). `uv` will automatically select a compatible version.

```bash
cd eva-bench

# Install all dependencies (uv automatically creates a virtual environment)
uv sync --all-extras

# Copy environment template (lives at the repo root)
cp ../.env.example ../.env
# Edit .env with the API keys required by your selected providers
```

After installation, the normal way to run an evaluation is the scenario runner
(`guava_daytona_runner.py`) — see [Running our voice agent](#running-our-voice-agent)
below. It reads the repo-root `.env`, sets up the environment, and launches EVA
for you, so you don't need to activate the virtualenv or use the `eva` CLI
directly.

### Environment Variables

**Required:**
- `OPENAI_API_KEY` (or another LLM provider): Powers text judge metrics
- User simulation: `ELEVENLABS_API_KEY` + agent IDs for the default ElevenLabs caller
- STT/TTS API key and model as needed by your pipeline

**For the EVA metrics we report:**
- `OPENAI_API_KEY`: text judge metrics (task completion, conciseness, turn taking, conversation progression)
- `GOOGLE_APPLICATION_CREDENTIALS`: Gemini via Vertex AI (agent speech fidelity audio judge)
- `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`: Claude via Bedrock (faithfulness metric)

See `.env.example` at the repo root for the complete list of configuration
options.

### Running our voice agent

This is the primary way to run an evaluation. Start the agent's endpoint first,
then run the scenario runner from `eva-bench/`:

```bash
.venv/bin/python guava_daytona_runner.py [RECORD_ID] [NUM_TRIALS] [--domain DOMAIN]

# e.g. two trials of record 1.1.2 on the airline domain:
.venv/bin/python guava_daytona_runner.py 1.1.2 2 --domain airline
```

The runner reads the repo-root `.env`, sets `EVA_METRICS` to the 7 EVA metrics
above, and launches the EVA benchmark against the agent. No virtualenv activation
and no direct `eva` CLI use are required.

### Advanced: the EVA CLI directly

The runner wraps EVA's `eva` CLI, which you normally don't need. It's useful for a
few side cases — discovering flags (`eva --help`) or re-running metrics on an
existing run without re-simulating:

```bash
eva --run-id <existing_run_id> --metrics task_completion,faithfulness,conciseness
```

Two caveats when calling `eva` directly:

- **PATH:** bare `eva` only works with the virtualenv active. Otherwise use
  `uv run eva …` or the full path `.venv/bin/eva …`.
- **`.env` location:** the `eva` CLI reads `.env` from the current working
  directory, not the repo root. Run it from a folder that has a `.env`, or export
  the root one first: `set -a; . ../.env; set +a`. (The runner handles this for
  you.)

## Output Structure

```
output/<run_id>/
├── config.json              # Run configuration snapshot
├── results.csv              # Quick results table
├── metrics_summary.json     # Aggregate metrics (the reported EVA metrics)
├── metrics_summary.csv      # Per-category metrics breakdown
└── records/<record_id>/
    ├── result.json          # Conversation result
    ├── audio_assistant.wav  # Assistant audio channel
    ├── audio_user.wav       # User audio channel
    ├── audio_mixed.wav      # Mixed stereo audio
    ├── transcript.jsonl     # Turn-by-turn transcript
    ├── audit_log.json       # Complete interaction log
    ├── user_simulator_events.jsonl # Provider-neutral caller events
    └── metrics.json         # Per-record EVA metric scores and details
```

## Licensing & Citation

The evaluation framework and all metrics used in this folder are the work of the
EVA project. Please refer to EVA's repository for its license terms, and cite EVA
in any work that uses these metrics:

- Paper: [arXiv:2605.13841](https://arxiv.org/abs/2605.13841)
- Project: [github.com/ServiceNow/eva](https://github.com/ServiceNow/eva)
