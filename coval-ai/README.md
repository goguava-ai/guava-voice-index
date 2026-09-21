<h1 align="center">Speech-to-Text WER benchmarking<br />(metric &amp; harness from Coval Benchmarks)</h1>

> *This folder measures the word error rate (WER) of a speech-to-text engine. The
> WER metric, the datasets, and the streaming benchmark harness all originate from
> **Coval Benchmarks**, and full credit for them belongs to the Coval authors and
> project. We vendor a minimal subset and point it at the STT engine under test.*

## 📢 Attribution & Credit

Everything in this folder that fetches audio, streams it, and scores a transcript —
the WER metric, its text normalization, the dataset manifests, and the provider
harness — comes from **[Coval Benchmarks](https://coval.dev)**. We did not invent
these; we vendor them from the coval-benchmarks runner package (`coval_bench`) and
use them to benchmark an STT engine of our choosing.

The WER computation itself stands on two upstream libraries:

- **[jiwer](https://github.com/jitsi/jiwer)** — the Levenshtein/edit-distance engine behind every WER count.
- **[whisper-normalizer](https://github.com/kurianbenoy/whisper_normalizer)** — the `EnglishTextNormalizer`, the de-facto standard for published WER, bundled from **[OpenAI Whisper](https://github.com/openai/whisper)**.

**All credit for the WER metric and benchmark harness goes to Coval Benchmarks,
jiwer, and OpenAI Whisper.**

- 🌐 Coval: [coval.dev](https://coval.dev)

If you use the metric or harness in this folder, please cite and credit Coval Benchmarks.

---

## What this is

A self-contained slice of the Coval Benchmarks runner, extracted to reproduce
**STT word error rate** — without carrying the full runner, database, or registry
layers of coval-benchmarks. It streams a dataset of reference clips to an STT
engine at 1× real time, collects each final transcript, and scores it against the
ground truth with Coval's WER metric.

| Component | Role |
|---|---|
| 📁 **Datasets** | Coval's STT clip manifests (`stt-v3`, `stt-wildasr-*`), each pinned with ground-truth transcripts and SHA-verified audio |
| 🔌 **STT provider** | An adapter implementing Coval's `STTProvider` contract — the engine under test |
| 🎧 **Audio prep** | 16 kHz mono PCM16, WAV header stripped, trailing silence trimmed to the VAD speech-end anchor |
| 📊 **WER metric** | Coval's `compute_wer(reference, hypothesis)` (jiwer + Whisper normalization) |

Everything under `coval_bench/` is vendored from `runner/src/coval_bench/`; each
file carries a header noting its upstream path, and three files are intentionally
trimmed:

| File | Trim |
|---|---|
| `coval_bench/config.py` | Reduced to the ~5 settings the STT path reads |
| `coval_bench/providers/stt/__init__.py` | Registers only the example provider (upstream: 20+) |
| `coval_bench/metrics/__init__.py` | Exports only WER (upstream: also rtf/ttfs/ttfa) |

`run_stt_wer.py` is **new** — a standalone re-implementation of the STT→WER path
from the upstream `runner/orchestrator.py::_run_stt_item`, minus the DB/registry
plumbing. It reproduces the same audio prep and the same metric
(`compute_wer(reference, hypothesis).wer_percentage`).

## Why this folder exists

We run an STT engine through Coval's STT datasets and report WER. The datasets,
manifests, WER metric, and provider contract are all Coval's; our additions are
the trimmed config, the provider registry that selects the engine under test, and
the `run_stt_wer.py` driver that points the metric at that engine.

## 📊 What we measure

We report **Word Error Rate (WER)** from Coval Benchmarks, computed per clip and
aggregated two ways:

| Figure | Meaning |
|---|---|
| **Corpus WER** | Σ edits / Σ reference words — the standard headline figure |
| **Mean clip WER** | Unweighted average of per-clip WER |

Datasets available (manifests bundled here): `stt-v3`, `stt-wildasr-accent`,
`stt-wildasr-clean`, `stt-wildasr-clipping`, `stt-wildasr-farfield`,
`stt-wildasr-noisegap`, `stt-wildasr-phonecodec`, `stt-wildasr-reverb`.

<details>
<summary><h2>Quick Start</h2></summary>

### Installation

We recommend using [uv](https://docs.astral.sh/uv/) for fast, reliable dependency
management. If you don't have `uv` installed, see the
[uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

This project requires **Python >= 3.12** (set via `requires-python` in
`pyproject.toml`; the vendored code uses 3.12+ syntax). `uv` will automatically
select a compatible version.

```bash
cd coval-ai

# Install all dependencies (uv automatically creates a virtual environment)
uv sync

# Copy environment template (lives at the repo root); add the STT engine's connection settings there
cp ../.env.example ../.env
```

### Environment Variables

Configuration is read from the **repo-root `.env`** (`../.env`), with an optional
`coval-ai/.env` override. See .env.example at the repo root for the complete list 
of configuration options.

Google Cloud credentials for the dataset bucket is optional; unset reads the public bucket
anonymously (no GCP account needed)

Audio clips download from the public GCS bucket `coval-benchmarks-datasets` and
cache under `~/.cache/coval-bench`. The ground-truth transcripts (WER references)
live in the pinned manifests under `coval_bench/datasets/manifests/`.

### Running

`run_stt_wer.py` is the driver. Start the STT engine's endpoint first, then run
the driver from `coval-ai/`:

```bash
.venv/bin/python run_stt_wer.py [--dataset DATASET | --all] [--sample-size N] \
    [--total-sample-size N] [--seed N] [--concurrency N] [--out CSV]

# whole stt-v3 dataset
.venv/bin/python run_stt_wer.py --dataset stt-v3

# a 100-clip subset PER dataset, 4 concurrent, dump per-clip results
.venv/bin/python run_stt_wer.py --dataset stt-v3 --sample-size 100 --concurrency 4 --out wer.csv

# a WildASR condition
.venv/bin/python run_stt_wer.py --dataset stt-wildasr-clean

# every bundled dataset, pooled into one figure (see below)
.venv/bin/python run_stt_wer.py --all --out wer.csv

# 100 clips TOTAL, split proportionally across all datasets, reproducible
.venv/bin/python run_stt_wer.py --total-sample-size 100 --seed 42 --out wer.csv
```

**`--all`** runs every bundled STT dataset and reports a per-dataset breakdown
plus a pooled **`__all__`** figure. The pooled number is computed the way Coval's
dashboard does it: it pools *every clip across every dataset* into one pool and
recomputes `100 × Σ(S+D+I) / Σ reference_words` from the raw counts — it is **not**
an average of the per-dataset WERs.

**`--total-sample-size N`** runs a *proportional* sample: it draws **N clips
total** across all bundled datasets, splitting the budget in proportion to each
dataset's pool size (largest-remainder allocation, drawn at random). It implies
`--all`, so you still get the per-dataset breakdown plus the pooled `__all__`
figure. Pair it with **`--seed N`** to make the random draw reproducible. This is
mutually exclusive with `--sample-size` (which draws N clips *per* dataset).

**Sampling flags at a glance:**

| Flag | Effect |
|---|---|
| *(none)* | Every clip in the selected dataset(s) |
| `--sample-size N` | N random clips **per** dataset |
| `--total-sample-size N` | N random clips **total**, split proportionally across all datasets |
| `--seed N` | Makes a `--total-sample-size` draw reproducible |
| `--concurrency N` | Clips processed in parallel (default **1**; raise if the engine tolerates concurrent streams) |

The driver reads the repo-root `.env`, streams the dataset to the STT engine, and
prints the aggregate WER. No virtualenv activation is required —
`.venv/bin/python` is the interpreter `uv sync` created. `uv run python
run_stt_wer.py …` works too and re-syncs the venv first if it is stale.

#### Benchmarking a different STT engine

The engine under test is any class that implements Coval's `STTProvider` contract
(`coval_bench/providers/base.py`) — a single async method:

```python
async def measure_ttft(
    self, audio_data: bytes, channels: int, sample_width: int,
    sample_rate: int, realtime_resolution: float = 0.1,
) -> TranscriptionResult:  # .complete_transcript holds the final text; .error if it failed
    ...
```

`coval_bench/providers/stt/guava.py` is the worked example — a WebSocket adapter
for a streaming STT gateway — and `run_stt_wer.py` points at it. To benchmark
your own engine:

1. **Add an adapter.** Create a class under `coval_bench/providers/stt/` that
   subclasses `STTProvider` and implements `measure_ttft`, returning the final
   transcript in `TranscriptionResult.complete_transcript` (set `.error` on
   failure). The `guava.py` adapter is a full reference for the streaming case.
2. **Register it.** Add it to `STT_PROVIDERS` in
   `coval_bench/providers/stt/__init__.py`.
3. **Point the driver at it.** In `run_stt_wer.py`, construct your provider
   instead of the example one (and read whatever settings it needs from
   `config.py`). Everything downstream — audio prep, WER scoring, aggregation —
   stays the same.

The audio contract is fixed by the harness: `measure_ttft` receives raw 16 kHz
mono PCM16 bytes (no WAV header), already trimmed to the speech-end anchor.

</details>

## Output Structure

For a single dataset, console output reports the aggregate WER plus any
failed/skipped clips:

```
=== STT WER ===
dataset:        stt-v3 (v1.0.0)
clips scored:   100   failed/skipped: 0
corpus WER:     4.21%   (sum errors / sum reference words)
mean clip WER:  3.87%   (unweighted average over clips)
```

With `--all` (or `--total-sample-size`), it prints a per-dataset breakdown
followed by the pooled `__all__` row (all clips in one pool); with
`--total-sample-size` the per-dataset `clips` counts are the proportional split
rather than equal:

```
=== STT WER ===
dataset                     clips  corpus WER   mean WER
--------------------------------------------------------
stt-v3                        100       4.21%      3.87%
stt-wildasr-accent            100      11.04%     10.12%
...
--------------------------------------------------------
__all__ (pooled clips)        800       7.63%      7.19%

pooled across 8 datasets · 800 clips scored · 0 failed/skipped
corpus WER pools every clip: 100 * sum(S+D+I) / sum(reference_words)
```

With `--out wer.csv`, a per-clip table is written:

| Column | Meaning |
|---|---|
| `dataset_id` | Which dataset the clip came from (useful with `--all`) |
| `sample_id`, `audio_filename` | Clip identity |
| `wer_percentage` | Per-clip WER (blank if the clip failed) |
| `substitutions`, `deletions`, `insertions`, `reference_words` | Edit breakdown |
| `reference`, `hypothesis` | Ground-truth vs. transcribed text |
| `error` | Reason a clip was skipped, if any |

## Licensing & Citation

This folder is Apache-2.0 (see `LICENSE`). The benchmark harness, datasets, and
WER metric are the work of Coval Benchmarks; the WER internals are jiwer
(Apache-2.0) and whisper-normalizer (MIT; bundles the OpenAI Whisper text
normalizer). Please credit Coval Benchmarks in any work that uses this folder.

- Coval: [coval.dev](https://coval.dev)
- jiwer: [github.com/jitsi/jiwer](https://github.com/jitsi/jiwer)
- whisper-normalizer: [github.com/kurianbenoy/whisper_normalizer](https://github.com/kurianbenoy/whisper_normalizer)
- OpenAI Whisper: [github.com/openai/whisper](https://github.com/openai/whisper)
