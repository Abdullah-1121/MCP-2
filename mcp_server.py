from pathlib import Path
from typing import List
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP , Context
from pydantic import BaseModel, Field
from mcp.server.fastmcp.prompts import base
from mcp.types import SamplingMessage , TextContent
from mcp import types
import asyncio
from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
    TextContent,
)
# === COMPLETION DATA ===
LANGUAGES = ["python", "javascript", "typescript", "java", "go", "rust"]
FRAMEWORKS = {
    "python": ["fastapi", "flask", "django"],
    "javascript": ["express", "react", "vue"],
    "typescript": ["nestjs", "angular", "next"]
}
GITHUB_OWNERS = ["microsoft", "google", "facebook", "openai", "anthropic"]
GITHUB_REPOS = {
    "microsoft": ["vscode", "typescript", "playwright"],
    "google": ["angular", "tensorflow", "protobuf"],
    "openai": ["openai-python", "gpt-4", "whisper"]
}
mcp = FastMCP("DocumentMCP", log_level="ERROR", stateless_http=False) # False for the Elicitation Demo

docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}


@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document and return it as a string."
)
def read_document(
    doc_id: str = Field(description="Id of the document to read")
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")

    return docs[doc_id]

@mcp.prompt(description="Code review with completable language")
def review_code(language: str, focus: str = "all") -> str:
    """Review code with language and focus completions."""
    return f"Please review this {language} code focusing on {focus} aspects."


@mcp.prompt(description="Project setup with context-aware framework")
def setup_project(language: str, framework: str) -> str:
    """Setup project with language and framework completions."""
    return f"Create a {language} project using {framework} framework."

# === RESOURCES ===


@mcp.resource("github://repos/{owner}/{repo}")
def github_repo(owner: str, repo: str) -> str:
    """GitHub repository with owner and repo completions."""
    return f"GitHub Repository: {owner}/{repo}\nURL: https://github.com/{owner}/{repo}"

# === COMPLETION HANDLER ===


@mcp.completion()
async def handle_completion(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    """Handle completion requests."""

    # === PROMPT COMPLETIONS ===
    if isinstance(ref, PromptReference):
        if ref.name == "review_code":
            if argument.name == "language":
                matches = [
                    lang for lang in LANGUAGES if lang.startswith(argument.value)]
                return Completion(values=matches, hasMore=False)
            elif argument.name == "focus":
                focuses = ["all", "security", "performance", "style"]
                matches = [f for f in focuses if f.startswith(argument.value)]
                return Completion(values=matches, hasMore=False)

        elif ref.name == "setup_project":
            if argument.name == "language":
                matches = [
                    lang for lang in LANGUAGES if lang.startswith(argument.value)]
                return Completion(values=matches, hasMore=False)
            elif argument.name == "framework":
                # Context-aware completion based on language
                if context and context.arguments:
                    language = context.arguments.get("language", "").lower()
                    if language in FRAMEWORKS:
                        frameworks = FRAMEWORKS[language]
                        matches = [
                            fw for fw in frameworks if fw.startswith(argument.value)]
                        return Completion(values=matches, hasMore=False)

    # === RESOURCE COMPLETIONS ===
    elif isinstance(ref, ResourceTemplateReference):
        if ref.uri == "github://repos/{owner}/{repo}":
            if argument.name == "owner":
                matches = [
                    owner for owner in GITHUB_OWNERS if owner.startswith(argument.value)]
                return Completion(values=matches, hasMore=False)
            elif argument.name == "repo":
                # Context-aware completion based on owner
                if context and context.arguments:
                    owner = context.arguments.get("owner", "").lower()
                    if owner in GITHUB_REPOS:
                        repos = GITHUB_REPOS[owner]
                        matches = [
                            repo for repo in repos if repo.startswith(argument.value)]
                        return Completion(values=matches, hasMore=False)

    return None

@mcp.tool(
    name="edit_document",
    description="Edit a document by replacing a string in the documents content with a new string."
)
def edit_document(
    doc_id: str = Field(description="Id of the document that will be edited"),
    old_str: str = Field(
        description="The text to replace. Must match exactly, including whitespace."),
    new_str: str = Field(
        description="The new text to insert in place of the old text.")
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")

    docs[doc_id] = docs[doc_id].replace(old_str, new_str)
    return f"Successfully updated document {doc_id}"
@mcp.tool()
async def create_story(ctx: Context, topic: str) -> str:
    """
    Creates a short story by asking the client to generate it via sampling.

    Args:
        ctx: The MCP Context, used to communicate with the client.
        topic: The topic for the story.

    Returns:
        The story generated by the client's LLM.
    """
    print(f"-> Server: Tool 'create_story' called with topic: '{topic}'")

    try:
        print(f"-> Server: Sending 'sampling/create' request to client...")

        #    The server delegates the "thinking" to the client.
        result = await ctx.session.create_message(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=f"Write a very short, three-sentence story about: {topic}"),
                )
            ],
            max_tokens=100,
        )

        if result.content.type == "text":
            return result.content.text
        return str(result.content)

    except Exception as e:
        print(f"-> Server: An error occurred during sampling: {e}")
        return f"Error asking client to generate story: {e}"
@mcp.tool()
async def process_item(
    ctx: Context,
    item_id: str,
    should_fail: bool = False,
) -> list[types.TextContent]:
    """
    A simple tool that demonstrates logging by emitting messages
    at different severity levels.
    """
    await ctx.debug(f"Starting processing for item: {item_id}")
    await asyncio.sleep(0.2)
    await ctx.info("Configuration loaded successfully.")
    await asyncio.sleep(0.2)

    if should_fail:
        await ctx.warning(f"Item '{item_id}' has a validation issue. Attempting to proceed...")
        await asyncio.sleep(0.2)
        await ctx.error(f"Failed to process item '{item_id}'. Critical failure.")
        return [types.TextContent(type="text", text=f"Failed to process {item_id}.")]

    await ctx.info(f"Item '{item_id}' processed successfully.")

    return [types.TextContent(type="text", text=f"Successfully processed {item_id}.")]
@mcp.tool()
async def download_file(filename: str, size_mb: int, ctx: Context) -> str:
    """
    Simulate downloading a file with progress tracking.
    
    Args:
        filename: Name of the file to download
        size_mb: Size of the file in MB (determines duration)
        ctx: MCP context for progress reporting
    """
    await ctx.info(f"Starting download of {filename} ({size_mb}MB)")
    
    # Simulate download with progress updates
    total_chunks = size_mb * 10  # 10 chunks per MB
    
    for chunk in range(total_chunks + 1):
        # Calculate progress
        progress = chunk
        percentage = (chunk / total_chunks) * 100
        
        # Report progress
        await ctx.report_progress(
            progress=progress,
            total=total_chunks,
            message=f"Downloading {filename}... {percentage:.1f}%"
        )
        
        # Simulate work (faster for demo)
        await asyncio.sleep(0.1)
    
    await ctx.info(f"Download completed: {filename}")
    return f"Successfully downloaded {filename} ({size_mb}MB)"

@mcp.tool()
async def process_data(records: int, ctx: Context) -> str:
    """
    Simulate processing data records with progress tracking.
    
    Args:
        records: Number of records to process
        ctx: MCP context for progress reporting
    """
    print('Downloading files...')
    await ctx.info(f"Starting to process {records} records")
    
    for i in range(records + 1):
        # Report progress with descriptive messages
        if i == 0:
            message = "Initializing data processor..."
            
        elif i < records // 4:
            message = "Loading and validating records..."
            
        elif i < records // 2:
            message = "Applying transformations..."
            
        elif i < records * 3 // 4:
            message = "Running calculations..."
            
        else:
            message = "Finalizing results..."
            
            
        await ctx.report_progress(
            progress=i,
            total=records,
            message=message
        )
        
        # Simulate processing time
        await asyncio.sleep(2)
    
    await ctx.info(f"Processing completed: {records} records")
    return f"Successfully processed {records} records"
@mcp.tool()
async def analyze_project(ctx: Context) -> TextContent:
    """
    Analyzes project structure using roots provided by the client.

    Returns:
        A summary of the project structure
    """
    print("-> Server: Requesting project roots from client...")
    roots = await ctx.session.list_roots()

    if not roots or not roots.roots:
        return TextContent(text="No project roots found", type="text")

    root = roots.roots[0]  # Get first root for simplicity
    print(f"<- Server: Received root: {root.uri}")

    # Parse the file URI to get the actual path
    path = Path(urlparse(root.uri).path)

    # Do a simple analysis
    py_files = list(path.glob("**/*.py"))

    analysis = f"Found {len(py_files)} Python files in project at {path}"
    print(f"-> Server: Analysis complete: {analysis}")

    return TextContent(text=analysis, type="text")
class OrderPreferences(BaseModel):
    """Schema for collecting user's pizza order preferences."""
    want_toppings: bool = Field(
        description="Would you like to add extra toppings?"
    )
    toppings: str = Field(
        default="mushrooms",
        description="What toppings would you like? (comma-separated)"
    )


@mcp.tool()
async def order_pizza(ctx: Context, size: str) -> str:
    """
    Orders a pizza with optional toppings through user elicitation.

    Args:
        ctx: The MCP Context, used to communicate with the client
        size: Size of the pizza (small, medium, large)

    Returns:
        Order confirmation message
    """
    print(f"-> Server: Tool 'order_pizza' called with size: '{size}'")

    try:
        # Ask user if they want toppings and what kind
        print("-> Server: Sending elicitation request to client...")
        result = await ctx.elicit(
            message=f"Ordering a {size} pizza. Would you like to customize it? Max 3 toppings.",
            schema=OrderPreferences
        )

        # Handle user's response
        if result.action == "accept" and result.data:
            if result.data.want_toppings:
                
                return f"Order confirmed: {size} pizza with {result.data.toppings}"
                
            return f"Order confirmed: {size} plain pizza"
        elif result.action == "decline":
            return "Order declined: No pizza ordered"
        else:  # cancel
            return "Order cancelled"

    except Exception as e:
        print(f"-> Server: An error occurred during elicitation: {e}")
        return f"Error processing pizza order: {e}"
@mcp.resource(
    "docs://documents",
    mime_type="application/json"
)
def list_docs() -> list[str]:
    return list(docs.keys())

@mcp.resource(
    "docs://{doc_id}",
    mime_type="text/plain"
)
def get_doc(doc_id: str) -> str:
    return docs[doc_id]
@mcp.prompt(
    name="format",
    description="Rewrites the contents of the document in Markdown format.",
)
def format_document(
    doc_id: str = Field(description="Id of the document to format"),
) -> list[base.Message]:
    prompt = f"""
    Your goal is to reformat a document to be written with markdown syntax.

    The id of the document you need to reformat is:
    <document_id>
    {doc_id}
    </document_id>

    Add in headers, bullet points, tables, etc as necessary. Feel free to add in extra text, but don't change the meaning of the report.
    Use the 'edit_document' tool to edit the document. After the document has been edited, respond with the final version of the doc. Don't explain your changes.
    """

    return [base.UserMessage(prompt)]
@mcp.prompt(
    name="summarize",
    description="Summarizes the contents of the document."
)
def summarize_document(doc_id: str = Field(description="Id of the document to summarize")) -> list:
    from mcp.types import PromptMessage, TextContent
    prompt_text = f"""
    Your goal is to summarize the contents of the document.
    Document ID: {doc_id}
    Include a concise summary of the document's main points.
    """
    return [PromptMessage(role="user", content=TextContent(type="text", text=prompt_text))]


mcp_app = mcp.streamable_http_app()
