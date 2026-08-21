from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HOOKS_ROOT = REPOSITORY_ROOT / ".githooks"


def utc_date() -> str:
    return datetime.now(UTC).strftime("%y%m%d")


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def make_repo(tmp_path: Path, version: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.name", "Test User")
    run_git(repo, "config", "user.email", "test@example.com")
    (repo / ".githooks").mkdir()
    if HOOKS_ROOT.exists():
        shutil.copytree(HOOKS_ROOT, repo / ".githooks", dirs_exist_ok=True)
    run_git(repo, "config", "core.hooksPath", ".githooks")
    (repo / "VERSION").write_text(version + "\n", encoding="utf-8")
    return repo


def run_hook(repo: Path, hook: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", ".githooks/" + hook, *args],
        cwd=repo,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )


def run_versioning(repo: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", ".githooks/versioning.sh", command],
        cwd=repo,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )


def test_pre_commit_bumps_patch_and_preserves_other_staged_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, f"v1.0.8-{utc_date()}1")
    (repo / "tracked.txt").write_text("keep me\n", encoding="utf-8")
    run_git(repo, "add", "tracked.txt")

    result = run_hook(repo, "pre-commit")

    assert result.returncode == 0, result.stderr
    assert (repo / "VERSION").read_text(encoding="utf-8") == f"v1.0.9-{utc_date()}2\n"
    assert run_git(repo, "diff", "--cached", "--name-only").stdout.splitlines() == [
        "VERSION",
        "tracked.txt",
    ]
    assert run_git(repo, "show", ":tracked.txt").stdout == "keep me\n"


def test_pre_commit_carries_patch_and_resets_build_on_new_utc_day(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "v1.9.9-260820z")

    result = run_hook(repo, "pre-commit")

    assert result.returncode == 0, result.stderr
    assert (repo / "VERSION").read_text(encoding="utf-8") == f"v2.0.0-{utc_date()}1\n"


def test_pre_commit_advances_build_counter_from_nine_to_a(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, f"v1.0.0-{utc_date()}9")

    result = run_hook(repo, "pre-commit")

    assert result.returncode == 0, result.stderr
    assert (repo / "VERSION").read_text(encoding="utf-8") == f"v1.0.1-{utc_date()}a\n"


def test_pre_commit_rejects_malformed_and_exhausted_versions(tmp_path: Path) -> None:
    malformed = make_repo(tmp_path / "malformed", "1.0.0-2608211")
    malformed_result = run_hook(malformed, "pre-commit")
    assert malformed_result.returncode != 0
    assert (malformed / "VERSION").read_text(encoding="utf-8") == "1.0.0-2608211\n"

    exhausted = make_repo(tmp_path / "exhausted", f"v1.0.0-{utc_date()}z")
    exhausted_result = run_hook(exhausted, "pre-commit")
    assert exhausted_result.returncode != 0
    assert (exhausted / "VERSION").read_text(encoding="utf-8") == f"v1.0.0-{utc_date()}z\n"


def test_versioning_script_migrates_legacy_version_without_changing_components(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, "1.2.3-2608207")

    result = run_versioning(repo, "normalize")

    assert result.returncode == 0, result.stderr
    assert (repo / "VERSION").read_text(encoding="utf-8") == "v1.2.3-2608207\n"


def test_prepare_commit_msg_stamps_subject_and_is_idempotent(tmp_path: Path) -> None:
    identifier = f"v1.0.0-{utc_date()}1"
    repo = make_repo(tmp_path, identifier)
    message_file = repo / "message.txt"
    message_file.write_text(
        "fix: repair parser\n\nKeep this body.\n\nTrailer: value\n",
        encoding="utf-8",
    )

    first = run_hook(repo, "prepare-commit-msg", "message.txt", "message")
    second = run_hook(repo, "prepare-commit-msg", "message.txt", "message")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert message_file.read_text(encoding="utf-8") == (
        f"{identifier} fix: repair parser\n\nKeep this body.\n\nTrailer: value\n"
    )
