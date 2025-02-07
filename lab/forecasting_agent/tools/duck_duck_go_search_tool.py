from typing import Any

from smolagents import Tool


class DuckDuckGoSearchTool(Tool):
    name = "web_search"
    description = """Performs a duckduckgo web search based on your query (think a Google search) then returns the top search results."""
    inputs = {"query": {"type": "string", "description": "The search query to perform."}}
    output_type = "string"

    def __init__(self, *args: Any, max_results: int = 10, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.max_results = max_results
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            raise ImportError(
                "You must install package `duckduckgo_search` to run this tool: for instance run `pip install duckduckgo-search`."
            )
        self.ddgs = DDGS()

    def forward(self, query: str) -> str:
        results = self.ddgs.text(query, max_results=self.max_results, timelimit="d")  # hardcode for one day
        postprocessed_results = [f"[{result['title']}]({result['href']})\n{result['body']}" for result in results]
        return "## Search Results\n\n" + "\n\n".join(postprocessed_results)
