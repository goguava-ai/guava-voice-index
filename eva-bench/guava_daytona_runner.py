"""Guava Daytona scenario runner — paper-faithful k-trial run.

Runs one or more records against a Guava Daytona voice bot
reached at a WebSocket endpoint (default ws://localhost:8765/ws), with the
ElevenLabs ElevenAgents user simulator as the caller:

  * assistant = EVA_FRAMEWORK=guava_daytona -> GuavaDaytonaAssistantServer.
  * caller    = ElevenLabs ElevenAgents user simulator (paper cascade: Scribe
    v2.2 Realtime + GPT-5.1 + Eleven v3 Conversational). Agent IDs come from
    EVA_EN_USER_{F,M} in .env; the gender is read from the record's persona.

Prerequisite — start the Guava Daytona endpoint first, then run this script. It
preflight-checks that the endpoint is reachable and exits early with
instructions if it isn't.

Paper-faithful trial handling: invalid (simulator-error) trials are archived and
regenerated up to --reruns times, and metrics + pass@k/pass^k are computed on the
k valid trials.

Usage:
    .venv/bin/python guava_daytona_runner.py [RECORD_ID] [NUM_TRIALS]
                                               [--domain DOMAIN] [--endpoint URL]
                                               [--alias NAME] [--concurrency N]
                                               [--reruns N] [--time-limit S]

    RECORD_ID       record id, or comma-separated list  (default: 1.1.2)
    NUM_TRIALS      k, valid trials to collect          (default: 5)
    --domain        EVA domain: airline | itsm | medical_hr (default: airline)
                    selects the dataset + tools + agent config
    --endpoint      Guava Daytona WebSocket URL             (default: ws://localhost:8765/ws)
    --alias         display label                       (default: guava-daytona)
    --concurrency   trials run in parallel              (default: 1)
    --reruns        max regenerations per invalid trial (default: 3, rerun as needed)
    --time-limit    per-conversation cap, seconds       (default: 600, paper)

Keys (GUAVA_API_KEY, ElevenLabs, OpenAI/Vertex judges) are read from .env.
"""

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

env = dict(os.environ)
# .env lives at the repo root (one level up from eva-bench/), shared across the
# sibling tool folders. Fall back to a local ./.env if one is present.
_ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
_ENV_FILE = _ROOT_ENV if _ROOT_ENV.exists() else Path(".env")
dotenv = dotenv_values(_ENV_FILE)


def _need(name: str) -> str:
    v = dotenv.get(name) or env.get(name)
    if not v or v.startswith("your_"):
        sys.exit(f"{name} not set in .env")
    return v


# ── CLI ────────────────────────────────────────────────────────────────────
p = argparse.ArgumentParser(description="Run one Guava Daytona scenario end-to-end with full metrics.")
p.add_argument(
    "record_id",
    nargs="?",
    default="1.1.2",
    help="airline record id, or comma-separated list (e.g. 1.1.2,1.1.3,1.1.4,1.1.5)",
)
p.add_argument("num_trials", nargs="?", type=int, default=5)
p.add_argument(
    "--endpoint",
    default=os.environ.get("GUAVA_DAYTONA_ENDPOINT", "ws://localhost:8765/ws"),
    help="Guava Daytona WebSocket endpoint URL",
)
p.add_argument("--alias", default="guava-daytona", help="display label -> run-dir suffix + Streamlit system name")
p.add_argument(
    "--domain",
    choices=["airline", "itsm", "medical_hr"],
    default="airline",
    help="EVA domain (selects dataset + tools + agent config)",
)
p.add_argument("--concurrency", type=int, default=1)
p.add_argument("--reruns", type=int, default=3)
p.add_argument("--time-limit", type=int, default=600)
args = p.parse_args()

# ── Parse the (possibly comma-separated) record id list ──────────────────────
record_ids = [r.strip() for r in args.record_id.split(",") if r.strip()]
if not record_ids:
    sys.exit("No record ids given")

# ── Preflight: the Guava Daytona endpoint must be running ─────────────────────────
# EVA does not start it. Fail early with clear instructions rather than mid-run.
_u = urlparse(args.endpoint)
_host = _u.hostname or "localhost"
_port = _u.port or (443 if _u.scheme == "wss" else 80)
try:
    with socket.create_connection((_host, _port), timeout=3):
        pass
    print(f"Guava Daytona endpoint reachable at {args.endpoint}")
except OSError:
    sys.exit(
        f"Guava Daytona endpoint NOT reachable at {args.endpoint} ({_host}:{_port}).\n"
        "Start the Guava Daytona endpoint first, then re-run this script."
    )

# ── Resolve the caller gender for each record (picks EVA_EN_USER_{F,M}) ───────
dataset_path = Path(f"data/{args.domain}_dataset.json")
genders: dict[str, str] = {}
try:
    with open(dataset_path) as f:
        by_id = {str(rec.get("id")): rec for rec in json.load(f)}
    for rid in record_ids:
        rec = by_id.get(rid)
        if rec is None:
            sys.exit(f"Record {rid} not found in {dataset_path}")
        uc = rec.get("user_config", {}) or {}
        # persona_id 1 = female, 2 = male; fall back to the 'gender' field.
        pid = uc.get("user_persona_id")
        g = (uc.get("gender") or "").strip().lower()
        genders[rid] = "F" if (pid == 1 or g in ("f", "female", "woman")) else "M"
except FileNotFoundError:
    print(f"WARN: {dataset_path} not found; cannot pre-check caller gender.", file=sys.stderr)

for rid, gender in genders.items():
    agent_var = f"EVA_EN_USER_{gender}"
    _need(agent_var)  # hard-fail early if the required simulator agent isn't set
    print(f"Record {rid} persona gender={gender} -> caller agent from {agent_var}")

guava_key = _need("GUAVA_API_KEY")
guava_base_url = _need("GUAVA_BASE_URL")
guava_sip_host = _need("GUAVA_SIP_HOST")

# Make .env values (EVA_MODEL_LIST, Vertex/ADC judge config, etc.) visible to the child.
for k, v in dotenv.items():
    if v is not None:
        env.setdefault(k, v)

# ── Assistant = Guava Daytona endpoint ───────────────────────────────────────────
env["EVA_FRAMEWORK"] = "guava_daytona"
env["EVA_MODEL__LLM"] = ""
env["EVA_MODEL__STT"] = ""
env["EVA_MODEL__TTS"] = ""
env["EVA_MODEL__AUDIO_LLM"] = ""
env["EVA_MODEL__S2S"] = "guava_daytona"
env["EVA_MODEL__S2S_PARAMS"] = json.dumps(
    {
        "model": "guava_daytona",  # metrics label
        "alias": args.alias,  # display label -> run-dir suffix + Streamlit system name
        "endpoint": args.endpoint,
        "api_key": guava_key,
        "base_url": guava_base_url,
        "sip_host": guava_sip_host,
        "sip_port": 5060,
        "voice": "grace",
    }
)

# ── Caller (user simulator): ElevenLabs ElevenAgents (paper cascade) ─────────
env["EVA_USER_SIMULATOR__PROVIDER"] = "elevenlabs"

# ── Scope + paper-faithful trial handling ───────────────────────────────────
env["EVA_DOMAIN"] = args.domain
env["EVA_RECORD_IDS"] = ",".join(record_ids)
env["EVA_NUM_TRIALS"] = str(args.num_trials)
env["EVA_MAX_CONCURRENT_CONVERSATIONS"] = str(args.concurrency)
env["EVA_MAX_RERUN_ATTEMPTS"] = str(args.reruns)
# IMPORTANT: do NOT enable debug mode. EVA's _filter_records treats debug as
# "run only records[:1]" and IGNORES EVA_RECORD_IDS. We scope via EVA_RECORD_IDS.
env["EVA_DEBUG"] = "false"
env["EVA_CONVERSATION_TIME_LIMIT_SECONDS"] = str(args.time_limit)
env["EVA_LOG_LEVEL"] = "INFO"
# Metrics default to the 7 EVA report metrics (RunConfig._DEFAULT_METRIC_NAMES);
# no EVA_METRICS override needed. Only these metrics are vendored here, so there
# is no larger set to opt into.

print(
    f"Launching EVA M2 Guava Daytona run [{args.alias}]: elevenlabs caller + guava_daytona "
    f"endpoint ({args.endpoint}), records {','.join(record_ids)} "
    f"x{args.num_trials} valid trials, reruns={args.reruns}, "
    f"concurrency={args.concurrency}, time_limit={args.time_limit}s"
)
import subprocess

sys.exit(subprocess.run([".venv/bin/eva"], env=env).returncode)
