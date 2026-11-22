"""Typed data models for the evidence layer.

Milestone 0 intentionally stores only evidence extracted from source files.
It does not infer concepts, claims, relations, or personal viewpoint changes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

EntryType = Literal["highlight", "thought", "review", "popular_highlight", "unknown"]
Severity = Literal["info", "warning", "error"]


@dataclass(slots=True)
class ParseWarning:
    code: str
    message: str
    source_path: str
    line: int | None = None
    severity: Severity = "warning"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ParseFailure:
    source_path: str
    error_type: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BookRecord:
    source_path: str
    file_name: str
    book_id: str | None
    title: str
    author: str | None
    document_type: str | None
    cover: str | None
    reading_status: str | None
    progress: str | None
    reading_time: str | None
    reading_date: str | None
    last_read_date: str | None
    isbn: str | None
    declared_note_count: int | None
    declared_review_count: int | None
    frontmatter: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EntryRecord:
    entry_id: str
    entry_type: EntryType
    marker: str
    text: str
    book_id: str | None
    book_title: str
    author: str | None
    section: str | None
    chapter: str | None
    timestamp: str | None
    block_id: str | None
    weread_uri: str | None
    chapter_uid: str | None
    range_start: int | None
    range_end: int | None
    source_path: str
    source_line_start: int
    source_line_end: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ParsedDocument:
    book: BookRecord
    entries: list[EntryRecord]
    warnings: list[ParseWarning]

    def to_dict(self) -> dict[str, Any]:
        return {
            "book": self.book.to_dict(),
            "entries": [entry.to_dict() for entry in self.entries],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


@dataclass(slots=True)
class AuditReport:
    source_directory: str
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    files_discovered: int = 0
    files_parsed: int = 0
    files_failed: int = 0
    books_exported: int = 0
    entries_exported: int = 0
    highlights_exported: int = 0
    thoughts_exported: int = 0
    reviews_exported: int = 0
    popular_highlights_exported: int = 0
    unknown_entries_exported: int = 0
    warnings_total: int = 0
    duplicate_entry_ids: list[str] = field(default_factory=list)
    warning_counts: dict[str, int] = field(default_factory=dict)
    failures: list[ParseFailure] = field(default_factory=list)

    def add_warning(self, warning: ParseWarning) -> None:
        self.warnings_total += 1
        self.warning_counts[warning.code] = self.warning_counts.get(warning.code, 0) + 1

    def add_entry(self, entry: EntryRecord) -> None:
        self.entries_exported += 1
        if entry.entry_type == "highlight":
            self.highlights_exported += 1
        elif entry.entry_type == "thought":
            self.thoughts_exported += 1
        elif entry.entry_type == "review":
            self.reviews_exported += 1
        elif entry.entry_type == "popular_highlight":
            self.popular_highlights_exported += 1
        else:
            self.unknown_entries_exported += 1

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["failures"] = [failure.to_dict() for failure in self.failures]
        return data


def relative_source_path(path: Path, source_root: Path) -> str:
    """Return a stable POSIX path relative to the configured source root."""

    try:
        return path.resolve().relative_to(source_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()
