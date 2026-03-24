# app/http.py
import httpx
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global HTTP client instance
_client: Optional[httpx.AsyncClient] = None

def get_client() -> httpx.AsyncClient:
    """Get or create HTTP client instance"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            headers={
                "User-Agent": "TravelApp/1.0.0"
            }
        )
    return _client

async def with_retries(
    request_func,
    max_retries: int = 3,
    backoff_factor: float = 1.0
):
    """
    Execute HTTP request with retry logic
    
    Args:
        request_func: The HTTP request function to execute
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor for exponential backoff
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            response = await request_func
            
            # If successful, return response
            if response.status_code < 500:
                return response
                
            # Server error - retry
            if attempt < max_retries:
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            
            return response
            
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Request failed: {e}, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            break
    
    # All retries failed
    if last_exception:
        raise last_exception
    
    return response

async def cleanup_client():
    """Cleanup HTTP client on app shutdown"""
    global _client
    if _client:
        await _client.aclose()
        _client = None
