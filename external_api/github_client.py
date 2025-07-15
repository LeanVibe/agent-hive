"""
GitHub API Client for Integration Agent

Provides comprehensive GitHub API integration including repository management,
issue tracking, pull requests, and webhook handling.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass
import base64
import hashlib
import hmac
import aiohttp
from urllib.parse import urljoin


logger = logging.getLogger(__name__)


class GitHubEventType(Enum):
    """GitHub webhook event types."""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    RELEASE = "release"
    STAR = "star"
    FORK = "fork"
    WORKFLOW_RUN = "workflow_run"
    DEPLOYMENT = "deployment"
    REPOSITORY = "repository"


class GitHubResourceType(Enum):
    """GitHub resource types."""
    REPOSITORY = "repository"
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
    COMMENT = "comment"
    COMMIT = "commit"
    BRANCH = "branch"
    TAG = "tag"
    RELEASE = "release"
    WORKFLOW = "workflow"
    DEPLOYMENT = "deployment"


@dataclass
class GitHubConfig:
    """GitHub API configuration."""
    base_url: str = "https://api.github.com"
    token: Optional[str] = None
    app_id: Optional[str] = None
    private_key: Optional[str] = None
    webhook_secret: Optional[str] = None
    default_owner: Optional[str] = None
    default_repo: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1
    rate_limit_buffer: int = 100  # Buffer to keep from rate limits


@dataclass
class GitHubWebhookEvent:
    """GitHub webhook event data."""
    event_type: GitHubEventType
    delivery_id: str
    signature: str
    payload: Dict[str, Any]
    timestamp: datetime
    repository: Optional[str] = None
    sender: Optional[str] = None


class GitHubAPIError(Exception):
    """GitHub API error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(message)


class GitHubClient:
    """
    Comprehensive GitHub API client with advanced features.
    
    Supports repository management, issue tracking, pull requests,
    webhooks, and GitHub Apps integration.
    """
    
    def __init__(self, config: GitHubConfig):
        """
        Initialize GitHub client.
        
        Args:
            config: GitHub API configuration
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_info = {
            "remaining": 5000,
            "reset_time": 0,
            "used": 0,
            "limit": 5000
        }
        
        # Request statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limit_hits": 0,
            "retries": 0
        }
        
        # Webhook event handlers
        self.webhook_handlers: Dict[GitHubEventType, List[callable]] = {}
        
        logger.info("GitHubClient initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Connect to GitHub API."""
        if self.session is None:
            headers = {
                "User-Agent": "LeanVibe-Agent-Hive/1.0",
                "Accept": "application/vnd.github.v3+json"
            }
            
            if self.config.token:
                headers["Authorization"] = f"token {self.config.token}"
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=100)
            )
            
            logger.info("Connected to GitHub API")
    
    async def disconnect(self) -> None:
        """Disconnect from GitHub API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from GitHub API")
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to GitHub API with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        if not self.session:
            await self.connect()
        
        url = urljoin(self.config.base_url, endpoint)
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Check rate limits
                await self._check_rate_limit()
                
                # Make request
                async with self.session.request(method, url, **kwargs) as response:
                    # Update rate limit info
                    self._update_rate_limit_info(response.headers)
                    
                    # Update statistics
                    self.stats["total_requests"] += 1
                    
                    # Handle response
                    if response.status == 200 or response.status == 201:
                        self.stats["successful_requests"] += 1
                        return await response.json()
                    elif response.status == 204:
                        self.stats["successful_requests"] += 1
                        return {}
                    elif response.status == 403 and "rate limit" in response.headers.get("x-ratelimit-remaining", ""):
                        # Rate limit hit
                        self.stats["rate_limit_hits"] += 1
                        await self._handle_rate_limit(response.headers)
                        continue
                    elif response.status == 404:
                        self.stats["failed_requests"] += 1
                        raise GitHubAPIError(f"Resource not found: {endpoint}", response.status)
                    else:
                        self.stats["failed_requests"] += 1
                        error_data = await response.json() if response.content_type == "application/json" else {}
                        raise GitHubAPIError(
                            f"GitHub API error: {response.status} - {error_data.get('message', 'Unknown error')}",
                            response.status,
                            error_data
                        )
                        
            except aiohttp.ClientError as e:
                if attempt < self.config.max_retries:
                    self.stats["retries"] += 1
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    continue
                else:
                    self.stats["failed_requests"] += 1
                    raise GitHubAPIError(f"Connection error: {e}")
        
        self.stats["failed_requests"] += 1
        raise GitHubAPIError(f"Max retries exceeded for {endpoint}")
    
    async def _check_rate_limit(self) -> None:
        """Check and handle rate limits."""
        if self.rate_limit_info["remaining"] < self.config.rate_limit_buffer:
            reset_time = self.rate_limit_info["reset_time"]
            current_time = time.time()
            
            if reset_time > current_time:
                sleep_time = reset_time - current_time + 1
                logger.warning(f"Rate limit buffer reached. Sleeping for {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
    
    def _update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """Update rate limit info from response headers."""
        if "x-ratelimit-remaining" in headers:
            self.rate_limit_info["remaining"] = int(headers["x-ratelimit-remaining"])
        if "x-ratelimit-limit" in headers:
            self.rate_limit_info["limit"] = int(headers["x-ratelimit-limit"])
        if "x-ratelimit-reset" in headers:
            self.rate_limit_info["reset_time"] = int(headers["x-ratelimit-reset"])
        if "x-ratelimit-used" in headers:
            self.rate_limit_info["used"] = int(headers["x-ratelimit-used"])
    
    async def _handle_rate_limit(self, headers: Dict[str, str]) -> None:
        """Handle rate limit responses."""
        reset_time = int(headers.get("x-ratelimit-reset", 0))
        current_time = time.time()
        
        if reset_time > current_time:
            sleep_time = reset_time - current_time + 1
            logger.warning(f"Rate limit hit. Sleeping for {sleep_time} seconds")
            await asyncio.sleep(sleep_time)
    
    # Repository operations
    
    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository data
        """
        return await self._make_request("GET", f"/repos/{owner}/{repo}")
    
    async def list_repositories(self, owner: Optional[str] = None, 
                              org: Optional[str] = None, 
                              type: str = "all") -> List[Dict[str, Any]]:
        """
        List repositories.
        
        Args:
            owner: Repository owner (user)
            org: Organization name
            type: Repository type (all, owner, member)
            
        Returns:
            List of repositories
        """
        if org:
            endpoint = f"/orgs/{org}/repos"
        elif owner:
            endpoint = f"/users/{owner}/repos"
        else:
            endpoint = "/user/repos"
        
        params = {"type": type, "per_page": 100}
        return await self._make_request("GET", endpoint, params=params)
    
    async def create_repository(self, name: str, description: str = "", 
                              private: bool = False, owner: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new repository.
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether repository is private
            owner: Repository owner (for org repos)
            
        Returns:
            Created repository data
        """
        data = {
            "name": name,
            "description": description,
            "private": private
        }
        
        if owner:
            endpoint = f"/orgs/{owner}/repos"
        else:
            endpoint = "/user/repos"
        
        return await self._make_request("POST", endpoint, json=data)
    
    # Issue operations
    
    async def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """
        Get issue details.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            
        Returns:
            Issue data
        """
        return await self._make_request("GET", f"/repos/{owner}/{repo}/issues/{issue_number}")
    
    async def list_issues(self, owner: str, repo: str, state: str = "open", 
                         labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List repository issues.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            labels: Filter by labels
            
        Returns:
            List of issues
        """
        params = {"state": state, "per_page": 100}
        if labels:
            params["labels"] = ",".join(labels)
        
        return await self._make_request("GET", f"/repos/{owner}/{repo}/issues", params=params)
    
    async def create_issue(self, owner: str, repo: str, title: str, body: str = "", 
                          labels: Optional[List[str]] = None, 
                          assignees: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a new issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Issue labels
            assignees: Issue assignees
            
        Returns:
            Created issue data
        """
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        
        return await self._make_request("POST", f"/repos/{owner}/{repo}/issues", json=data)
    
    async def update_issue(self, owner: str, repo: str, issue_number: int, 
                          title: Optional[str] = None, body: Optional[str] = None,
                          state: Optional[str] = None, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Update an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            title: New title
            body: New body
            state: New state (open, closed)
            labels: New labels
            
        Returns:
            Updated issue data
        """
        data = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if labels is not None:
            data["labels"] = labels
        
        return await self._make_request("PATCH", f"/repos/{owner}/{repo}/issues/{issue_number}", json=data)
    
    async def add_issue_comment(self, owner: str, repo: str, issue_number: int, 
                               body: str) -> Dict[str, Any]:
        """
        Add comment to an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            body: Comment body
            
        Returns:
            Created comment data
        """
        data = {"body": body}
        return await self._make_request("POST", f"/repos/{owner}/{repo}/issues/{issue_number}/comments", json=data)
    
    # Pull Request operations
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request details.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            Pull request data
        """
        return await self._make_request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
    
    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """
        List repository pull requests.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)
            
        Returns:
            List of pull requests
        """
        params = {"state": state, "per_page": 100}
        return await self._make_request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
    
    async def create_pull_request(self, owner: str, repo: str, title: str, head: str, 
                                 base: str, body: str = "") -> Dict[str, Any]:
        """
        Create a new pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Head branch
            base: Base branch
            body: PR body
            
        Returns:
            Created pull request data
        """
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body
        }
        
        return await self._make_request("POST", f"/repos/{owner}/{repo}/pulls", json=data)
    
    async def merge_pull_request(self, owner: str, repo: str, pr_number: int, 
                                commit_title: Optional[str] = None, 
                                commit_message: Optional[str] = None,
                                merge_method: str = "merge") -> Dict[str, Any]:
        """
        Merge a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            commit_title: Merge commit title
            commit_message: Merge commit message
            merge_method: Merge method (merge, squash, rebase)
            
        Returns:
            Merge result data
        """
        data = {"merge_method": merge_method}
        
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message
        
        return await self._make_request("PUT", f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", json=data)
    
    # Webhook operations
    
    async def create_webhook(self, owner: str, repo: str, url: str, 
                           events: List[str], secret: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a repository webhook.
        
        Args:
            owner: Repository owner
            repo: Repository name
            url: Webhook URL
            events: List of events to subscribe to
            secret: Webhook secret
            
        Returns:
            Created webhook data
        """
        config = {
            "url": url,
            "content_type": "json"
        }
        
        if secret:
            config["secret"] = secret
        
        data = {
            "name": "web",
            "active": True,
            "events": events,
            "config": config
        }
        
        return await self._make_request("POST", f"/repos/{owner}/{repo}/hooks", json=data)
    
    async def list_webhooks(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        List repository webhooks.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of webhooks
        """
        return await self._make_request("GET", f"/repos/{owner}/{repo}/hooks")
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: int) -> None:
        """
        Delete a repository webhook.
        
        Args:
            owner: Repository owner
            repo: Repository name
            webhook_id: Webhook ID
        """
        await self._make_request("DELETE", f"/repos/{owner}/{repo}/hooks/{webhook_id}")
    
    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        if not signature.startswith("sha256="):
            return False
        
        expected_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def process_webhook_event(self, headers: Dict[str, str], payload: bytes) -> GitHubWebhookEvent:
        """
        Process incoming webhook event.
        
        Args:
            headers: Request headers
            payload: Request payload
            
        Returns:
            Processed webhook event
        """
        # Verify signature
        signature = headers.get("x-hub-signature-256", "")
        if self.config.webhook_secret:
            if not self.verify_webhook_signature(payload, signature, self.config.webhook_secret):
                raise GitHubAPIError("Invalid webhook signature")
        
        # Parse event
        event_type = headers.get("x-github-event")
        delivery_id = headers.get("x-github-delivery")
        
        if not event_type or not delivery_id:
            raise GitHubAPIError("Missing required webhook headers")
        
        try:
            event_data = json.loads(payload.decode())
        except json.JSONDecodeError:
            raise GitHubAPIError("Invalid JSON payload")
        
        # Create event object
        webhook_event = GitHubWebhookEvent(
            event_type=GitHubEventType(event_type),
            delivery_id=delivery_id,
            signature=signature,
            payload=event_data,
            timestamp=datetime.now(),
            repository=event_data.get("repository", {}).get("full_name"),
            sender=event_data.get("sender", {}).get("login")
        )
        
        # Trigger event handlers
        await self._trigger_webhook_handlers(webhook_event)
        
        return webhook_event
    
    def register_webhook_handler(self, event_type: GitHubEventType, handler: callable) -> None:
        """
        Register webhook event handler.
        
        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        if event_type not in self.webhook_handlers:
            self.webhook_handlers[event_type] = []
        
        self.webhook_handlers[event_type].append(handler)
        logger.info(f"Registered webhook handler for {event_type.value}")
    
    async def _trigger_webhook_handlers(self, event: GitHubWebhookEvent) -> None:
        """Trigger registered webhook handlers."""
        handlers = self.webhook_handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in webhook handler: {e}")
    
    # File operations
    
    async def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Dict[str, Any]:
        """
        Get file content from repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Branch/commit reference
            
        Returns:
            File content data
        """
        params = {"ref": ref}
        return await self._make_request("GET", f"/repos/{owner}/{repo}/contents/{path}", params=params)
    
    async def create_or_update_file(self, owner: str, repo: str, path: str, 
                                   content: str, message: str, branch: str = "main",
                                   sha: Optional[str] = None) -> Dict[str, Any]:
        """
        Create or update a file in repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: File content (base64 encoded)
            message: Commit message
            branch: Target branch
            sha: File SHA (for updates)
            
        Returns:
            File operation result
        """
        # Encode content to base64
        if isinstance(content, str):
            content = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": message,
            "content": content,
            "branch": branch
        }
        
        if sha:
            data["sha"] = sha
        
        return await self._make_request("PUT", f"/repos/{owner}/{repo}/contents/{path}", json=data)
    
    # Workflow operations
    
    async def list_workflows(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        List repository workflows.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of workflows
        """
        response = await self._make_request("GET", f"/repos/{owner}/{repo}/actions/workflows")
        return response.get("workflows", [])
    
    async def trigger_workflow(self, owner: str, repo: str, workflow_id: str, 
                              ref: str = "main", inputs: Optional[Dict[str, str]] = None) -> None:
        """
        Trigger a workflow dispatch.
        
        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Workflow ID or filename
            ref: Branch/tag reference
            inputs: Workflow inputs
        """
        data = {"ref": ref}
        if inputs:
            data["inputs"] = inputs
        
        await self._make_request("POST", f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches", json=data)
    
    async def get_workflow_runs(self, owner: str, repo: str, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get workflow runs.
        
        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Optional workflow ID filter
            
        Returns:
            List of workflow runs
        """
        if workflow_id:
            endpoint = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
        else:
            endpoint = f"/repos/{owner}/{repo}/actions/runs"
        
        response = await self._make_request("GET", endpoint)
        return response.get("workflow_runs", [])
    
    # Utility methods
    
    async def search_repositories(self, query: str, sort: str = "stars", order: str = "desc") -> List[Dict[str, Any]]:
        """
        Search repositories.
        
        Args:
            query: Search query
            sort: Sort field
            order: Sort order
            
        Returns:
            Search results
        """
        params = {"q": query, "sort": sort, "order": order}
        response = await self._make_request("GET", "/search/repositories", params=params)
        return response.get("items", [])
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get rate limit status.
        
        Returns:
            Rate limit information
        """
        response = await self._make_request("GET", "/rate_limit")
        return response.get("resources", {})
    
    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Client statistics
        """
        return {
            "stats": self.stats.copy(),
            "rate_limit": self.rate_limit_info.copy(),
            "webhook_handlers": {
                event_type.value: len(handlers)
                for event_type, handlers in self.webhook_handlers.items()
            },
            "connected": self.session is not None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health check result
        """
        try:
            await self.get_rate_limit_status()
            return {
                "status": "healthy",
                "connected": True,
                "rate_limit": self.rate_limit_info,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }