"""Pre-seeded demo data for CogWatch — realistic contradictions for demo.

Run this script to populate the database with realistic decision records
that demonstrate contradiction detection.
"""

import logging
from datetime import datetime, timedelta

from cogwatch.db import store_decision
from cogwatch.llm import generate_embedding
from cogwatch.models import DecisionRecord, DecisionSource, DecisionStatus

logger = logging.getLogger(__name__)

# Realistic decision records that form contradictions
DEMO_DECISIONS = [
    # Contradiction pair 1: REST vs GraphQL
    {
        "source": "github",
        "content": "Decided to use REST API for all backend services. REST is simpler, better tooling, team knows it well. GraphQL adds unnecessary complexity for our use case.",
        "context": "PR #42 in main/backend-api — Architecture Decision Record",
        "days_ago": 21,
        "tags": ["architecture", "api", "backend"],
    },
    {
        "source": "obsidian",
        "content": "Going with GraphQL for the new API layer. Need flexible querying for the dashboard, and the frontend team wants to avoid over-fetching. REST was too rigid.",
        "context": "From note: API Architecture Rethink (architecture/api-design.md)",
        "days_ago": 2,
        "tags": ["architecture", "api", "graphql"],
    },
    # Contradiction pair 2: PostgreSQL vs MongoDB
    {
        "source": "claude_session",
        "content": "After careful analysis, we're using PostgreSQL for everything. Relational model fits our domain perfectly. NoSQL would fragment our data model unnecessarily.",
        "context": "Claude session: database-design-session",
        "days_ago": 30,
        "tags": ["database", "architecture"],
    },
    {
        "source": "github",
        "content": "Adding MongoDB for the event store. PostgreSQL can't handle the write throughput we need for real-time events. Need document flexibility for event schemas.",
        "context": "PR #67 in main/event-system — Adding event store",
        "days_ago": 3,
        "tags": ["database", "events", "mongodb"],
    },
    # Contradiction pair 3: Monolith vs Microservices
    {
        "source": "obsidian",
        "content": "Keeping everything in the monolith for now. Microservices are premature optimization. We don't have the team size or traffic to justify the operational overhead.",
        "context": "From note: Architecture Principles (architecture/principles.md)",
        "days_ago": 45,
        "tags": ["architecture", "infrastructure"],
    },
    {
        "source": "github",
        "content": "Extracting the notification service into its own microservice. The monolith is getting too large, deployments are slow, and we need independent scaling for notifications.",
        "context": "PR #89 in main/notifications — Extract notification microservice",
        "days_ago": 5,
        "tags": ["architecture", "microservices", "notifications"],
    },
    # Non-contradiction: consistent decisions (should NOT trigger)
    {
        "source": "obsidian",
        "content": "Using TypeScript for all new frontend code. Type safety catches bugs early and the team is productive with it.",
        "context": "From note: Frontend Standards (frontend/standards.md)",
        "days_ago": 60,
        "tags": ["frontend", "typescript"],
    },
    {
        "source": "github",
        "content": "Migrated the dashboard components to TypeScript. Follows our established standard for type safety in frontend code.",
        "context": "PR #95 in main/dashboard — TypeScript migration",
        "days_ago": 7,
        "tags": ["frontend", "typescript", "migration"],
    },
    # Stale thread: forgotten TODO
    {
        "source": "obsidian",
        "content": "TODO: Need to decide on caching strategy. Redis vs Memcached vs application-level cache. Will think about this after the auth system is done.",
        "context": "From note: Technical Debt (tech-debt/caching.md)",
        "days_ago": 35,
        "tags": ["caching", "infrastructure", "TODO"],
    },
    # Forgotten resolution: re-asking solved question
    {
        "source": "claude_session",
        "content": "After researching auth solutions, decided on JWT with refresh tokens stored in httpOnly cookies. This gives us stateless auth with secure token storage.",
        "context": "Claude session: auth-research",
        "days_ago": 25,
        "tags": ["auth", "security", "jwt"],
    },
    {
        "source": "claude_session",
        "content": "What's the best approach for authentication? Should we use sessions or JWTs? Need to figure out token storage strategy.",
        "context": "Claude session: new-feature-planning",
        "days_ago": 1,
        "tags": ["auth", "security"],
    },
]


def seed_demo_data() -> dict:
    """Populate the database with demo decision records."""
    now = datetime.utcnow()
    records_created = 0
    errors = 0

    for decision in DEMO_DECISIONS:
        try:
            record = DecisionRecord(
                source=DecisionSource(decision["source"]),
                content=decision["content"],
                context=decision["context"],
                timestamp=now - timedelta(days=decision["days_ago"]),
                tags=decision["tags"],
                status=DecisionStatus.ACTIVE,
            )

            # Generate embedding
            record.embedding = generate_embedding(record.content)

            # Store
            record_id = store_decision(record)
            records_created += 1
            logger.info("Created record %s: %s", record_id, decision["content"][:60])

        except Exception as e:
            logger.error("Error seeding record: %s", e)
            errors += 1

    return {
        "records_created": records_created,
        "errors": errors,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = seed_demo_data()
    print(f"Seeded {result['records_created']} records ({result['errors']} errors)")
