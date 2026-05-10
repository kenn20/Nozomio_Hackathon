"""Hyperspell integration for CogWatch — Gmail and other data source ingestion."""

import logging
import os

from hyperspell import Hyperspell

logger = logging.getLogger(__name__)

HYPERSPELL_API_KEY = os.environ.get("HYPERSPELL_API_KEY", "")


def get_client(user_id: str) -> Hyperspell:
    """Get a Hyperspell client for a specific user."""
    return Hyperspell(
        api_key=HYPERSPELL_API_KEY,
        user_id=user_id,
    )


def get_user_token(user_id: str) -> str:
    """Generate a Hyperspell user token for OAuth connect flow.

    The frontend uses this token to redirect the user to connect.hyperspell.com
    where they can authorize their Gmail, Google Drive, GitHub, etc.
    """
    client = Hyperspell(api_key=HYPERSPELL_API_KEY)
    response = client.auth.user_token(user_id=user_id)
    return response.token


def search_memories(user_id: str, query: str, answer: bool = True) -> dict:
    """Search user memories from connected accounts (Gmail, Drive, GitHub).

    Args:
        user_id: The user whose memories to search.
        query: Natural language search query.
        answer: If True, returns an AI-generated answer from memories.
                If False, returns raw document matches only.

    Returns:
        dict with 'answer' (str or None) and 'documents' (list).
    """
    client = get_client(user_id)
    response = client.memories.search(
        query=query,
        answer=answer,
    )
    return response


def add_memory(user_id: str, content: str, metadata: dict | None = None) -> dict:
    """Add a memory programmatically (for non-OAuth sources like Obsidian/Claude sessions).

    Args:
        user_id: The user to add the memory for.
        content: The text content of the memory.
        metadata: Optional metadata dict (source, timestamp, etc.).
    """
    client = get_client(user_id)
    response = client.memories.add(
        content=content,
        metadata=metadata or {},
    )
    return response


def list_memories(user_id: str) -> list:
    """List all memories for a user."""
    client = get_client(user_id)
    response = client.memories.list()
    return response
