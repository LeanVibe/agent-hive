#!/usr/bin/env python3
"""
GitHub App Authentication System
Provides secure authentication for agents to interact with GitHub API
"""

import base64
import json
import subprocess
import time
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import jwt
import requests
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

class GitHubAppAuth:
    """GitHub App authentication manager for agent PR operations."""

    def __init__(self, app_id: str = None, private_key_path: str = None):
        """
        Initialize GitHub App authentication.

        Args:
            app_id: GitHub App ID (defaults to env var GITHUB_APP_ID)
            private_key_path: Path to private key file (defaults to env var GITHUB_APP_PRIVATE_KEY_PATH)
        """
        self.app_id = app_id or os.getenv('GITHUB_APP_ID')
        self.private_key_path = private_key_path or os.getenv('GITHUB_APP_PRIVATE_KEY_PATH', '.github/app-private-key.pem')

        if not self.app_id:
            raise ValueError("GitHub App ID not provided. Set GITHUB_APP_ID environment variable.")

        self.private_key = self._load_private_key()
        self.installation_token_cache = {}
        self.installation_id_cache = {}

    def _load_private_key(self) -> str:
        """Load GitHub App private key."""
        key_path = Path(self.private_key_path)

        # Try multiple locations for the private key
        possible_paths = [
            key_path,
            Path('.github/app-private-key.pem'),
            Path('.claude/secrets/github-app-key.pem'),
            Path(os.path.expanduser('~/.github/app-private-key.pem'))
        ]

        for path in possible_paths:
            if path.exists():
                with open(path, 'r') as f:
                    return f.read()

        # Check for base64 encoded key in environment
        if encoded_key := os.getenv('GITHUB_APP_PRIVATE_KEY_BASE64'):
            return base64.b64decode(encoded_key).decode('utf-8')

        # Check for direct key in environment (less secure)
        if direct_key := os.getenv('GITHUB_APP_PRIVATE_KEY'):
            return direct_key

        raise FileNotFoundError(
            f"GitHub App private key not found. Tried: {possible_paths}. "
            "Also checked GITHUB_APP_PRIVATE_KEY_BASE64 and GITHUB_APP_PRIVATE_KEY env vars."
        )

    def generate_jwt(self) -> str:
        """Generate JWT for GitHub App authentication."""
        now = int(time.time())
        payload = {
            'iat': now - 60,  # Issued at (60 seconds ago to account for clock skew)
            'exp': now + 600,  # Expires (10 minutes from now)
            'iss': self.app_id  # Issuer (GitHub App ID)
        }

        # Load private key
        private_key = serialization.load_pem_private_key(
            self.private_key.encode(),
            password=None
        )

        return jwt.encode(payload, private_key, algorithm='RS256')

    def get_installation_id(self, owner: str, repo: str) -> str:
        """Get installation ID for a repository."""
        cache_key = f"{owner}/{repo}"

        if cache_key in self.installation_id_cache:
            return self.installation_id_cache[cache_key]

        jwt_token = self.generate_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # Try organization installation first
        url = f"https://api.github.com/orgs/{owner}/installation"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            installation_id = str(response.json()['id'])
            self.installation_id_cache[cache_key] = installation_id
            return installation_id

        # Try repository installation
        url = f"https://api.github.com/repos/{owner}/{repo}/installation"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            installation_id = str(response.json()['id'])
            self.installation_id_cache[cache_key] = installation_id
            return installation_id

        raise Exception(f"Could not find GitHub App installation for {owner}/{repo}: {response.text}")

    def get_installation_token(self, owner: str, repo: str) -> str:
        """Get installation access token for repository operations."""
        installation_id = self.get_installation_id(owner, repo)

        # Check cache for valid token
        cache_key = f"{owner}/{repo}"
        if cache_key in self.installation_token_cache:
            token_data = self.installation_token_cache[cache_key]
            expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))

            # Return cached token if it's valid for more than 5 minutes
            if expires_at > datetime.now().astimezone() + timedelta(minutes=5):
                return token_data['token']

        # Generate new installation token
        jwt_token = self.generate_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        response = requests.post(url, headers=headers)

        if response.status_code == 201:
            token_data = response.json()
            self.installation_token_cache[cache_key] = token_data
            return token_data['token']

        raise Exception(f"Could not create installation token: {response.text}")

    def get_authenticated_headers(self, owner: str, repo: str) -> Dict[str, str]:
        """Get headers with installation token for API requests."""
        token = self.get_installation_token(owner, repo)
        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'LeanVibe-Agent-Hive/1.0'
        }

    def test_authentication(self, owner: str, repo: str) -> bool:
        """Test if authentication is working for a repository."""
        try:
            headers = self.get_authenticated_headers(owner, repo)
            url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                logger.info(f"✅ GitHub App authentication successful for {owner}/{repo}")
                return True
            else:
                logger.error(f"❌ GitHub App authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ GitHub App authentication error: {e}")
            return False

def setup_github_auth() -> GitHubAppAuth:
    """Setup GitHub App authentication with fallbacks."""
    try:
        return GitHubAppAuth()
    except (ValueError, FileNotFoundError) as e:
        logger.warning(f"⚠️ GitHub App authentication not available: {e}")
        logger.info("📝 To enable GitHub App authentication:")
        logger.info("   1. Create a GitHub App at https://github.com/settings/apps")
        logger.info("   2. Set GITHUB_APP_ID environment variable")
        logger.info("   3. Save private key to .github/app-private-key.pem or set GITHUB_APP_PRIVATE_KEY_BASE64")
        logger.info("   4. Install the app on your repository")
        return None

def get_repository_info() -> tuple:
    """Get current repository owner and name from git remote."""
    try:
        # Get remote URL
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, check=True
        )
        remote_url = result.stdout.strip()

        # Parse GitHub URL
        if 'github.com' in remote_url:
            if remote_url.startswith('git@github.com:'):
                # SSH format: git@github.com:owner/repo.git
                repo_path = remote_url.replace('git@github.com:', '').replace('.git', '')
            elif remote_url.startswith('https://github.com/'):
                # HTTPS format: https://github.com/owner/repo.git
                repo_path = remote_url.replace('https://github.com/', '').replace('.git', '')
            else:
                raise ValueError(f"Unexpected GitHub URL format: {remote_url}")

            owner, repo = repo_path.split('/', 1)
            return owner, repo
        else:
            raise ValueError(f"Remote is not a GitHub repository: {remote_url}")

    except subprocess.CalledProcessError as e:
        raise Exception(f"Could not get git remote: {e}")

def main():
    """Test GitHub App authentication."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        # Setup authentication
        auth = setup_github_auth()
        if not auth:
            return 1

        # Get repository info
        owner, repo = get_repository_info()
        logger.info(f"🔍 Testing authentication for {owner}/{repo}")

        # Test authentication
        success = auth.test_authentication(owner, repo)
        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ Authentication test failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
