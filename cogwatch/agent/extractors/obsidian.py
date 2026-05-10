"""Obsidian vault extractor — scans markdown files for decision language."""

import logging
import re
from datetime import datetime
from pathlib import Path

from git import Repo

from cogwatch.models import DecisionRecord, DecisionSource, DecisionStatus

logger = logging.getLogger(__name__)

# Patterns that indicate a decision, question, or deferred thread
DECISION_PATTERNS = [
    r"(?i)\b(?:decided|choosing|chose|going with|picked|selected|opting for)\b",
    r"(?i)\b(?:we(?:'ll| will) use|i(?:'ll| will) use|using|switched to|migrating to)\b",
    r"(?i)\b(?:the plan is|strategy is|approach is|architecture will be)\b",
]

QUESTION_PATTERNS = [
    r"(?i)\b(?:should (?:we|i)|what if|how (?:do|should|can)|why (?:not|do))\b",
    r"(?i)\b(?:not sure|uncertain|undecided|need to decide|open question)\b",
]

THREAD_PATTERNS = [
    r"(?i)\b(?:TODO|FIXME|HACK|REVISIT)\b",
    r"(?i)\b(?:think about (?:this )?later|come back to|defer|park (?:this|for now))\b",
    r"(?i)\b(?:not sure yet|TBD|to be determined)\b",
]


def extract_from_vault(vault_path: str, since: datetime | None = None) -> list[DecisionRecord]:
    """Extract decision records from an Obsidian vault (git-synced).

    Args:
        vault_path: Path to the local clone of the Obsidian vault.
        since: Only process files modified after this timestamp.

    Returns:
        List of extracted DecisionRecord objects.
    """
    records: list[DecisionRecord] = []
    vault = Path(vault_path)

    if not vault.exists():
        logger.warning("Vault path does not exist: %s", vault_path)
        return records

    # Pull latest if it's a git repo
    if (vault / ".git").exists():
        try:
            repo = Repo(vault_path)
            repo.remotes.origin.pull()
            logger.info("Pulled latest from vault repo")
        except Exception as e:
            logger.warning("Failed to pull vault repo: %s", e)

    # Scan markdown files
    for md_file in vault.rglob("*.md"):
        # Skip hidden directories and templates
        if any(part.startswith(".") for part in md_file.parts):
            continue
        if "template" in str(md_file).lower():
            continue

        # Check modification time if filtering by since
        if since:
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if mtime < since:
                continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to read %s: %s", md_file, e)
            continue

        # Extract the note title from filename
        note_title = md_file.stem

        # Split into paragraphs and check each for decision language
        paragraphs = re.split(r"\n\n+", content)
        for para in paragraphs:
            para = para.strip()
            if len(para) < 20:
                continue

            record_type = _classify_paragraph(para)
            if record_type is None:
                continue

            status = DecisionStatus.ACTIVE
            if record_type == "thread":
                status = DecisionStatus.STALE

            records.append(
                DecisionRecord(
                    source=DecisionSource.OBSIDIAN,
                    content=para[:500],  # Truncate long paragraphs
                    context=f"From note: {note_title} ({md_file.relative_to(vault)})",
                    timestamp=datetime.fromtimestamp(md_file.stat().st_mtime),
                    tags=_extract_tags(content),
                    status=status,
                )
            )

    logger.info("Extracted %d records from Obsidian vault", len(records))
    return records


def _classify_paragraph(text: str) -> str | None:
    """Classify a paragraph as decision, question, thread, or None."""
    for pattern in DECISION_PATTERNS:
        if re.search(pattern, text):
            return "decision"
    for pattern in QUESTION_PATTERNS:
        if re.search(pattern, text):
            return "question"
    for pattern in THREAD_PATTERNS:
        if re.search(pattern, text):
            return "thread"
    return None


def _extract_tags(content: str) -> list[str]:
    """Extract hashtags from Obsidian note content."""
    tags = re.findall(r"#([a-zA-Z][\w/-]*)", content)
    return list(set(tags))[:10]
