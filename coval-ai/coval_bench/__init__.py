# Copyright 2026 The Coval Benchmarks Authors
# SPDX-License-Identifier: Apache-2.0
#
# Vendored from coval-benchmarks (the coval runner package `coval_bench`).
# Upstream path: runner/src/coval_bench/__init__.py
# Kept verbatim except this note; re-sync from upstream rather than editing here.

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("coval-bench")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
