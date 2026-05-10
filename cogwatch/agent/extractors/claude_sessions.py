"""Claude Code session extractor — reads .claude/ directory for decisions."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from cogwatch.models import DecisionRecord, DecisionSource

logger = logging.getLogger(__name__)


def extract_from_claude_sessions(
    project_path: str,
    since: datetime | None = None,
) -> list[DecisionRecord]:
    """Extract decision records from Claude Code session files.

    Args:
        project_path: Path to the project directory containing .claude/.
        since: Only process files modified after this timestamp.

    Returns:
        List of extracted DecisionRecord objects.
    """
    records: list[DecisionRecord] = []
    claude_dir = Path(project_path) / ".claude"

    if not claude_dir.exists():
        logger.info("No .claude/ directory found in %s", project_path)
        return records

    # Scan for session files (JSONL conversation logs, memory files, etc.)
    for session_file in claude_dir.rglob("*"):
        if session_file.is_dir():
            continue
        if session_file.suffix not in (".json", ".jsonl", ".md", ".txt"):
            continue

        if since:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            if mtime < since:
                continue

        try:
            content = session_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to read %s: %s", session_file, e)
            continue

        if session_file.suffix == ".jsonl":
            records.extend(_extract_from_jsonl(content, session_file))
        elif session_file.suffix == ".json":
            records.extend(_extract_from_json(content, session_file))
        else:
            records.extend(_extract_from_text(content, session_file))

    logger.info("Extracted %d records from Claude sessions", len(records))
    return records


def _extract_from_jsonl(content: str, filepath: Path) -> list[DecisionRecord]:
    """Extract decisions from JSONL conversation logs."""
    records: list[DecisionRecord] = []
    for line in content.strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Look for assistant messages with decision language
        if entry.get("role") == "assistant":
            text = entry.get("content", "")
            if isinstance(text, list):
                text = " ".join(block.get("text", "") for block in text if isinstance(block, dict))

            if _contains_decision_language(text):
                records.append(
                    DecisionRecord(
                        source=DecisionSource.CLAUDE_SESSION,
                        content=text[:500],
                        context=f"Claude session: {filepath.name}",
                        timestamp=datetime.fromtimestamp(filepath.stat().st_mtime),
                        tags=["claude_session"],
                    )
                )
    return records


def _extract_from_json(content: str, filepath: Path) -> list[DecisionRecord]:
    """Extract decisions from JSON memory/summary files."""
    records: list[DecisionRecord] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return records

    # Handle memory files (key-value or structured)
    texts: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                texts.append(f"{key}: {value}")
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        texts.append(item)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                texts.append(item)

    for text in texts:
        if _contains_decision_language(text):
            records.append(
                DecisionRecord(
                    source=DecisionSource.CLAUDE_SESSION,
                    content=text[:500],
                    context=f"Claude memory: {filepath.name}",
                    timestamp=datetime.fromtimestamp(filepath.stat().st_mtime),
                    tags=["claude_memory"],
                )
            )
    return records


def _extract_from_text(content: str, filepath: Path) -> list[DecisionRecord]:
    """Extract decisions from plain text/markdown files."""
    records: list[DecisionRecord] = []
    paragraphs = re.split(r"\n\n+", content)

    for para in paragraphs:
        para = para.strip()
        if len(para) < 20:
            continue
        if _contains_decision_language(para):
            records.append(
                DecisionRecord(
                    source=DecisionSource.CLAUDE_SESSION,
                    content=para[:500],
                    context=f"Claude file: {filepath.name}",
                    timestamp=datetime.fromtimestamp(filepath.stat().st_mtime),
                    tags=["claude_file"],
                )
            )
    return records


def _contains_decision_language(text: str) -> bool:
    """Check if text contains decision-related language."""
    if len(text) < 20:
        return False
    decision_keywords = [
        r"(?i)\b(?:decided|chose|choosing|going with|picked|selected)\b",
        r"(?i)\b(?:we(?:'ll| will) use|using|switched to|migrating)\b",
        r"(?i)\b(?:should|instead of|better to|reason for|because)\b",
        r"(?i)\b(?:TODO|FIXME|not sure|need to decide|open question)\b",
        r"(?i)\b(?:architecture|design decision|trade-?off|approach)\b",
    ]
    return any(re.search(pattern, text) for pattern in decision_keywords)
