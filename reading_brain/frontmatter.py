"""A conservative, dependency-free parser for simple YAML frontmatter.

The WeRead plugin's default frontmatter is flat key/value metadata.  This
module intentionally supports that subset so Milestone 0 can run without
network access or third-party packages.  Unknown values are preserved as
strings rather than guessed aggressively.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FrontmatterResult:
    metadata: dict[str, Any]
    body: str
    body_start_line: int
    error: str | None = None


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return None

    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]

    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return parsed
        except (SyntaxError, ValueError):
            pass

    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass

    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            pass

    return value


def parse_frontmatter(text: str) -> FrontmatterResult:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return FrontmatterResult(
            metadata={},
            body=text,
            body_start_line=1,
            error="The document does not begin with YAML frontmatter.",
        )

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return FrontmatterResult(
            metadata={},
            body=text,
            body_start_line=1,
            error="YAML frontmatter is not closed with a second '---' line.",
        )

    metadata: dict[str, Any] = {}
    parse_errors: list[str] = []
    for offset, line in enumerate(lines[1:closing_index], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            parse_errors.append(f"line {offset}: expected 'key: value'")
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            parse_errors.append(f"line {offset}: empty frontmatter key")
            continue
        metadata[key] = _parse_scalar(raw_value)

    return FrontmatterResult(
        metadata=metadata,
        body="".join(lines[closing_index + 1 :]),
        body_start_line=closing_index + 2,
        error="; ".join(parse_errors) if parse_errors else None,
    )
