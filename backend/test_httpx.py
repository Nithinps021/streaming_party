import asyncio
import httpx

async def main():
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    async with httpx.AsyncClient(transport=transport, follow_redirects=True, timeout=10.0) as client:
        r = await client.get("https://www.google.com/")
        print(r.status_code)

asyncio.run(main())
