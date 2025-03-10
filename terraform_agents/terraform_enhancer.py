import logging
import os
from typing import Any

from terraform_agents.github_utils import GitHubRepo
from terraform_agents.llm import LLMClient
from terraform_agents.terraform_analyzer import TerraformAnalyzer


logger = logging.getLogger("terraform-agent")


class TerraformEnhancer:
    """Main class that orchestrates the enhancement process"""

    def __init__(self, config: dict[str, Any]):
        """Initialize with configuration"""
        self.config = config
        self.llm_client = LLMClient(
            api_key=config.get("api_key", ""), provider=config.get("provider", "openai")
        )

    def enhance_terraform_code(self, repo_url: str, prompt: str) -> dict[str, str]:
        """
        Enhance Terraform code based on user prompt

        Args:
            repo_url: GitHub repository URL
            prompt: User prompt for enhancement

        Returns:
            Dictionary of modified files
        """
        try:
            # Step 1: Clone the repository
            github_repo = GitHubRepo(repo_url, token=self.config.get("github_token"))
            repo_path = github_repo.clone()
            logger.info(f"Cloned repository to {repo_path}")

            # Step 2: Analyze the repository for dependencies
            analyzer = TerraformAnalyzer(repo_path)

            # Step 3: Find files relevant to the user prompt
            relevant_files = analyzer.find_relevant_files(prompt)

            if not relevant_files:
                logger.warning("No relevant files found. Using all Terraform files.")
                relevant_files = analyzer.file_contents

            # Step 4: Use LLM to update the code
            logger.info(f"Sending {len(relevant_files)} files to LLM for enhancement")
            modified_files = self.llm_client.update_terraform_code(
                relevant_files, prompt
            )

            # Step 5: Save results
            if self.config.get("output_dir"):
                self._save_results(
                    modified_files, self.config.get("output_dir", "./output")
                )

            # Step 6: Cleanup
            github_repo.cleanup()

            return modified_files

        except Exception as e:
            logger.error(f"Error enhancing Terraform code: {str(e)}")
            raise

    def _save_results(self, modified_files: dict[str, str], output_dir: str) -> None:
        """Save modified files to the output directory"""
        os.makedirs(output_dir, exist_ok=True)

        for file_path, content in modified_files.items():
            output_path = os.path.join(output_dir, file_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w") as f:
                f.write(content)

        logger.info(f"Saved {len(modified_files)} modified files to {output_dir}")
