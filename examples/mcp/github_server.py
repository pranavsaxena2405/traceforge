"""GitHub MCP Server providing code repository, commit history, and PR inspection tools."""
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("traceforge.mcp.github")


class RepositoryInfo(BaseModel):
    name: str
    owner: str
    default_branch: str = "main"
    stars: int = 1420
    language: str = "Python"
    description: str = "E-Commerce Checkout & Payment Gateway API Service"


class CommitInfo(BaseModel):
    sha: str
    author: str
    timestamp: str
    message: str
    files_changed: List[str]
    diff_summary: str
    additions: int
    deletions: int


class PullRequestInfo(BaseModel):
    number: int
    title: str
    author: str
    status: str
    merged_at: str
    related_commits: List[str]


class GitHubMCPServer:
    """Deterministic GitHub MCP Server for incident root cause analysis."""

    def __init__(self, repo_name: str = "acme-corp/checkout-api"):
        self.repo_name = repo_name
        # Deterministic simulation dataset
        self._commits = [
            CommitInfo(
                sha="86a5672",
                author="alex.dev@acmecorp.com",
                timestamp="2026-09-03T14:30:00Z",
                message="feat(checkout): add promo code validation and transaction loyalty lookup",
                files_changed=[
                    "src/checkout/service.py",
                    "src/checkout/db_queries.py",
                ],
                diff_summary=(
                    "+ def validate_loyalty_discount(user_id):\n"
                    "+     # BUG: Executing unindexed sequential query per line item\n"
                    "+     records = db.execute('SELECT * FROM user_purchases WHERE user_id = %s', user_id)\n"
                    "+     for r in records:\n"
                    "+         db.execute('SELECT * FROM loyalty_tiers WHERE item_id = %s', r.item_id)\n"
                ),
                additions=45,
                deletions=3,
            ),
            CommitInfo(
                sha="7724e4d",
                author="priya.eng@acmecorp.com",
                timestamp="2026-09-02T10:15:00Z",
                message="chore(deps): bump fastapi to 0.110.0 and uvicorn to 0.28.0",
                files_changed=["pyproject.toml"],
                diff_summary="- fastapi = 0.109.0\n+ fastapi = 0.110.0",
                additions=2,
                deletions=2,
            ),
            CommitInfo(
                sha="6a19f3b",
                author="devops-bot",
                timestamp="2026-09-01T08:00:00Z",
                message="build: update release version to v1.8.0-rc1",
                files_changed=["VERSION"],
                diff_summary="v1.7.9 -> v1.8.0-rc1",
                additions=1,
                deletions=1,
            ),
        ]

    def get_repository(self, repository: str) -> Dict[str, Any]:
        """Expose get_repository tool schema."""
        if repository != self.repo_name and not repository.endswith("checkout-api"):
            raise ValueError(f"Repository '{repository}' not found in GitHub Organization.")
        repo = RepositoryInfo(name=repository, owner="acme-corp")
        return repo.model_dump()

    def list_recent_commits(self, repository: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Expose list_recent_commits tool."""
        if limit <= 0:
            return []
        return [c.model_dump() for c in self._commits[:limit]]

    def get_commit(self, repository: str, commit_sha: str) -> Dict[str, Any]:
        """Expose get_commit tool."""
        for c in self._commits:
            if c.sha.startswith(commit_sha) or commit_sha in c.sha:
                return c.model_dump()
        raise ValueError(f"Commit SHA '{commit_sha}' not found in repository {repository}")

    def get_pull_request(self, repository: str, pr_number: int) -> Dict[str, Any]:
        """Expose get_pull_request tool."""
        if pr_number == 142:
            return PullRequestInfo(
                number=142,
                title="Add loyalty points auto-redemption on checkout",
                author="alex.dev@acmecorp.com",
                status="merged",
                merged_at="2026-09-03T15:00:00Z",
                related_commits=["86a5672"],
            ).model_dump()
        raise ValueError(f"Pull Request #{pr_number} not found.")

    def search_code(self, repository: str, query: str) -> List[Dict[str, Any]]:
        """Expose search_code tool."""
        results = []
        for c in self._commits:
            if query.lower() in c.diff_summary.lower() or query.lower() in c.message.lower():
                results.append({
                    "file": c.files_changed[0] if c.files_changed else "unknown",
                    "commit_sha": c.sha,
                    "snippet": c.diff_summary,
                })
        return results
