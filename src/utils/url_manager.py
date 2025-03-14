import aiohttp
import json
from bs4 import BeautifulSoup
import redis
from typing import List, Optional

class URLManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.processed_set = "processed_urls"

    async def parse_sitemap(self, sitemap_url: str = "https://n8n.io/sitemap-workflows.xml") -> List[str]:
        """Parse sitemap.xml and extract workflow URLs from 'loc' parameter"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'xml')
                        urls = [loc.text for loc in soup.find_all('loc')]
                        return urls
                    else:
                        raise Exception(f"Failed to fetch sitemap: {response.status}")
        except Exception as e:
            raise Exception(f"Error parsing sitemap: {str(e)}")

    async def is_processed(self, url: str) -> bool:
        """Check if URL has been processed"""
        return await self.redis.sismember(self.processed_set, url)

    async def mark_processed(self, url: str) -> None:
        """Mark URL as processed"""
        await self.redis.sadd(self.processed_set, url)

    async def get_next_batch(self, batch_size: int = 50) -> List[str]:
        """Get next batch of URLs to process"""
        # Implemented in BatchProcessor
        pass
        """Get next batch of URLs to process"""
        # Implemented in BatchProcessor
        pass
