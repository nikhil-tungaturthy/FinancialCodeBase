"""Loader for the exception reason policy document."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.policies import ExceptionPolicyDocument, ReasonPolicy

_POLICY_PATH = Path(__file__).resolve().parent / "exception_reasons.json"


@lru_cache(maxsize=1)
def load_exception_policy() -> ExceptionPolicyDocument:
    raw = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    return ExceptionPolicyDocument.model_validate(raw)


def reason_by_code(reason_code: str) -> ReasonPolicy | None:
    """The policy row for ``reason_code``, or ``None`` when the code is not in the document."""
    key = reason_code.strip().upper()
    for reason in load_exception_policy().reasons:
        if reason.reason_code == key:
            return reason
    return None


def policy_version() -> str:
    return load_exception_policy().version
