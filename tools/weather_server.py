from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise RuntimeError("OPENWEATHER_API_KEY not set in .env")

app = FastAPI()
logger = logging.getLogger("weather_server")
logging.basicConfig(level=logging.INFO)

class WeatherRequest(BaseModel):
    city: str  # 사용자로부터 도시명을 city로 받습니다.

class WeatherResponse(BaseModel):
    city: str
    temp: float
    description: str
    humidity: float

@app.post("/tools/weather/invoke", response_model=WeatherResponse)
async def weather_invoke(req: WeatherRequest):
    city = req.city
    api_uri = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}"
        f"&units=metric"
        f"&appid={OPENWEATHER_API_KEY}"
    )
    logger.info(f"[weather_invoke] Fetching weather via URL: {api_uri}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(api_uri)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            detail = "Weather API unauthorized (invalid key)"
        else:
            detail = f"HTTP error: {e.response.status_code}"
        logger.error(f"[weather_invoke] {detail}")
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        logger.exception("[weather_invoke] Failed to fetch weather data")
        raise HTTPException(status_code=502, detail=str(e))

    try:
        return WeatherResponse(
            city=data.get("name", city),
            temp=data["main"]["temp"],
            description=data["weather"][0]["description"],
            humidity=data["main"]["humidity"]
        )
    except (KeyError, IndexError) as e:
        logger.error(f"[weather_invoke] Parsing error: {e}")
        raise HTTPException(status_code=502, detail="Unexpected response format")
