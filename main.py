import argparse
import json
import logging
import os
import sys

from terraform_agents.terraform_enhancer import TerraformEnhancer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("terraform-agent")


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Terraform Security Enhancement Tool")
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository URL (can include nested folders)",
    )
    parser.add_argument("--prompt", required=True, help="Security enhancement prompt")
    parser.add_argument(
        "--output", default="./output", help="Output directory for modified files"
    )
    parser.add_argument("--api-key", help="API key for the LLM provider")
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "anthropic"],
        help="LLM provider",
    )
    parser.add_argument("--github-token", help="GitHub token for private repositories")
    parser.add_argument("--config", help="Path to configuration file")
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    # Load configuration
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)

    # Override config with command-line arguments
    if args.api_key:
        config["api_key"] = args.api_key
    if args.provider:
        config["provider"] = args.provider
    if args.github_token:
        config["github_token"] = args.github_token
    if args.output:
        config["output_dir"] = args.output

    # Check for required configuration
    if "api_key" not in config:
        logger.error(
            "API key is required. Provide it via --api-key or in the configuration file."
        )
        return 1

    # Create enhancer
    enhancer = TerraformEnhancer(config)

    try:
        # Enhance the Terraform code
        modified_files = enhancer.enhance_terraform_code(args.repo, args.prompt)

        # Print summary
        print(f"\nEnhanced {len(modified_files)} files:")
        for file_path in modified_files.keys():
            print(f" - {file_path}")

        print(f"\nResults saved to: {args.output}")
        return 0

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
