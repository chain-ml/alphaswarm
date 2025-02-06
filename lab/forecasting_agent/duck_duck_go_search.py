from smolagents import Tool


class DuckDuckGoSearchTool(Tool):
    name = "web_search"
    description = """Performs a duckduckgo web search based on your query (think a Google search) then returns the top search results.
    
    Output format:
    Return a string with search results in the following structure:

    [<title>](<url>)
    <snippet of article text>

    [<title>](<url>)
    <snippet of article text>
    
    ... (up to max_results entries)
    
    where:
    - <title>: The title of the search result
    - <url>: The URL link to the full article
    - <snippet>: A brief excerpt from the article content
    """
    inputs = {"query": {"type": "string", "description": "The search query to perform."}}
    output_type = "string"

    def __init__(self, *args, max_results=10, **kwargs):
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
