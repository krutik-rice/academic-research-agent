FETCH_PAPER_TOOL = {
    "name": "fetch_paper",
    "description": (
        "Fetch and extract the full text of a paper given its ID. "
        "For arXiv papers this tries the HTML version first, then falls back to PDF. "
        "Use this when you need more detail than the abstract provides."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Paper ID as returned by search_papers (e.g. 'arxiv:2310.01234').",
            },
            "pdf_url": {
                "type": "string",
                "description": "Direct PDF URL (optional — used as fallback).",
            },
            "title": {
                "type": "string",
                "description": "Paper title (optional — improves display).",
            },
        },
        "required": ["paper_id"],
    },
}
