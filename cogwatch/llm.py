"""LLM client for CogWatch — uses OpenRouter for inference and embeddings."""

import json
import logging

from openai import OpenAI

from cogwatch.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    LLM_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)

logger = logging.getLogger(__name__)


def get_openrouter_client() -> OpenAI:
    """Create an OpenAI-compatible client pointing to OpenRouter."""
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    client = get_openrouter_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def classify_decision(text: str, context: str) -> dict:
    """Classify extracted text as a decision, question, or thread using LLM."""
    client = get_openrouter_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a decision classifier. Given text from a user's notes, "
                    "commits, or AI sessions, classify it as one of: "
                    "'decision' (a choice was made), 'question' (unresolved question), "
                    "or 'thread' (ongoing topic that may become stale). "
                    'Respond as JSON: {"type": "decision|question|thread", '
                    '"content": "normalized statement", "tags": ["tag1", "tag2"]}'
                ),
            },
            {
                "role": "user",
                "content": f"Text: {text}\nContext: {context}",
            },
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def check_contradiction(old_decision: str, old_date: str, new_activity: str, new_date: str) -> dict:
    """Check if two statements from the same person are contradictory."""
    client = get_openrouter_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze whether two statements from the same person are contradictory. "
                    'Respond as JSON: {"is_contradiction": bool, "explanation": str, '
                    '"severity": "low"|"medium"|"high", '
                    '"contradiction_type": "direct_contradiction"|"forgotten_resolution"|"stale_thread"}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Given these two statements from the same person:\n"
                    f'- OLD ({old_date}): "{old_decision}"\n'
                    f'- NEW ({new_date}): "{new_activity}"\n\n'
                    f"Are these contradictory? If so, what's the nature of the contradiction?"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def generate_persona_advisory(
    persona_name: str,
    persona_prompt: str,
    old_decision: str,
    old_context: str,
    old_date: str,
    new_activity: str,
    new_context: str,
    new_date: str,
    related_decisions: list[str],
) -> str:
    """Generate advisory response from a specific persona."""
    client = get_openrouter_client()
    related_text = "\n".join(f"- {d}" for d in related_decisions) if related_decisions else "None"

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": f"You are {persona_name}. {persona_prompt}",
            },
            {
                "role": "user",
                "content": (
                    f"The user made this decision on {old_date}:\n"
                    f'"{old_decision}"\n'
                    f"Context: {old_context}\n\n"
                    f"Now they appear to be doing the opposite:\n"
                    f'"{new_activity}"\n'
                    f"Context: {new_context}\n\n"
                    f"Related past decisions by this person:\n"
                    f"{related_text}\n\n"
                    f"Provide your perspective in 2-3 sentences. "
                    f"Reference their specific history. Stay in character. Be direct."
                ),
            },
        ],
    )
    return response.choices[0].message.content
