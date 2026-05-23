"""Claude tool-use definitions for the research agent.

Each entry follows the Anthropic tool schema:
  { name, description, input_schema }
"""

from agent.tools.search_tool import SEARCH_PAPERS_TOOL
from agent.tools.fetch_tool import FETCH_PAPER_TOOL
from agent.tools.summarize_tool import SUMMARIZE_PAPER_TOOL
from agent.tools.citations_tool import FORMAT_CITATION_TOOL
from agent.tools.memory_tool import SEARCH_MEMORY_TOOL

TOOL_DEFINITIONS = [
    SEARCH_PAPERS_TOOL,
    FETCH_PAPER_TOOL,
    SUMMARIZE_PAPER_TOOL,
    FORMAT_CITATION_TOOL,
    SEARCH_MEMORY_TOOL,
]

__all__ = ["TOOL_DEFINITIONS"]
