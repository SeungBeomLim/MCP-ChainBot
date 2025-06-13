# mcp/host.py

import asyncio
import json
import websockets
from pydantic import parse_obj_as, ValidationError

from mcp.manager import Manager
from mcp.message_schema import MCPMessage
from utils.logger import logger

manager = Manager()

async def handler(websocket, path=None):
    logger.info(f"[Host] Client connected")
    try:
        async for raw in websocket:
            logger.debug(f"[Host] Received raw: {raw}")

            # 1) JSON → Pydantic Union 파싱
            try:
                payload = json.loads(raw)
                msg = parse_obj_as(MCPMessage, payload)
            except ValidationError as e:
                logger.error(f"[Host] Invalid MCP message: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid message format",
                    "details": e.errors()
                }))
                continue
            except Exception as e:
                logger.exception(f"[Host] Unexpected parse error: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Parse failure",
                    "details": str(e)
                }))
                continue

            # 2) Manager에게 처리 위임
            try:
                response_msg = await manager.handle_message(msg)
            except Exception as e:
                logger.exception("[Host] Error in manager.handle_message")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Internal server error",
                    "details": str(e)
                }))
                continue

            # 3) 정상 응답 전송
            resp_json = response_msg.json()
            logger.debug(f"[Host] Sending response: {resp_json}")
            await websocket.send(resp_json)

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"[Host] Client disconnected gracefully")
    except Exception as e:
        logger.exception(f"[Host] Unexpected error in handler: {e}")

async def run_host(host: str = "localhost", port: int = 8080):
    logger.info(f"[Host] Starting MCP Host at ws://{host}:{port}")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(run_host())
