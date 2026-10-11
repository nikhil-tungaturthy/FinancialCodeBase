"""Shared fixtures for the legacy golden-master tests.

The COBOL fixtures compile ``FEECALC01`` into a pytest temporary directory
(never into ``legacy/cobol/build``, so parallel runs cannot race) and skip with
the message mandated by the build spec when GnuCOBOL is not available.

``legacy/reference-tests`` is deliberately not a Python package (its name is
not an identifier, so pytest would not treat it as one anyway). Test modules
therefore never import from this file; everything they need is a fixture, and
fixture JSON is loaded by path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest

REFERENCE_TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = REFERENCE_TESTS_DIR / "fixtures"
REPO_ROOT = REFERENCE_TESTS_DIR.parents[1]
COBOL_DIR = REPO_ROOT / "legacy" / "cobol"
COBOL_SOURCE = COBOL_DIR / "FEECALC01.cbl"
COBOL_COPYBOOKS = COBOL_DIR / "copybooks"
VB6_MODULE = REPO_ROOT / "legacy" / "vb6" / "modExceptionRouting.bas"

COBC_SKIP_MESSAGE = (
    "GnuCOBOL (cobc) not installed; COBOL not executed — Python reference + fixtures only"
)


def load_fixture_cases(name: str) -> list[dict[str, Any]]:
    """Return the ``cases`` list of a fixture file under ``fixtures/``."""
    document = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = document["cases"]
    return cases


def find_cobc() -> str | None:
    """Locate the GnuCOBOL compiler: ``$COBC`` if set, otherwise ``cobc`` on PATH."""
    override = os.environ.get("COBC")
    if override:
        return override if shutil.which(override) else None
    return shutil.which("cobc")


#: ``(return_code, stdout, feeout_lines)`` of one FEECALC01 execution.
FeeCalcRun = tuple[int, str, list[str]]
FeeCalcRunner = Callable[[Sequence[str]], FeeCalcRun]


@pytest.fixture(scope="session")
def feecalc_cases() -> list[dict[str, Any]]:
    return load_fixture_cases("feecalc_cases.json")


@pytest.fixture(scope="session")
def routing_cases() -> list[dict[str, Any]]:
    return load_fixture_cases("exception_routing_cases.json")


@pytest.fixture(scope="session")
def cobc() -> str:
    compiler = find_cobc()
    if compiler is None:
        pytest.skip(COBC_SKIP_MESSAGE)
    return compiler


@pytest.fixture(scope="session")
def feecalc01_binary(cobc: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Compile FEECALC01 once per session into a temporary directory."""
    build_dir = tmp_path_factory.mktemp("feecalc01-build")
    binary = build_dir / "feecalc01"
    command = [
        cobc,
        "-x",
        "-std=default",
        "-I",
        str(COBOL_COPYBOOKS),
        "-o",
        str(binary),
        str(COBOL_SOURCE),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not binary.exists():
        pytest.fail(
            "cobc failed to compile FEECALC01.cbl\n"
            f"command: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return binary


@pytest.fixture
def feecalc01_runner(feecalc01_binary: Path, tmp_path: Path) -> FeeCalcRunner:
    """Return a callable that runs the compiled program on the given FEEIN lines."""

    def run(feein_lines: Sequence[str]) -> FeeCalcRun:
        feein = tmp_path / "FEEIN"
        feeout = tmp_path / "FEEOUT"
        feein.write_text("".join(f"{line}\n" for line in feein_lines), encoding="ascii")
        env = {**os.environ, "DD_FEEIN": str(feein), "DD_FEEOUT": str(feeout)}
        completed = subprocess.run(
            [str(feecalc01_binary)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        lines = feeout.read_text(encoding="ascii").splitlines() if feeout.exists() else []
        return completed.returncode, completed.stdout + completed.stderr, lines

    return run
