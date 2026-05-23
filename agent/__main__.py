"""Interactive CLI — run with: python -m agent"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.core import ResearchAgent  # noqa: E402  (import after load_dotenv)


def main() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY is not set.\n"
            "Add it to a .env file or export it in your shell.",
            file=sys.stderr,
        )
        sys.exit(1)

    agent = ResearchAgent(api_key=api_key)

    print("=" * 60)
    print("  Academic Research Agent")
    print("  Powered by Claude + arXiv + Semantic Scholar")
    print("=" * 60)
    print("Type a research question and press Enter.")
    print("Commands: 'quit' or Ctrl-C to exit.\n")

    while True:
        try:
            query = input("Research> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("\nSearching and analysing...\n")
        try:
            answer = agent.research(query)
            print(answer)
            print()
        except Exception as exc:
            print(f"[error] {exc}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
