# Copyright 2026 The Coval Benchmarks Authors
# SPDX-License-Identifier: Apache-2.0
#
# Derived from the coval-benchmarks runner package (`coval_bench`).
# This driver is a standalone replacement for
#   runner/src/coval_bench/runner/orchestrator.py :: _run_stt_item
# extracting only the STT -> WER path so the benchmark can run without the
# runner/orchestration, database, and registry layers of coval-benchmarks.
#
# What it does, per dataset clip (matching the upstream orchestrator exactly):
#   1. read the WAV, assert 16 kHz mono PCM16, strip the header (send frames only),
#   2. trim trailing silence to the VAD speech-end anchor (speech_end_offset_ms),
#   3. stream the audio to guava daytona-stt at 1x realtime and collect the final
#      transcript,
#   4. WER = compute_wer(ground_truth, transcript).wer_percentage.
#
# Two aggregate figures are reported, matching coval's dashboard:
#   * corpus WER    = 100 * sum(S+D+I) / sum(reference_words)  (pooled / micro)
#   * mean clip WER = unweighted average of per-clip WER        (macro / avg_value)
# With --all, every bundled STT dataset is run and the clips are pooled into one
# figure the same way coval materializes its "__all__" sentinel row: it pools all
# clips across datasets and recomputes from raw counts, NOT an average of the
# per-dataset numbers (see runner/.../api/routers/aggregates.py::_POOLED_TOTAL).
#
# Audio clips are fetched from the public GCS dataset bucket and cached under
# ~/.cache/coval-bench; no GCP account is needed (anonymous read).

from __future__ import annotations

import argparse
import asyncio
import csv
import random
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

from coval_bench.config import get_settings
from coval_bench.datasets.loader import DatasetItem, _load_manifest, load_stt_dataset
from coval_bench.metrics.wer import compute_wer
from coval_bench.providers.stt.guava import GuavaSTTProvider

_SAMPLE_RATE = 16000
_STT_TIMEOUT_S = 120.0

# Every bundled STT manifest, in the order --all runs them. These are the
# datasets whose clips coval pools into its "__all__" sentinel row.
_ALL_STT_DATASETS = (
    "stt-v3",
    "stt-wildasr-accent",
    "stt-wildasr-clean",
    "stt-wildasr-clipping",
    "stt-wildasr-farfield",
    "stt-wildasr-noisegap",
    "stt-wildasr-phonecodec",
    "stt-wildasr-reverb",
)


def _allocate_proportional(sizes: dict[str, int], total: int) -> dict[str, int]:
    """Split ``total`` clips across datasets in proportion to their pool sizes.

    Largest-remainder (Hamilton) allocation: each dataset gets the floor of its
    proportional share, then the leftover clips go one each to the datasets with
    the biggest fractional remainders, so the allocations sum to exactly ``total``.
    Matches the smoke-test allocator in
    ``runner/scripts/stt_prop100.py`` (coval-benchmarks).
    """
    grand = sum(sizes.values())
    raw = {d: sizes[d] / grand * total for d in sizes}
    alloc = {d: int(raw[d]) for d in sizes}
    leftover = total - sum(alloc.values())
    for d in sorted(sizes, key=lambda d: raw[d] - int(raw[d]), reverse=True)[:leftover]:
        alloc[d] += 1
    return alloc


@dataclass
class ClipResult:
    dataset_id: str
    sample_id: str
    audio_filename: str
    reference: str
    hypothesis: str | None
    wer_percentage: float | None
    substitutions: int
    deletions: int
    insertions: int
    reference_words: int
    error: str | None


def _read_frames_trimmed(item: DatasetItem) -> bytes:
    """Read PCM frames (no WAV header), trimmed to the speech-end anchor.

    Mirrors _run_stt_item: a WAV header sent as PCM reads as a click that can
    derail provider VAD, so only frames are returned; trailing silence past
    ``speech_end_offset_ms`` is dropped so TTFS reflects finalization, not
    source silence.
    """
    with wave.open(str(item.path), "rb") as wav_file:
        fmt = (wav_file.getframerate(), wav_file.getnchannels(), wav_file.getsampwidth())
        if fmt != (_SAMPLE_RATE, 1, 2):
            raise ValueError(f"{item.path.name}: expected 16 kHz mono PCM16, got {fmt}")
        audio_bytes = wav_file.readframes(wav_file.getnframes())

    duration_sec = item.duration_sec
    speech_end_offset_ms = item.speech_end_offset_ms
    if isinstance(speech_end_offset_ms, (int, float)):
        trailing_ms = max(0.0, duration_sec * 1000.0 - speech_end_offset_ms)
        tail_bytes = int(round(trailing_ms / 1000.0 * _SAMPLE_RATE)) * 2
        if 0 < tail_bytes < len(audio_bytes):
            audio_bytes = audio_bytes[: len(audio_bytes) - tail_bytes]
    return audio_bytes


async def _run_clip(
    item: DatasetItem,
    *,
    dataset_id: str,
    provider_kwargs: dict,
    sem: asyncio.Semaphore,
) -> ClipResult:
    base = ClipResult(
        dataset_id=dataset_id,
        sample_id=item.sample_id,
        audio_filename=item.path.name,
        reference=item.transcript,
        hypothesis=None,
        wer_percentage=None,
        substitutions=0,
        deletions=0,
        insertions=0,
        reference_words=0,
        error=None,
    )
    async with sem:
        try:
            audio_bytes = _read_frames_trimmed(item)
        except Exception as exc:  # noqa: BLE001 — surface as a per-clip failure row
            base.error = f"audio_prep: {exc}"
            return base

        try:
            provider = GuavaSTTProvider(**provider_kwargs)
            async with asyncio.timeout(_STT_TIMEOUT_S):
                result = await provider.measure_ttft(audio_bytes, 1, 2, _SAMPLE_RATE, 0.1)
        except Exception as exc:  # noqa: BLE001
            base.error = f"stt: {exc}"
            return base

        if result.error is not None:
            base.error = result.error
            return base

        hyp = result.complete_transcript
        base.hypothesis = hyp
        # Skip WER when the stream produced no final transcript — scoring a
        # salvaged/empty transcript from a failed run is misleading.
        if not item.transcript or hyp is None:
            base.error = base.error or "no final transcript"
            return base

        wer = compute_wer(item.transcript, hyp)
        base.wer_percentage = wer.wer_percentage
        base.substitutions = wer.substitutions
        base.deletions = wer.deletions
        base.insertions = wer.insertions
        base.reference_words = wer.reference_words
        return base


def _aggregate(results: list[ClipResult]) -> tuple[list[ClipResult], float, float]:
    """Return (scored clips, corpus WER, mean clip WER) over *results*.

    Corpus (pooled/micro) WER weights by reference length — coval's headline
    ``_POOLED_TOTAL`` (100 * sum(S+D+I) / sum(reference_words)). Mean clip WER is
    the unweighted per-clip average — coval's ``avg_value``. Only clips that were
    actually scored enter either figure. Pooling a list that spans datasets
    reproduces coval's "__all__" row (all clips in one pool, not a mean of means).
    """
    scored = [r for r in results if r.wer_percentage is not None]
    total_ref = sum(r.reference_words for r in scored)
    total_err = sum(r.substitutions + r.deletions + r.insertions for r in scored)
    corpus_wer = (total_err / total_ref * 100.0) if total_ref else float("nan")
    macro_wer = (sum(r.wer_percentage for r in scored) / len(scored)) if scored else float("nan")
    return scored, corpus_wer, macro_wer


async def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run guava daytona-stt WER over coval STT datasets.")
    parser.add_argument("--dataset", default="stt-v3", help="manifest id, e.g. stt-v3 (default) or stt-wildasr-clean")
    parser.add_argument(
        "--all",
        action="store_true",
        help="run every bundled STT dataset and pool the clips into one "
        "'__all__' figure the way coval does (overrides --dataset)",
    )
    parser.add_argument("--sample-size", type=int, default=None, help="random subset size PER dataset (default: whole dataset)")
    parser.add_argument(
        "--total-sample-size",
        type=int,
        default=None,
        help="TOTAL clips to draw across all datasets being run, split proportionally "
        "to each dataset's pool size (largest-remainder, random). Implies --all; "
        "mutually exclusive with --sample-size",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed the random draw for --total-sample-size so the sample is reproducible",
    )
    parser.add_argument("--concurrency", type=int, default=1, help="concurrent clips (default: 1)")
    parser.add_argument("--out", type=Path, default=None, help="write per-clip results to this CSV")
    args = parser.parse_args(argv)

    if args.total_sample_size is not None:
        if args.sample_size is not None:
            print("--total-sample-size and --sample-size are mutually exclusive", file=sys.stderr)
            return 2
        if args.total_sample_size <= 0:
            print("--total-sample-size must be positive", file=sys.stderr)
            return 2

    settings = get_settings()
    if not settings.guava_base_url or settings.guava_api_key is None:
        print(
            "GUAVA_BASE_URL and GUAVA_API_KEY must be set (env or .env). "
            "GUAVA_STT_DOMAIN is optional.",
            file=sys.stderr,
        )
        return 2

    provider_kwargs = {
        "api_key": settings.guava_api_key,
        "model": "daytona-stt",
        "base_url": settings.guava_base_url,
        "domain": settings.guava_stt_domain,
    }

    # --total-sample-size runs the full dataset set and splits the budget across
    # it proportionally; otherwise --all runs everything and --dataset runs one.
    if args.total_sample_size is not None:
        dataset_ids = list(_ALL_STT_DATASETS)
    else:
        dataset_ids = list(_ALL_STT_DATASETS) if args.all else [args.dataset]

    # Per-dataset random subset size. For --total-sample-size, allocate the budget
    # proportionally to each manifest's pool size (read from the manifest, no audio
    # fetch); a seeded rng makes the draw reproducible. Otherwise every dataset
    # gets the same --sample-size (or None = whole dataset).
    rng: random.Random | None = None
    alloc: dict[str, int] | None = None
    if args.total_sample_size is not None:
        pool_sizes = {d: len(_load_manifest(d).items) for d in dataset_ids}
        grand = sum(pool_sizes.values())
        if args.total_sample_size > grand:
            print(
                f"--total-sample-size {args.total_sample_size} exceeds the {grand} clips "
                f"available across {len(dataset_ids)} datasets",
                file=sys.stderr,
            )
            return 2
        alloc = _allocate_proportional(pool_sizes, args.total_sample_size)
        rng = random.Random(args.seed)
        print(f"proportional sample: {args.total_sample_size} clips | alloc={alloc}", file=sys.stderr)

    sem = asyncio.Semaphore(args.concurrency)
    all_results: list[ClipResult] = []
    # (dataset_id, version, results) in run order, for the per-dataset breakdown.
    per_dataset: list[tuple[str, str, list[ClipResult]]] = []
    for dataset_id in dataset_ids:
        sample_size = alloc[dataset_id] if alloc is not None else args.sample_size
        dataset = load_stt_dataset(dataset_id, settings=settings, sample_size=sample_size, rng=rng)
        print(f"loaded {dataset_id} v{dataset.version}: {len(dataset.items)} clips", file=sys.stderr)
        results = await asyncio.gather(
            *(
                _run_clip(item, dataset_id=dataset_id, provider_kwargs=provider_kwargs, sem=sem)
                for item in dataset.items
            )
        )
        per_dataset.append((dataset_id, dataset.version, results))
        all_results.extend(results)

    if args.out is not None:
        with args.out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["dataset_id", "sample_id", "audio_filename", "wer_percentage", "substitutions",
                 "deletions", "insertions", "reference_words", "reference", "hypothesis", "error"]
            )
            for r in all_results:
                writer.writerow(
                    [r.dataset_id, r.sample_id, r.audio_filename,
                     "" if r.wer_percentage is None else f"{r.wer_percentage:.4f}",
                     r.substitutions, r.deletions, r.insertions, r.reference_words,
                     r.reference, r.hypothesis or "", r.error or ""]
                )
        print(f"wrote {args.out}", file=sys.stderr)

    print("\n=== STT WER ===")
    if len(dataset_ids) > 1:
        # Per-dataset breakdown, then the pooled "__all__" row: every clip across
        # every dataset in one pool, recomputed from raw counts (coval's sentinel).
        print(f"{'dataset':26} {'clips':>6} {'corpus WER':>11} {'mean WER':>10}")
        print("-" * 56)
        for dataset_id, _version, results in per_dataset:
            scored, corpus_wer, macro_wer = _aggregate(results)
            print(f"{dataset_id:26} {len(scored):>6} {corpus_wer:>10.2f}% {macro_wer:>9.2f}%")
        print("-" * 56)
        scored, corpus_wer, macro_wer = _aggregate(all_results)
        print(f"{'__all__ (pooled clips)':26} {len(scored):>6} {corpus_wer:>10.2f}% {macro_wer:>9.2f}%")
        failed = [r for r in all_results if r.wer_percentage is None]
        print(
            f"\npooled across {len(dataset_ids)} datasets · {len(scored)} clips scored · "
            f"{len(failed)} failed/skipped"
        )
        print("corpus WER pools every clip: 100 * sum(S+D+I) / sum(reference_words)")
    else:
        dataset_id, version, results = per_dataset[0]
        scored, corpus_wer, macro_wer = _aggregate(results)
        failed = [r for r in results if r.wer_percentage is None]
        print(f"dataset:        {dataset_id} (v{version})")
        print(f"clips scored:   {len(scored)}   failed/skipped: {len(failed)}")
        print(f"corpus WER:     {corpus_wer:.2f}%   (sum errors / sum reference words)")
        print(f"mean clip WER:  {macro_wer:.2f}%   (unweighted average over clips)")

    if failed:
        print(f"\n{len(failed)} clip(s) failed or produced no transcript:")
        for r in failed[:20]:
            label = f"{r.dataset_id}/{r.audio_filename}" if len(dataset_ids) > 1 else r.audio_filename
            print(f"  - {label}: {r.error}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
