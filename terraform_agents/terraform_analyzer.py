import logging
import os
import re
from pathlib import Path
from typing import Optional


logger = logging.getLogger("terraform-agent")


class TerraformAnalyzer:
    """Analyzes Terraform code to find relevant files and relationships"""

    def __init__(self, repo_path: str):
        """Initialize with repository path"""
        self.repo_path = repo_path
        self.file_contents: dict[str, str] = {}
        self.dependency_graph: dict[str, list[str]] = {}
        self._load_terraform_files()

    def _load_terraform_files(self) -> None:
        """Load all Terraform files from the repository"""
        terraform_files = list(Path(self.repo_path).glob("**/*.tf"))
        logger.info(f"Found {len(terraform_files)} Terraform files in repository")

        for file_path in terraform_files:
            relative_path = str(file_path.relative_to(self.repo_path))
            try:
                file_content = file_path.read_text()
                self.file_contents[relative_path] = file_content
                self.dependency_graph[relative_path] = []
                logger.debug(f"Loaded file: {relative_path}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")

        # Find dependencies between files
        self._build_dependency_graph()

    def _build_dependency_graph(self) -> None:
        """Build a simple dependency graph between Terraform files"""
        # Look for references between files
        for file_path, content in self.file_contents.items():
            # Look for module sources
            module_sources = self._extract_module_sources(content)

            # Look for variable references
            var_refs = self._extract_variable_references(content)

            # For each module source, find the corresponding files
            for source in module_sources:
                if source.startswith("./") or source.startswith("../"):
                    # Calculate the absolute path of the module
                    source_dir = os.path.normpath(
                        os.path.join(os.path.dirname(file_path), source)
                    )

                    # Find all .tf files in this directory
                    for other_file in self.file_contents.keys():
                        if other_file.startswith(source_dir):
                            self.dependency_graph[file_path].append(other_file)
                            logger.debug(
                                f"Added dependency: {file_path} -> {other_file}"
                            )

            # For each variable reference, find the corresponding variable declaration
            for var_name in var_refs:
                for other_file, other_content in self.file_contents.items():
                    if f'variable "{var_name}"' in other_content:
                        self.dependency_graph[file_path].append(other_file)
                        logger.debug(
                            f"Added variable dependency: {file_path} -> {other_file}"
                        )

    def _extract_module_sources(self, content: str) -> list[str]:
        """Extract module sources from Terraform content"""
        sources = []
        # Look for module blocks and their sources
        module_pattern = (
            r'module\s+["\']([\w-]+)["\']\s*{[^}]*source\s*=\s*["\']([\w\.\/-]+)["\']'
        )
        for match in re.finditer(module_pattern, content):
            sources.append(match.group(2))
        return sources

    def _extract_variable_references(self, content: str) -> list[str]:
        """Extract variable references from Terraform content"""
        var_pattern = r"var\.([a-zA-Z0-9_-]+)"
        matches = re.findall(var_pattern, content)
        return list(set(matches))  # Return unique variable names

    def find_relevant_files(self, prompt: str) -> dict[str, str]:
        """Find files relevant to the user prompt"""
        relevant_files = {}

        # Extract keywords from the prompt
        keywords = self._extract_keywords_from_prompt(prompt)
        logger.info(f"Extracted keywords from prompt: {keywords}")

        # First pass: find files with direct keyword references
        for file_path, content in self.file_contents.items():
            content_lower = content.lower()
            if any(keyword in content_lower for keyword in keywords) or any(
                keyword in file_path.lower() for keyword in keywords
            ):
                relevant_files[file_path] = content
                logger.debug(f"Found relevant file by keyword: {file_path}")

        # If the prompt mentions VPC specifically, also include VPC-related files
        if any(vpc_term in prompt.lower() for vpc_term in ["vpc", "network"]):
            vpc_keywords = ["vpc", "subnet", "cidr", "network", "route", "gateway"]
            for file_path, content in self.file_contents.items():
                if file_path not in relevant_files:
                    content_lower = content.lower()
                    if any(keyword in content_lower for keyword in vpc_keywords) or any(
                        keyword in file_path.lower() for keyword in vpc_keywords
                    ):
                        relevant_files[file_path] = content
                        logger.debug(f"Found VPC-related file: {file_path}")

        # Second pass: add dependencies
        dependency_files = {}
        for file_path in list(relevant_files.keys()):
            dependencies = self._find_all_dependencies(file_path)
            for dep in dependencies:
                if dep not in relevant_files and dep in self.file_contents:
                    dependency_files[dep] = self.file_contents[dep]
                    logger.debug(f"Added dependency file: {dep}")

        # Combine the results
        relevant_files.update(dependency_files)

        # If we still don't have enough files, add main.tf and other important files
        if len(relevant_files) < 3:
            for file_path, content in self.file_contents.items():
                if file_path not in relevant_files and file_path.endswith(
                    ("main.tf", "variables.tf", "outputs.tf")
                ):
                    relevant_files[file_path] = content
                    logger.debug(f"Added important file: {file_path}")

        logger.info(f"Found {len(relevant_files)} relevant files for prompt")
        return relevant_files

    def _extract_keywords_from_prompt(self, prompt: str) -> list[str]:
        """Extract relevant keywords from the user prompt"""
        # Convert to lowercase
        prompt_lower = prompt.lower()

        # Define common Terraform resource types and concepts
        terraform_keywords = [
            "vpc",
            "subnet",
            "security_group",
            "nacl",
            "sg",
            "security",
            "network",
            "flow_log",
            "encryption",
            "firewall",
            "route",
            "gateway",
            "iam",
            "policy",
            "ec2",
            "rds",
            "lambda",
            "s3",
            "kms",
            "ssl",
            "tls",
            "https",
            "alb",
            "elb",
            "load_balancer",
            "autoscaling",
            "cloudwatch",
            "logs",
            "cloudtrail",
            "monitoring",
            "alerts",
            "backup",
            "storage",
        ]

        # Find terraform keywords in the prompt
        found_keywords = []
        for keyword in terraform_keywords:
            if keyword in prompt_lower:
                found_keywords.append(keyword)

        # If no specific keywords, extract all significant words
        if not found_keywords:
            import re

            stop_words = {
                "update",
                "the",
                "by",
                "adding",
                "and",
                "or",
                "with",
                "for",
                "to",
                "in",
                "on",
                "a",
                "an",
                "this",
                "that",
                "these",
                "those",
                "our",
                "your",
                "my",
                "mine",
                "we",
                "need",
                "want",
                "should",
                "will",
            }
            words = re.findall(r"\b\w{3,}\b", prompt_lower)
            found_keywords = [word for word in words if word not in stop_words]

        return found_keywords

    def _find_all_dependencies(
        self, file_path: str, visited: Optional[set[str]] = None
    ) -> list[str]:
        """Find all dependencies of a file recursively"""
        if visited is None:
            visited = set()

        if file_path in visited:
            return []

        visited.add(file_path)
        dependencies = []

        for dep in self.dependency_graph.get(file_path, []):
            dependencies.append(dep)
            dependencies.extend(self._find_all_dependencies(dep, visited))

        return list(set(dependencies))  # Return unique dependencies
