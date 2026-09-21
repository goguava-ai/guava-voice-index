# Copyright 2026 The Coval Benchmarks Authors
# SPDX-License-Identifier: Apache-2.0
#
# TRIMMED: this is a reduced copy of coval-benchmarks' config
# (upstream: runner/src/coval_bench/config.py). The upstream Settings holds the
# whole runner's configuration; this copy keeps ONLY the fields the STT WER path
# reads. Do not re-sync it verbatim from upstream.

"""Minimal Pydantic settings for the vendored STT WER path.

    from coval_bench.config import Settings, get_settings
"""

from __future__ import annotations

import functools
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The canonical .env lives at the guava-voice-index repo root. This file is at
# <repo-root>/coval-ai/coval_bench/config.py, so parents[2] is the repo root.
# Resolved absolutely (not CWD-relative) so it loads no matter where the driver
# is launched from. A coval-ai/.env, then a CWD .env, override it if present.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
_LOCAL_ENV = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """STT WER settings, populated from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        # Later entries win, so a local override beats the repo-root default.
        env_file=(str(_REPO_ROOT_ENV), str(_LOCAL_ENV), ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    # --- Dataset (public GCS bucket; anonymous read when no creds are set) ---
    dataset_bucket: str = "coval-benchmarks-datasets"

    # --- Guava STT (daytona-stt) ---
    guava_base_url: str | None = None
    guava_api_key: SecretStr | None = None
    guava_stt_domain: str | None = None

    # --- GCS auth (optional) ---
    google_application_credentials: Path | None = None


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-cached Settings instance."""
    return Settings()
