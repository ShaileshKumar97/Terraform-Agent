import logging
import os
import re
import shutil
import tempfile
from typing import Optional

from git import Repo

logger = logging.getLogger("terraform-agent")


class GitHubRepo:
    """Handles GitHub repository operations including nested folders"""

    def __init__(self, repo_url: str, token: Optional[str] = None):
        """
        Initialize with a GitHub repository URL

        Args:
            repo_url: URL to GitHub repository, can include nested folders
            token: Optional GitHub token for private repositories
        """
        self.repo_url = repo_url
        self.token = token
        self.temp_dir: Optional[str] = None
        self.nested_path: Optional[str] = None
        self.clone_url: str = ""
        self.branch = "main"
        self._parse_repo_url()

    def _parse_repo_url(self) -> None:
        """Parse the repository URL to extract repository and nested path if any"""
        # Match GitHub URL pattern with optional path components
        pattern = r"https://github\.com/([^/]+/[^/]+)(?:/tree/([^/]+)(?:/(.+))?)?"
        match = re.match(pattern, self.repo_url)

        if match:
            self.repo_name = match.group(1)
            self.branch = match.group(2) or "main"
            self.nested_path = match.group(3)

            # Create the base URL for cloning (without tree/branch/path)
            self.clone_url = f"https://github.com/{self.repo_name}"

            # If token is provided, add it to the URL for private repositories
            if self.token:
                self.auth_url = self.clone_url.replace(
                    "https://github.com", f"https://{self.token}@github.com"
                )
            else:
                self.auth_url = self.clone_url

            logger.info(
                f"Parsed repo: {self.repo_name}, branch: {self.branch}, nested path: {self.nested_path or 'None'}"
            )
        else:
            # If the URL doesn't match the pattern, use it as is
            self.clone_url = self.repo_url
            self.nested_path = None

            # Apply token if provided
            if self.token and self.clone_url.startswith("https://github.com"):
                self.auth_url = self.clone_url.replace(
                    "https://github.com", f"https://{self.token}@github.com"
                )
            else:
                self.auth_url = self.clone_url

            logger.warning(
                f"Could not parse repository URL: {self.repo_url}, using as is"
            )

    def clone(self) -> str:
        """
        Clone the repository to a temporary directory and return the path

        Returns:
            Path to the cloned repository or nested folder within it
        """
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Cloning {self.clone_url} to {self.temp_dir}")

        try:
            # Clone the repository - try with auth URL first
            try:
                Repo.clone_from(self.auth_url, self.temp_dir, branch=self.branch)
                logger.info("Repository cloned successfully using authentication")
            except Exception as e:
                # If authentication fails or token is not provided, try without auth
                if not self.token or "authentication failed" in str(e).lower():
                    logger.info(
                        "Trying to clone without authentication (public repository)"
                    )
                    Repo.clone_from(self.clone_url, self.temp_dir, branch=self.branch)
                    logger.info("Repository cloned successfully as public repository")
                else:
                    raise

            # If a nested path is specified, return the path to that directory
            if self.nested_path:
                nested_dir = os.path.join(self.temp_dir, self.nested_path)
                if os.path.exists(nested_dir):
                    logger.info(f"Using nested directory: {self.nested_path}")
                    return nested_dir
                else:
                    logger.error(f"Nested directory not found: {self.nested_path}")
                    raise FileNotFoundError(
                        f"Nested directory not found: {self.nested_path}"
                    )

            # If no nested path or it doesn't exist, return the repo root
            return self.temp_dir

        except Exception as e:
            logger.error(f"Failed to clone repository: {str(e)}")
            self.cleanup()
            raise

    def cleanup(self) -> None:
        """Clean up the temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
            import time

            time.sleep(1)
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
