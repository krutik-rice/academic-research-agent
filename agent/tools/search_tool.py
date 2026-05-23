SEARCH_PAPERS_TOOL = {
    "name": "search_papers",
    "description": (
        "Search for academic papers on arXiv and/or Semantic Scholar. "
        "Returns papers with title, authors, abstract, year, URL, and PDF link."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search terms — keywords, topic phrases, or author names.",
            },
            "sources": {
                "type": "array",
                "items": {"type": "string", "enum": ["arxiv", "semantic_scholar"]},
                "description": "Databases to query. Omit to search both.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum papers to return (default 10, max 20).",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}
