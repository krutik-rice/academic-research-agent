SEARCH_MEMORY_TOOL = {
    "name": "search_memory",
    "description": (
        "Search papers already retrieved in this session (or from previous sessions). "
        "Always call this before search_papers to avoid unnecessary external API calls."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords to match against saved paper titles and abstracts.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
