import json
import logging
import re


logger = logging.getLogger("terraform-agent")


class LLMClient:
    """Client for communicating with LLM APIs"""

    def __init__(self, api_key: str, provider: str = "openai"):
        """Initialize with API key and provider"""
        self.api_key = api_key
        self.provider = provider.lower()

    def update_terraform_code(
        self, files_dict: dict[str, str], prompt: str
    ) -> dict[str, str]:
        """
        Send files to the LLM with a prompt to update them

        Args:
            files_dict: Dictionary mapping file paths to their contents
            prompt: User prompt for code modification

        Returns:
            Dictionary of updated file contents
        """
        # Prepare system prompt
        system_prompt = """
        You are an expert Terraform developer specializing in AWS infrastructure. \
        Your task is to analyze and modify Terraform code according to the user's requirements.

        Follow these guidelines:
        1. Carefully analyze all provided Terraform files
        2. Understand the infrastructure being deployed
        3. Make only the necessary changes to fulfill the user's specific requirements
        4. Maintain the existing code structure and style
        5. Document your changes with comments
        6. Return all modified files with their complete content
        7. Format the output as JSON with the file path as key and modified content as value

        Before making changes:
        - Identify all dependencies between files to ensure your modifications are consistent
        - Consider AWS best practices relevant to the user's requirements
        - Don't make unrelated changes that weren't requested by the user
        - If the user asks for security enhancements, focus on proper security group rules, encryption, IAM policies, etc.
        - If the user asks for performance improvements, focus on appropriate instance types, scaling configurations, etc.
        - If the user asks for cost optimizations, focus on resource sizing, reserved instances, lifecycle policies, etc.
        """

        # Format the files content for the prompt
        files_content = ""
        for file_path, content in files_dict.items():
            files_content += f"\n\n--- File: {file_path} ---\n\n{content}"

        # Construct the full prompt
        user_message = f"""
USER REQUIREMENTS:
{prompt}

TERRAFORM FILES:
{files_content}

Please analyze these files and make the necessary changes to fulfill the requirements.
Return the modified files in JSON format where each key is the file path and each value is the complete modified content.
Only return the files that you've modified - don't include unchanged files.
"""

        # Determine which API to use
        if self.provider == "anthropic":
            return self._call_anthropic_api(system_prompt, user_message)
        else:  # default to OpenAI
            return self._call_openai_api(system_prompt, user_message)

    def _call_openai_api(self, system_prompt: str, user_message: str) -> dict[str, str]:
        """Call OpenAI API to generate code updates"""
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=8000,
            )

            result = response.choices[0].message.content
            return self._extract_modified_files(result)

        except ImportError:
            logger.error(
                "OpenAI library not available. Install with: pip install openai"
            )
            return {}
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {}

    def _call_anthropic_api(
        self, system_prompt: str, user_message: str
    ) -> dict[str, str]:
        """Call Anthropic API to generate code updates"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system=system_prompt,
                max_tokens=8000,
                messages=[{"role": "user", "content": user_message}],
            )

            result = response.content[0].text
            return self._extract_modified_files(result)

        except ImportError:
            logger.error(
                "Anthropic library not available. Install with: pip install anthropic"
            )
            return {}
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {str(e)}")
            return {}

    def _extract_modified_files(self, response: str) -> dict[str, str]:
        """Extract modified files from the LLM response"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
            if json_match:
                json_str = json_match.group(1)
                modified_files = json.loads(json_str)
                logger.info(
                    f"Extracted {len(modified_files)} modified files from JSON response"
                )
                return modified_files
            else:
                # If no JSON block is found, try to parse the entire response
                modified_files = json.loads(response)
                logger.info(
                    f"Extracted {len(modified_files)} modified files from direct JSON response"
                )
                return modified_files

        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from LLM response")
            # If JSON parsing fails, try to extract file sections manually
            return self._extract_files_manually(response)

    def _extract_files_manually(self, text: str) -> dict[str, str]:
        """Extract file contents manually from text if JSON parsing fails"""
        files = {}
        file_pattern = (
            r"---\s*File:\s*([\w\./\\-]+)\s*---\s*([\s\S]*?)(?=---\s*File:|$)"
        )

        for match in re.finditer(file_pattern, text):
            file_path = match.group(1).strip()
            content = match.group(2).strip()
            files[file_path] = content

        logger.info(f"Manually extracted {len(files)} modified files from response")
        return files
