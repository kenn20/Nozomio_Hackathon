"""CogWatch Tensorlake Agent — background cron agent for context rot detection.

Deployed to Tensorlake, scheduled via cron (every 15 minutes).
Ingests from Obsidian, GitHub, Claude Code sessions, and Gmail (via Hyperspell),
then runs contradiction detection + persona advisory.
"""

import logging
import os
from datetime import datetime, timedelta

from tensorlake.applications import Image, Retries, application, function

from cogwatch.agent.extractors.claude_sessions import extract_from_claude_sessions
from cogwatch.agent.extractors.github import extract_from_github
from cogwatch.agent.extractors.gmail import extract_gmail_decisions
from cogwatch.agent.extractors.obsidian import extract_from_vault
from cogwatch.db import store_decision
from cogwatch.detection.engine import detect_contradictions
from cogwatch.llm import generate_embedding
from cogwatch.models import DecisionRecord

logger = logging.getLogger(__name__)

# Custom image with our dependencies
cogwatch_image = Image(name="cogwatch-agent").run(
    "pip install httpx psycopg2-binary openai pydantic GitPython hyperspell"
)


@application(
    tags={"project": "cogwatch", "type": "ingestion"},
    retries=Retries(max_retries=2),
)
@function(
    image=cogwatch_image,
    timeout=600,
    secrets=[
        "OPENROUTER_API_KEY",
        "GITHUB_TOKEN",
        "INSFORGE_DB_HOST",
        "INSFORGE_DB_PORT",
        "INSFORGE_DB_NAME",
        "INSFORGE_DB_USER",
        "INSFORGE_DB_PASSWORD",
        "HYPERSPELL_API_KEY",
    ],
    description="Ingest decisions from all sources and run contradiction detection",
)
def cogwatch_ingest(config: dict | None = None) -> dict:
    """Main ingestion pipeline — runs every 15 minutes via cron.

    Config can override default paths/repos:
    {
        "obsidian_vault_path": "/path/to/vault",
        "github_repos": [{"owner": "org", "name": "repo"}],
        "claude_project_paths": ["/path/to/project"],
        "lookback_minutes": 30
    }
    """
    config = config or {}
    lookback = timedelta(minutes=config.get("lookback_minutes", 30))
    since = datetime.utcnow() - lookback

    all_records: list[DecisionRecord] = []
    alerts_generated = 0

    # 1. Extract from Obsidian vault
    vault_path = config.get("obsidian_vault_path", os.environ.get("OBSIDIAN_VAULT_PATH", ""))
    if vault_path:
        logger.info("Extracting from Obsidian vault: %s", vault_path)
        records = extract_from_vault(vault_path, since=since)
        all_records.extend(records)

    # 2. Extract from GitHub repos
    github_repos = config.get("github_repos", [])
    for repo in github_repos:
        logger.info("Extracting from GitHub: %s/%s", repo["owner"], repo["name"])
        records = extract_from_github(repo["owner"], repo["name"], since=since)
        all_records.extend(records)

    # 3. Extract from Claude Code sessions
    claude_paths = config.get("claude_project_paths", [])
    for path in claude_paths:
        logger.info("Extracting from Claude sessions: %s", path)
        records = extract_from_claude_sessions(path, since=since)
        all_records.extend(records)

    # 4. Extract from Gmail via Hyperspell
    if os.environ.get("HYPERSPELL_API_KEY"):
        logger.info("Extracting from Gmail via Hyperspell")
        gmail_records = extract_gmail_decisions(
            user_id=config.get("hyperspell_user_id", "default-user")
        )
        all_records.extend(gmail_records)

    # 5. Process each record: embed, store, detect
    for record in all_records:
        try:
            # Generate embedding
            record.embedding = generate_embedding(record.content)

            # Store in database
            record_id = store_decision(record)
            record.id = record_id

            # Run contradiction detection
            alert = detect_contradictions(record)
            if alert:
                alerts_generated += 1
                logger.info("Alert generated: %s", alert.explanation[:100])

        except Exception as e:
            logger.error("Error processing record: %s", e)
            continue

    return {
        "records_processed": len(all_records),
        "alerts_generated": alerts_generated,
        "timestamp": datetime.utcnow().isoformat(),
    }
