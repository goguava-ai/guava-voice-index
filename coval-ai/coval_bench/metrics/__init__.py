# Copyright 2026 The Coval Benchmarks Authors
# SPDX-License-Identifier: Apache-2.0
#
# Vendored from coval-benchmarks (the coval runner package `coval_bench`).
# Upstream path: runner/src/coval_bench/metrics/__init__.py
# TRIMMED: upstream also exports rtf/ttfs/ttfa; this copy carries only WER,
# the sole metric needed to reproduce STT word error rate.

"""Metrics package (WER only)."""

from coval_bench.metrics.wer import WERResult, compute_wer, normalize_text

__all__ = ["WERResult", "compute_wer", "normalize_text"]
