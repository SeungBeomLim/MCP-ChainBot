# exchange_server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import traceback
import logging
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
logger = logging.getLogger("exchange")
logging.basicConfig(level=logging.INFO)

class ConvertRequest(BaseModel):
    base: str          # "from" 통화 코드
    symbol: str        # "to" 통화 코드
    amount: float = 1  # 변환할 액수 (기본 1)

@app.post("/tools/exchange/invoke")
async def exchange_convert(req: ConvertRequest):
    try:
        api_key = os.getenv("EXCHANGE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Missing EXCHANGE_API_KEY env var")

        params = {
            "access_key": api_key,
            "from": req.base.upper(),
            "to": req.symbol.upper(),
            "amount": req.amount,
            "format": 1
        }
        url = "http://api.exchangerate.host/convert"
        logger.info(f"[exchange_convert] GET {url} params={params}")

        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        logger.info(f"[exchange_convert] External API returned: {data}")

        # 에러 페이로드 체크
        if not data.get("success", True):
            info = data.get("error", {}).get("info", "Unknown error")
            raise HTTPException(status_code=502, detail=info)

        # 반환값 정리
        return {
            "query": data.get("query"),    # { from, to, amount }
            "result": data.get("result")   # 변환된 환율 값
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"[exchange_convert] HTTP error: {e.response.text}")
        raise HTTPException(status_code=502, detail=e.response.text)

    except HTTPException:
        raise

    except Exception as e:
        logger.error("[exchange_convert] Unexpected error:", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
