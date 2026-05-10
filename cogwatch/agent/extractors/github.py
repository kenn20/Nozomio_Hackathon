"""GitHub extractor — fetches decisions from PRs, commits, and review comments."""

import logging
from datetime import datetime

import httpx

from cogwatch.config import GITHUB_TOKEN
from cogwatch.models import DecisionRecord, DecisionSource

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def extract_from_github(
    repo_owner: str,
    repo_name: str,
    since: datetime | None = None,
) -> list[DecisionRecord]:
    """Extract decision records from GitHub repo activity.

    Args:
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        since: Only process activity after this timestamp.

    Returns:
        List of extracted DecisionRecord objects.
    """
    records: list[DecisionRecord] = []
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
    }

    if not GITHUB_TOKEN:
        logger.warning("No GITHUB_TOKEN set, skipping GitHub extraction")
        return records

    with httpx.Client(headers=headers, timeout=30) as client:
        # Extract from recent commits
        records.extend(_extract_commits(client, repo_owner, repo_name, since))

        # Extract from PRs
        records.extend(_extract_prs(client, repo_owner, repo_name, since))

    logger.info("Extracted %d records from GitHub %s/%s", len(records), repo_owner, repo_name)
    return records


def _extract_commits(
    client: httpx.Client,
    owner: str,
    repo: str,
    since: datetime | None,
) -> list[DecisionRecord]:
    """Extract decision-relevant content from commit messages."""
    records: list[DecisionRecord] = []
    params: dict = {"per_page": 50}
    if since:
        params["since"] = since.isoformat()

    try:
        resp = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/commits", params=params)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch commits: %s", e)
        return records

    for commit in resp.json():
        message = commit.get("commit", {}).get("message", "")
        if len(message) < 20:
            continue

        # Only extract commits with substantial messages (likely design decisions)
        if len(message) > 80 or any(
            kw in message.lower()
            for kw in ["because", "instead of", "decided", "refactor", "migrate", "switch"]
        ):
            date_str = commit.get("commit", {}).get("committer", {}).get("date", "")
            timestamp = (
                datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if date_str
                else datetime.utcnow()
            )

            records.append(
                DecisionRecord(
                    source=DecisionSource.GITHUB,
                    content=message[:500],
                    context=f"Commit {commit.get('sha', '')[:8]} in {owner}/{repo}",
                    timestamp=timestamp,
                    tags=["commit"],
                )
            )

    return records


def _extract_prs(
    client: httpx.Client,
    owner: str,
    repo: str,
    since: datetime | None,
) -> list[DecisionRecord]:
    """Extract decision-relevant content from PR descriptions and comments."""
    records: list[DecisionRecord] = []

    try:
        params: dict = {"state": "all", "per_page": 20, "sort": "updated", "direction": "desc"}
        resp = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls", params=params)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch PRs: %s", e)
        return records

    for pr in resp.json():
        body = pr.get("body") or ""
        title = pr.get("title", "")
        pr_number = pr.get("number", "?")

        if since:
            updated_at = pr.get("updated_at", "")
            if updated_at:
                pr_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if pr_date < since:
                    continue

        # Extract from PR description if substantial
        if len(body) > 50:
            created = pr.get("created_at", "")
            timestamp = (
                datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created
                else datetime.utcnow()
            )

            records.append(
                DecisionRecord(
                    source=DecisionSource.GITHUB,
                    content=f"{title}\n\n{body[:400]}",
                    context=f"PR #{pr_number} in {owner}/{repo}",
                    timestamp=timestamp,
                    tags=["pull_request"],
                )
            )

        # Extract from PR review comments
        try:
            comments_resp = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                params={"per_page": 10},
            )
            comments_resp.raise_for_status()
            for comment in comments_resp.json():
                comment_body = comment.get("body", "")
                if len(comment_body) > 50 and any(
                    kw in comment_body.lower()
                    for kw in ["should", "decided", "let's", "instead", "better to", "reason"]
                ):
                    created = comment.get("created_at", "")
                    timestamp = (
                        datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if created
                        else datetime.utcnow()
                    )
                    records.append(
                        DecisionRecord(
                            source=DecisionSource.GITHUB,
                            content=comment_body[:500],
                            context=f"PR #{pr_number} review comment in {owner}/{repo}",
                            timestamp=timestamp,
                            tags=["review_comment"],
                        )
                    )
        except Exception as e:
            logger.warning("Failed to fetch PR comments for #%s: %s", pr_number, e)

    return records
