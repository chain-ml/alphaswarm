
Firecrawl Docs home pagedark logo
v1

Search or ask...
⌘K
Status
Support
mendableai/firecrawl
27,499

Documentation
SDKs
Learn
API Reference
Playground
Blog
Community
Talk to Us
Changelog
Get Started
Quickstart
Launch Week II (New)
Welcome to V1
Rate Limits
Integrations
Advanced Scraping Guide
Features
Scrape
Crawl
Map
Extract (New)
Integrations
Langchain
Llamaindex
CrewAI
Dify
Flowise
Langflow
Camel AI
RAGaaS
Contributing
Open Source vs Cloud
Running locally
Self-hosting
Get Started
Quickstart
Firecrawl allows you to turn entire websites into LLM-ready markdown

Hero Light
​
Welcome to Firecrawl
Firecrawl is an API service that takes a URL, crawls it, and converts it into clean markdown. We crawl all accessible subpages and give you clean markdown for each. No sitemap required.

​
How to use it?
We provide an easy to use API with our hosted version. You can find the playground and documentation here. You can also self host the backend if you’d like.

Check out the following resources to get started:

 API: Documentation
 SDKs: Python, Node, Go, Rust
 LLM Frameworks: Langchain (python), Langchain (js), Llama Index, Crew.ai, Composio, PraisonAI, Superinterface, Vectorize
 Low-code Frameworks: Dify, Langflow, Flowise AI, Cargo, Pipedream
 Others: Zapier, Pabbly Connect
 Want an SDK or Integration? Let us know by opening an issue.
Self-host: To self-host refer to guide here.

​
API Key
To use the API, you need to sign up on Firecrawl and get an API key.

​
Features
Scrape: scrapes a URL and get its content in LLM-ready format (markdown, structured data via LLM Extract, screenshot, html)
Crawl: scrapes all the URLs of a web page and return content in LLM-ready format
Map: input a website and get all the website urls - extremely fast
​
Powerful Capabilities
LLM-ready formats: markdown, structured data, screenshot, HTML, links, metadata
The hard stuff: proxies, anti-bot mechanisms, dynamic content (js-rendered), output parsing, orchestration
Customizability: exclude tags, crawl behind auth walls with custom headers, max crawl depth, etc…
Media parsing: pdfs, docx, images.
Reliability first: designed to get the data you need - no matter how hard it is.
Actions: click, scroll, input, wait and more before extracting data
You can find all of Firecrawl’s capabilities and how to use them in our documentation

​
Crawling
Used to crawl a URL and all accessible subpages. This submits a crawl job and returns a job ID to check the status of the crawl.

​
Installation

Python

Node

Go

Rust

pip install firecrawl-py
​
Usage

Python

Node

Go

Rust

cURL

from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="fc-YOUR_API_KEY")

# Crawl a website:
crawl_status = app.crawl_url(
  'https://firecrawl.dev', 
  params={
    'limit': 100, 
    'scrapeOptions': {'formats': ['markdown', 'html']}
  },
  poll_interval=30
)
print(crawl_status)
If you’re using cURL or async crawl functions on SDKs, this will return an ID where you can use to check the status of the crawl.


{
  "success": true,
  "id": "123-456-789",
  "url": "https://api.firecrawl.dev/v1/crawl/123-456-789"
}
​
Check Crawl Job
Used to check the status of a crawl job and get its result.


Python

Node

Go

Rust

cURL

crawl_status = app.check_crawl_status("<crawl_id>")
print(crawl_status)
​
Response
The response will be different depending on the status of the crawl. For not completed or large responses exceeding 10MB, a next URL parameter is provided. You must request this URL to retrieve the next 10MB of data. If the next parameter is absent, it indicates the end of the crawl data.


Scraping

Completed

{
  "status": "scraping",
  "total": 36,
  "completed": 10,
  "creditsUsed": 10,
  "expiresAt": "2024-00-00T00:00:00.000Z",
  "next": "https://api.firecrawl.dev/v1/crawl/123-456-789?skip=10",
  "data": [
    {
      "markdown": "[Firecrawl Docs home page![light logo](https://mintlify.s3-us-west-1.amazonaws.com/firecrawl/logo/light.svg)!...",
      "html": "<!DOCTYPE html><html lang=\"en\" class=\"js-focus-visible lg:[--scroll-mt:9.5rem]\" data-js-focus-visible=\"\">...",
      "metadata": {
        "title": "Build a 'Chat with website' using Groq Llama 3 | Firecrawl",
        "language": "en",
        "sourceURL": "https://docs.firecrawl.dev/learn/rag-llama3",
        "description": "Learn how to use Firecrawl, Groq Llama 3, and Langchain to build a 'Chat with your website' bot.",
        "ogLocaleAlternate": [],
        "statusCode": 200
      }
    },
    ...
  ]
}
​
Scraping
To scrape a single URL, use the scrape_url method. It takes the URL as a parameter and returns the scraped data as a dictionary.


Python

Node

Go

Rust

cURL

from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="fc-YOUR_API_KEY")

# Scrape a website:
scrape_result = app.scrape_url('firecrawl.dev', params={'formats': ['markdown', 'html']})
print(scrape_result)
​
Response
SDKs will return the data object directly. cURL will return the payload exactly as shown below.


{
  "success": true,
  "data" : {
    "markdown": "Launch Week I is here! [See our Day 2 Release 🚀](https://www.firecrawl.dev/blog/launch-week-i-day-2-doubled-rate-limits)[💥 Get 2 months free...",
    "html": "<!DOCTYPE html><html lang=\"en\" class=\"light\" style=\"color-scheme: light;\"><body class=\"__variable_36bd41 __variable_d7dc5d font-inter ...",
    "metadata": {
      "title": "Home - Firecrawl",
      "description": "Firecrawl crawls and converts any website into clean markdown.",
      "language": "en",
      "keywords": "Firecrawl,Markdown,Data,Mendable,Langchain",
      "robots": "follow, index",
      "ogTitle": "Firecrawl",
      "ogDescription": "Turn any website into LLM-ready data.",
      "ogUrl": "https://www.firecrawl.dev/",
      "ogImage": "https://www.firecrawl.dev/og.png?123",
      "ogLocaleAlternate": [],
      "ogSiteName": "Firecrawl",
      "sourceURL": "https://firecrawl.dev",
      "statusCode": 200
    }
  }
}
​
Extraction
With LLM extraction, you can easily extract structured data from any URL. We support pydantic schemas to make it easier for you too. Here is how you to use it:

v1 is only supported on node, python and cURL at this time.


Python

Node

cURL

from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field

# Initialize the FirecrawlApp with your API key
app = FirecrawlApp(api_key='your_api_key')

class ExtractSchema(BaseModel):
    company_mission: str
    supports_sso: bool
    is_open_source: bool
    is_in_yc: bool

data = app.scrape_url('https://docs.firecrawl.dev/', {
    'formats': ['json'],
    'jsonOptions': {
        'schema': ExtractSchema.model_json_schema(),
    }
})
print(data["json"])
Output:

JSON

{
    "success": true,
    "data": {
      "json": {
        "company_mission": "Train a secure AI on your technical resources that answers customer and employee questions so your team doesn't have to",
        "supports_sso": true,
        "is_open_source": false,
        "is_in_yc": true
      },
      "metadata": {
        "title": "Mendable",
        "description": "Mendable allows you to easily build AI chat applications. Ingest, customize, then deploy with one line of code anywhere you want. Brought to you by SideGuide",
        "robots": "follow, index",
        "ogTitle": "Mendable",
        "ogDescription": "Mendable allows you to easily build AI chat applications. Ingest, customize, then deploy with one line of code anywhere you want. Brought to you by SideGuide",
        "ogUrl": "https://docs.firecrawl.dev/",
        "ogImage": "https://docs.firecrawl.dev/mendable_new_og1.png",
        "ogLocaleAlternate": [],
        "ogSiteName": "Mendable",
        "sourceURL": "https://docs.firecrawl.dev/"
      },
    }
}
​
Extracting without schema (New)
You can now extract without a schema by just passing a prompt to the endpoint. The llm chooses the structure of the data.


cURL

curl -X POST https://api.firecrawl.dev/v1/scrape \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer YOUR_API_KEY' \
    -d '{
      "url": "https://docs.firecrawl.dev/",
      "formats": ["json"],
      "jsonOptions": {
        "prompt": "Extract the company mission from the page."
      }
    }'
Output:

JSON

{
    "success": true,
    "data": {
      "json": {
        "company_mission": "Train a secure AI on your technical resources that answers customer and employee questions so your team doesn't have to",
      },
      "metadata": {
        "title": "Mendable",
        "description": "Mendable allows you to easily build AI chat applications. Ingest, customize, then deploy with one line of code anywhere you want. Brought to you by SideGuide",
        "robots": "follow, index",
        "ogTitle": "Mendable",
        "ogDescription": "Mendable allows you to easily build AI chat applications. Ingest, customize, then deploy with one line of code anywhere you want. Brought to you by SideGuide",
        "ogUrl": "https://docs.firecrawl.dev/",
        "ogImage": "https://docs.firecrawl.dev/mendable_new_og1.png",
        "ogLocaleAlternate": [],
        "ogSiteName": "Mendable",
        "sourceURL": "https://docs.firecrawl.dev/"
      },
    }
}
​
Extraction (v0)

Python

JavaScript

Go

Rust

cURL


app = FirecrawlApp(version="v0")

class ArticleSchema(BaseModel):
    title: str
    points: int 
    by: str
    commentsURL: str

class TopArticlesSchema(BaseModel):
top: List[ArticleSchema] = Field(..., max_items=5, description="Top 5 stories")

data = app.scrape_url('https://news.ycombinator.com', {
'extractorOptions': {
'extractionSchema': TopArticlesSchema.model_json_schema(),
'mode': 'llm-extraction'
},
'pageOptions':{
'onlyMainContent': True
}
})
print(data["llm_extraction"])
​
Interacting with the page with Actions
Firecrawl allows you to perform various actions on a web page before scraping its content. This is particularly useful for interacting with dynamic content, navigating through pages, or accessing content that requires user interaction.

Here is an example of how to use actions to navigate to google.com, search for Firecrawl, click on the first result, and take a screenshot.

It is important to almost always use the wait action before/after executing other actions to give enough time for the page to load.

​
Example

Python

Node

cURL

from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="fc-YOUR_API_KEY")

# Scrape a website:
scrape_result = app.scrape_url('firecrawl.dev', 
    params={
        'formats': ['markdown', 'html'], 
        'actions': [
            {"type": "wait", "milliseconds": 2000},
            {"type": "click", "selector": "textarea[title=\"Search\"]"},
            {"type": "wait", "milliseconds": 2000},
            {"type": "write", "text": "firecrawl"},
            {"type": "wait", "milliseconds": 2000},
            {"type": "press", "key": "ENTER"},
            {"type": "wait", "milliseconds": 3000},
            {"type": "click", "selector": "h3"},
            {"type": "wait", "milliseconds": 3000},
            {"type": "scrape"},
            {"type": "screenshot"}
        ]
    }
)
print(scrape_result)
​
Output

JSON

{
  "success": true,
  "data": {
    "markdown": "Our first Launch Week is over! [See the recap 🚀](blog/firecrawl-launch-week-1-recap)...",
    "actions": {
      "screenshots": [
        "https://alttmdsdujxrfnakrkyi.supabase.co/storage/v1/object/public/media/screenshot-75ef2d87-31e0-4349-a478-fb432a29e241.png"
      ],
      "scrapes": [
        {
          "url": "https://www.firecrawl.dev/",
          "html": "<html><body><h1>Firecrawl</h1></body></html>"
        }
      ]
    },
    "metadata": {
      "title": "Home - Firecrawl",
      "description": "Firecrawl crawls and converts any website into clean markdown.",
      "language": "en",
      "keywords": "Firecrawl,Markdown,Data,Mendable,Langchain",
      "robots": "follow, index",
      "ogTitle": "Firecrawl",
      "ogDescription": "Turn any website into LLM-ready data.",
      "ogUrl": "https://www.firecrawl.dev/",
      "ogImage": "https://www.firecrawl.dev/og.png?123",
      "ogLocaleAlternate": [],
      "ogSiteName": "Firecrawl",
      "sourceURL": "http://google.com",
      "statusCode": 200
    }
  }
}
​
Open Source vs Cloud
Firecrawl is open source available under the AGPL-3.0 license.

To deliver the best possible product, we offer a hosted version of Firecrawl alongside our open-source offering. The cloud solution allows us to continuously innovate and maintain a high-quality, sustainable service for all users.

Firecrawl Cloud is available at firecrawl.dev and offers a range of features that are not available in the open source version:

Firecrawl Cloud vs Open Source

​
Contributing
We love contributions! Please read our contributing guide before submitting a pull request.

Suggest edits
Raise issue
Launch Week II (New)
x
github
linkedin
Powered by Mintlify
On this page
Welcome to Firecrawl
How to use it?
API Key
Features
Powerful Capabilities
Crawling
Installation
Usage
Check Crawl Job
Response
Scraping
Response
Extraction
Extracting without schema (New)
Extraction (v0)
Interacting with the page with Actions
Example
Output
Open Source vs Cloud
Contributing
