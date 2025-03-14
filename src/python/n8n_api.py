from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Optional, Union
from n8n_integration import Crawl4AIAgent
import asyncio
import uvicorn

app = FastAPI(
    title="Crawl4AI n8n API",
    description="n8n-specific endpoints for Crawl4AI",
    version="1.0.0"
)

# Initialize agent
agent = Crawl4AIAgent()

class CrawlRequest(BaseModel):
    urls: Union[str, List[str]]
    metadata: Optional[Dict] = None

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

@app.post("/n8n/crawl")
async def crawl_urls(request: CrawlRequest):
    """Crawl one or more URLs and store in Supabase."""
    try:
        urls = [request.urls] if isinstance(request.urls, str) else request.urls
        results = await agent.process_urls(urls, request.metadata)
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/n8n/search")
async def search_content(request: SearchRequest):
    """Search for similar content using vector similarity."""
    try:
        results = await agent.search_similar(request.query, request.limit)
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/n8n/health")
async def health_check():
    """Check if the service is healthy."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("n8n_api:app", host="0.0.0.0", port=8000, reload=True) 