# Terraform Enhancer Agent

## Problem Statement

Terraform modules are widely reused across projects, but updating an existing Infrastructure-as-Code (IaC) codebase-especially one with nested modules and shared references-can be time-consuming and error-prone.

The goal of this project is to automatically enhance an existing Terraform codebase using a natural-language prompt. Given a public Terraform repository (e.g., examples from [`terraform-aws-modules/terraform-aws-vpc`](https://github.com/terraform-aws-modules/terraform-aws-vpc/tree/master/examples)) and a user prompt such as:

> **“Update the VPC by adding security”**

the system should:

1. Identify the relevant Terraform modules and resources (e.g., VPC)
2. Resolve referenced and dependent files (including relative module sources)
3. Pass only the necessary context to an LLM
4. Generate updated Terraform code with the requested enhancements applied

## Solution Overview

The output is the same Terraform codebase, modified to include the requested changes while preserving structure and dependencies.

The core functionality of this Agent includes:
1. Fetching code from GitHub repositories (public/private)
2. Analyzing the codebase to find relevant files
3. Using LLM to update code based on user prompts
4. Reviewing and presenting the updated code

Here's a simplified implementation that captures these aspects, It includes:

1. A `GitHubRepo` class for handling GitHub repository operations
2. A `TerraformAnalyzer` class for analyzing Terraform code and finding dependencies
3. An `LLMClient` class for communicating with LLM APIs (supporting both OpenAI and Anthropic)
4. A `TerraformEnhancer` class that orchestrates the entire process


## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up config variables:
   ```json
    {
        "api_key": "sk-",
        "provider": "openai"
    }
   ```

## Usage

### Command-line Interface

Process a single query:

```bash
python main.py --repo https://github.com/terraform-aws-modules/terraform-aws-vpc/tree/master/examples/complete --prompt "Update the VPC by adding security" --config "config.json"
```

## Things to consider:

### 1. How can we store these entire codebases from the customer that we import? Do we need some sort of a database?

Yes, storing entire codebases would benefit from a database approach. We can use three different storage systems:

- **MongoDB** for document storage (storing file contents)
- **Neo4j** for graph storage (storing code relationships)
- **Vector Database** for storing embeddings (for semantic search)

For a production system, this multi-database approach makes sense. MongoDB stores the actual content, Neo4j stores the relationships between files and resources, and a vector database enables semantic search capabilities.

In the Current Approach, I simplified this to in-memory storage, but for a real system, a combination of:
- Document database (MongoDB) for file contents
- Graph database (Neo4j) for code relationships
- Vector database for embeddings (FAISS, Milvus, Pinecone, etc.)

would provide comprehensive storage and retrieval capabilities.

### 2. How do we fetch the relevant files from a massive codebase?
(we don't want to pass the whole codebase in the context as it will be very expensive from the LLM side)

We can use 4 different methods to find relevant files:

1. **Embedding-based search**: Using embeddings to find semantically similar content
2. **LLM-based analysis**: Using an LLM to identify relevant files (Optional)
3. **Keyword matching**: Finding files based on specific keywords (VPC, security, etc.)
4. **Dependency analysis**: Following file dependencies to find related files

In the Current Approach, I've implemented a simplified version that focuses on:
- Keyword matching to find VPC-related files
- Dependency analysis to find related files

For a production system, combining all these techniques would provide the best results:
1. Create embeddings for all files
2. Use semantic search to find the most relevant files
3. Analyze dependencies to include related files
4. Use an LLM to refine the selection of files (Can be optional)

### 3. Could we utilize an architecture like knowledge graphs, tree structure to represent and store the code?

Yes, knowledge graphs are an excellent way to represent code relationships and can be used to enhance the overall relationship between individual entities.

- Neo4j for storing the graph of dependencies
- Custom relationship builder to build relationships between files, resources, modules, etc.

This approach allows you to:
- Track dependencies between files
- Understand how resources relate to each other
- Follow data flow through the infrastructure
- Query for specific patterns or relationships

In the Current Approach, I've simplified this to a basic dependency graph using dictionaries, but for a full implementation, a proper graph database like Neo4j would be essential.

### 4. How will RAG be used here? Graph RAG perhaps?

Retrieval-Augmented Generation (RAG) is crucial for this application. We can implement this like below:

1. **Vector search**: Finding semantically similar files based on the query
2. **Graph traversal**: Using the knowledge graph to find related content
3. **LLM-based enhancement**: Using the retrieved context to enhance the code

For a production system, Graph RAG would be particularly powerful:
1. Use vector search to find initial candidate files
2. Use graph relationships to expand the context (finding dependencies)
3. Rank the combined results by relevance
4. Provide the most relevant subset to the LLM for enhancement

### 5. How can we utilize agent building here?

We can use a multi-agent architecture approach with individual agents like below:

- Fetcher Agent: Fetches and analyzes code
- Analyzer Agent: Finds relevant files for a user prompt
- Generator Agent: Generates updated code using LLMs
- Reviewer Agent: Reviews generated code for correctness and security
- Workflow Agent: Coordinates the entire workflow

For a production system, this could be expanded further:
1. **GitHub Agent**: Handles Git repostiories cloning, storing and Pull Request
2. **Parsing Agent**: Specialized in parsing and understanding Terraform code
3. **Security Agent**: Focuses on security best practices for Terraform
4. **Testing Agent**: Tests the generated code for correctness
5. **Explanation Agent**: Generates detailed explanations of changes
6. **Deployment Agent**: Handles deploying or submitting changes
7. **Learning Agent**: Improves over time by learning from successful/failed enhancements

The orchestration of these agents would ensure each specialized task is handled by an agent with the appropriate expertise.
