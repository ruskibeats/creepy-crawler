import os
from supabase import create_client, Client
from typing import List, Dict, Optional
import openai
from datetime import datetime
import tiktoken
import json
from crawler_script import AsyncWebCrawler
from bs4 import BeautifulSoup
import asyncio

class Crawl4AIAgent:
    def __init__(self):
        # Initialize Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Initialize OpenAI
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_model = "text-embedding-3-small"
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Initialize crawler
        self.crawler = AsyncWebCrawler()

    def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text."""
        response = openai.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def chunk_text(self, text: str, chunk_size: int = 512) -> List[str]:
        """Split text into chunks of roughly equal token length."""
        tokens = self.encoding.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), chunk_size):
            chunk = tokens[i:i + chunk_size]
            chunks.append(self.encoding.decode(chunk))
            
        return chunks

    def extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text

    async def process_url(self, url: str, metadata: Optional[Dict] = None) -> Dict:
        """Process a single URL and store results in Supabase."""
        # Crawl the URL
        await self.crawler.crawl(url)
        
        # Get the HTML content
        html_path = None
        for row in self.crawler.cursor.execute("SELECT html_path FROM pages WHERE url = ?", (url,)):
            html_path = row[0]
            
        if not html_path:
            return {"status": "error", "message": "Failed to crawl URL"}
            
        # Read HTML content
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
            
        # Extract text
        text = self.extract_text_from_html(html)
        
        # Chunk text
        chunks = self.chunk_text(text)
        
        # Get embeddings and store in Supabase
        for i, chunk in enumerate(chunks):
            embedding = self.get_embedding(chunk)
            
            # Store in Supabase
            self.supabase.table("page_chunks").insert({
                "url": url,
                "chunk_index": i,
                "content": chunk,
                "embedding": embedding,
                "metadata": {
                    **(metadata or {}),
                    "crawl_date": datetime.now().isoformat(),
                    "chunk_count": len(chunks)
                }
            }).execute()
            
        return {
            "status": "success",
            "url": url,
            "chunks_processed": len(chunks),
            "metadata": metadata
        }

    async def search_similar(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar content using vector similarity."""
        query_embedding = self.get_embedding(query)
        
        # Search using Supabase's vector similarity
        response = self.supabase.rpc(
            'match_page_chunks',
            {
                'query_embedding': query_embedding,
                'match_threshold': 0.5,
                'match_count': limit
            }
        ).execute()
        
        return response.data

    async def process_urls(self, urls: List[str], metadata: Optional[Dict] = None) -> List[Dict]:
        """Process multiple URLs in parallel."""
        tasks = [self.process_url(url, metadata) for url in urls]
        return await asyncio.gather(*tasks)

    def close(self):
        """Clean up resources."""
        self.crawler.close() 