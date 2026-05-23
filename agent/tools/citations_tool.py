FORMAT_CITATION_TOOL = {
    "name": "format_citation",
    "description": "Format a paper as a citation in APA, MLA, or BibTeX style.",
    "input_schema": {
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Paper ID (must exist in session memory).",
            },
            "style": {
                "type": "string",
                "enum": ["apa", "mla", "bibtex"],
                "description": "Citation format. Defaults to 'apa'.",
                "default": "apa",
            },
        },
        "required": ["paper_id"],
    },
}
