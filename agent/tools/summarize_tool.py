SUMMARIZE_PAPER_TOOL = {
    "name": "summarize_paper",
    "description": (
        "Generate a structured summary for a paper that has already been searched or fetched. "
        "Returns: summary, key findings, methodology, contributions, limitations, keywords. "
        "Cached after first call — subsequent calls for the same paper ID are free."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Paper ID (must exist in session memory from a prior search).",
            },
        },
        "required": ["paper_id"],
    },
}
