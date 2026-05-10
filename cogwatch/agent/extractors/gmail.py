"""Gmail extractor — pulls decision-relevant emails via Hyperspell memory search."""

import logging

from cogwatch.hyperspell_client import search_memories
from cogwatch.models import DecisionRecord, DecisionSource

logger = logging.getLogger(__name__)

# Keywords that indicate decision-relevant emails
DECISION_KEYWORDS = [
    "decided", "decision", "agreed", "approved", "rejected",
    "chose", "choosing", "selected", "going with", "switched to",
    "migrating", "plan is", "we will", "we should", "strategy",
    "architecture", "stack", "approach", "framework",
]


def extract_gmail_decisions(user_id: str = "default-user") -> list[DecisionRecord]:
    """Extract decision-relevant records from Gmail via Hyperspell.

    Uses Hyperspell's memory search to find emails containing decisions,
    then converts them into DecisionRecord objects for contradiction detection.
    """
    records: list[DecisionRecord] = []

    for keyword in DECISION_KEYWORDS[:5]:
        try:
            result = search_memories(user_id, keyword, answer=False)

            if not hasattr(result, "documents"):
                continue

            for doc in result.documents:
                content = doc.text if hasattr(doc, "text") else str(doc)
                title = doc.title if hasattr(doc, "title") else ""

                if not content or len(content) < 20:
                    continue

                record = DecisionRecord(
                    source=DecisionSource.GMAIL,
                    content=content[:2000],
                    context=f"Gmail: {title}" if title else "Gmail thread",
                )
                records.append(record)
        except Exception as e:
            logger.debug("Gmail search for '%s' failed: %s", keyword, e)
            continue

    # Deduplicate by content hash
    seen = set()
    unique_records = []
    for r in records:
        key = r.content[:200]
        if key not in seen:
            seen.add(key)
            unique_records.append(r)

    logger.info("Extracted %d unique Gmail decision records via Hyperspell", len(unique_records))
    return unique_records
