"""Batch audit and normalized export for a WeRead source directory."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from .models import AuditReport, ParseFailure, ParsedDocument
from .parser import parse_weread_markdown

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".obsidian",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "output",
    "reading_brain",
    "reading-brain",
}


def discover_markdown_files(source_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in source_dir.rglob("*.md"):
        relative_parts = path.relative_to(source_dir).parts[:-1]
        if any(part in IGNORED_DIRECTORY_NAMES or part.startswith(".") for part in relative_parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix().casefold())


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def audit_source_directory(
    source_dir: Path,
    output_dir: Path,
    *,
    limit: int | None = None,
) -> AuditReport:
    source_dir = source_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    discovered = discover_markdown_files(source_dir)
    selected = discovered[:limit] if limit is not None else discovered

    report = AuditReport(source_directory=source_dir.as_posix())
    report.files_discovered = len(discovered)
    documents: list[ParsedDocument] = []
    entry_id_counts: Counter[str] = Counter()

    for path in selected:
        try:
            document = parse_weread_markdown(path, source_dir)
        except Exception as exc:  # Keep the batch running and report every failure.
            report.files_failed += 1
            report.failures.append(
                ParseFailure(
                    source_path=path.relative_to(source_dir).as_posix(),
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )
            continue

        report.files_parsed += 1
        report.books_exported += 1
        documents.append(document)
        for warning in document.warnings:
            report.add_warning(warning)
        for entry in document.entries:
            report.add_entry(entry)
            entry_id_counts[entry.entry_id] += 1

    report.duplicate_entry_ids = sorted(
        entry_id for entry_id, count in entry_id_counts.items() if count > 1
    )

    _write_jsonl(
        output_dir / "books.jsonl",
        (document.book.to_dict() for document in documents),
    )
    _write_jsonl(
        output_dir / "entries.jsonl",
        (entry.to_dict() for document in documents for entry in document.entries),
    )
    _write_jsonl(
        output_dir / "warnings.jsonl",
        (warning.to_dict() for document in documents for warning in document.warnings),
    )
    _write_json(output_dir / "audit.json", report.to_dict())

    return report
