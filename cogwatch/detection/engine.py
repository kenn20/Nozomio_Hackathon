"""Contradiction detection engine — finds context rot in decision history."""

import logging

from cogwatch.config import SIMILARITY_THRESHOLD, TOP_K_SIMILAR
from cogwatch.db import find_similar_decisions, get_active_personas, store_alert
from cogwatch.llm import check_contradiction, generate_embedding, generate_persona_advisory
from cogwatch.models import (
    Alert,
    ContradictionResult,
    ContradictionType,
    DecisionRecord,
    PersonaResponse,
    Severity,
)

logger = logging.getLogger(__name__)


def detect_contradictions(new_record: DecisionRecord) -> Alert | None:
    """Check a new decision record against history for contradictions.

    Process:
    1. Generate embedding for new record
    2. Query DB for similar past decisions (cosine similarity via pgvector)
    3. If similarity > threshold, use LLM to confirm contradiction
    4. If contradiction confirmed, generate persona advisory

    Returns:
        Alert if contradiction detected, None otherwise.
    """
    if not new_record.embedding:
        logger.info("Generating embedding for new record")
        new_record.embedding = generate_embedding(new_record.content)

    # Find similar past decisions
    similar = find_similar_decisions(
        embedding=new_record.embedding,
        limit=TOP_K_SIMILAR,
        threshold=SIMILARITY_THRESHOLD,
    )

    if not similar:
        logger.debug("No similar decisions found for: %s", new_record.content[:80])
        return None

    logger.info("Found %d similar decisions, checking for contradictions", len(similar))

    # Check each similar decision for contradiction
    for past_decision in similar:
        result = _check_pair(new_record, past_decision)
        if result and result.is_contradiction:
            logger.info(
                "Contradiction detected (severity=%s): %s",
                result.severity,
                result.explanation[:100],
            )

            # Generate persona advisory
            persona_responses = _generate_advisory(new_record, past_decision, similar)

            alert = Alert(
                old_decision_id=past_decision["id"],
                new_decision_id=new_record.id or "",
                contradiction_type=result.contradiction_type or ContradictionType.DIRECT,
                severity=result.severity,
                explanation=result.explanation,
                persona_responses=persona_responses,
            )

            # Store and return
            alert_id = store_alert(alert)
            alert.id = alert_id
            return alert

    return None


def _check_pair(new_record: DecisionRecord, past_decision: dict) -> ContradictionResult | None:
    """Check a pair of decisions for contradiction using LLM."""
    try:
        result = check_contradiction(
            old_decision=past_decision["content"],
            old_date=str(past_decision.get("timestamp", "unknown")),
            new_activity=new_record.content,
            new_date=str(new_record.timestamp),
        )
        return ContradictionResult(
            is_contradiction=result.get("is_contradiction", False),
            explanation=result.get("explanation", ""),
            severity=Severity(result.get("severity", "low")),
            contradiction_type=(
                ContradictionType(result["contradiction_type"])
                if result.get("contradiction_type")
                else None
            ),
        )
    except Exception as e:
        logger.error("Error checking contradiction: %s", e)
        return None


def _generate_advisory(
    new_record: DecisionRecord,
    old_decision: dict,
    related_decisions: list[dict],
) -> list[PersonaResponse]:
    """Generate multi-persona advisory for a detected contradiction."""
    personas = get_active_personas()
    if not personas:
        logger.warning("No active personas found, skipping advisory generation")
        return []

    related_contents = [
        d["content"] for d in related_decisions[:5] if d["id"] != old_decision["id"]
    ]
    responses: list[PersonaResponse] = []

    for persona in personas:
        try:
            response_text = generate_persona_advisory(
                persona_name=persona["name"],
                persona_prompt=persona["system_prompt"],
                old_decision=old_decision["content"],
                old_context=old_decision.get("context", ""),
                old_date=str(old_decision.get("timestamp", "unknown")),
                new_activity=new_record.content,
                new_context=new_record.context,
                new_date=str(new_record.timestamp),
                related_decisions=related_contents,
            )
            responses.append(
                PersonaResponse(
                    persona_name=persona["name"],
                    response=response_text,
                )
            )
        except Exception as e:
            logger.error("Error generating advisory for persona %s: %s", persona["name"], e)

    return responses
