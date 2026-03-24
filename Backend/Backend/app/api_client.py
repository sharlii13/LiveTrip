import asyncio
import httpx

def get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, read=10.0),
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    )

async def with_retries(request_coro, retries: int = 2):
    last_exc = None
    for _ in range(retries + 1):
        try:
            return await request_coro
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            last_exc = e
            await asyncio.sleep(0.5)
    raise last_exc
