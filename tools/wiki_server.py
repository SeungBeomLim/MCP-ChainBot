from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

class WikiRequest(BaseModel):
    query: str

@app.post("/tools/wiki/invoke")
async def wiki_invoke(req: WikiRequest):
    query = req.query.strip()
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=404, detail="Wikipedia page not found")
        except Exception:
            raise HTTPException(status_code=500, detail="Internal Server Error")

    return {
        "title": data.get("title", query),
        "extract": data.get("extract", "No summary available."),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
    }