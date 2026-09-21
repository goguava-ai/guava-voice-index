# Copyright 2026 The Coval Benchmarks Authors
# SPDX-License-Identifier: Apache-2.0
#
# Vendored from coval-benchmarks (the coval runner package `coval_bench`).
# Upstream path: runner/src/coval_bench/providers/stt/__init__.py
# TRIMMED: upstream registers 20+ STT providers; this copy keeps only guava
# (daytona-stt), so none of the other provider SDKs are needed.

"""STT provider registry (guava-only).

Usage::

    from coval_bench.providers.stt import STT_PROVIDERS

    cls = STT_PROVIDERS["guava"]
    provider = cls(api_key=settings.guava_api_key, ...)
    result = await provider.measure_ttft(...)
"""

from __future__ import annotations

from coval_bench.providers.base import STTProvider
from coval_bench.providers.stt.guava import GuavaSTTProvider

STT_PROVIDERS: dict[str, type[STTProvider]] = {
    "guava": GuavaSTTProvider,
}

__all__ = [
    "STT_PROVIDERS",
    "GuavaSTTProvider",
]
