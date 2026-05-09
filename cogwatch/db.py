"""Database operations for CogWatch — InsForge PostgreSQL + pgvector."""

import json
import logging
import os
import uuid

import psycopg2
import psycopg2.extras

from cogwatch.models import (
    Alert,
    DecisionRecord,
)

logger = logging.getLogger(__name__)


def get_connection():
    """Get a PostgreSQL connection using InsForge credentials."""
    return psycopg2.connect(
        host=os.environ.get("INSFORGE_DB_HOST", ""),
        port=os.environ.get("INSFORGE_DB_PORT", "5432"),
        dbname=os.environ.get("INSFORGE_DB_NAME", "postgres"),
        user=os.environ.get("INSFORGE_DB_USER", "postgres"),
        password=os.environ.get("INSFORGE_DB_PASSWORD", ""),
        sslmode="require",
    )


def store_decision(record: DecisionRecord) -> str:
    """Store a decision record with its embedding in the database."""
    record_id = record.id or str(uuid.uuid4())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            embedding_str = json.dumps(record.embedding) if record.embedding else None
            cur.execute(
                """
                INSERT INTO decision_records
                    (id, source, content, context,
                     timestamp, embedding, tags, status)
                VALUES (%s, %s, %s, %s, %s, %s::vector(1536), %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    context = EXCLUDED.context,
                    embedding = EXCLUDED.embedding,
                    tags = EXCLUDED.tags,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (
                    record_id,
                    record.source.value,
                    record.content,
                    record.context,
                    record.timestamp.isoformat(),
                    embedding_str,
                    record.tags,
                    record.status.value,
                ),
            )
            conn.commit()
            return record_id
    finally:
        conn.close()


def find_similar_decisions(
    embedding: list[float], limit: int = 5, threshold: float = 0.75
) -> list[dict]:
    """Find similar decisions using pgvector cosine similarity."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            embedding_str = json.dumps(embedding)
            cur.execute(
                """
                SELECT id, source, content, context, timestamp, tags, status,
                       1 - (embedding <=> %s::vector(1536)) as similarity
                FROM decision_records
                WHERE embedding IS NOT NULL
                  AND 1 - (embedding <=> %s::vector(1536)) > %s
                ORDER BY embedding <=> %s::vector(1536)
                LIMIT %s
                """,
                (embedding_str, embedding_str, threshold, embedding_str, limit),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


def store_alert(alert: Alert) -> str:
    """Store a contradiction alert with persona responses."""
    alert_id = alert.id or str(uuid.uuid4())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            persona_responses_json = json.dumps(
                [
                    {"persona_name": pr.persona_name, "response": pr.response}
                    for pr in alert.persona_responses
                ]
            )
            cur.execute(
                """
                INSERT INTO alerts
                    (id, old_decision_id, new_decision_id,
                     contradiction_type, severity, explanation,
                     persona_responses, acknowledged, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                RETURNING id
                """,
                (
                    alert_id,
                    alert.old_decision_id,
                    alert.new_decision_id,
                    alert.contradiction_type.value,
                    alert.severity.value,
                    alert.explanation,
                    persona_responses_json,
                    alert.acknowledged,
                    alert.created_at.isoformat(),
                ),
            )
            conn.commit()
            return alert_id
    finally:
        conn.close()


def get_alerts(limit: int = 50, acknowledged: bool | None = None) -> list[dict]:
    """Get alerts, optionally filtered by acknowledged status."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = "SELECT * FROM alerts"
            params: list = []
            if acknowledged is not None:
                query += " WHERE acknowledged = %s"
                params.append(acknowledged)
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def acknowledge_alert(alert_id: str, resolution: str) -> None:
    """Acknowledge an alert with a resolution."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE alerts SET acknowledged = true, resolution = %s WHERE id = %s",
                (resolution, alert_id),
            )
            conn.commit()
    finally:
        conn.close()


def get_decisions(
    source: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Get decision records, optionally filtered by source."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = (
                "SELECT id, source, content, context, timestamp, tags, status FROM decision_records"
            )
            params: list = []
            if source:
                query += " WHERE source = %s"
                params.append(source)
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_active_personas() -> list[dict]:
    """Get all active personas."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM personas WHERE active = true ORDER BY name")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_persona(persona_id: str, name: str, system_prompt: str) -> None:
    """Update a persona's name and system prompt."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE personas SET name = %s, system_prompt = %s WHERE id = %s",
                (name, system_prompt, persona_id),
            )
            conn.commit()
    finally:
        conn.close()
