# app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

# Streamlit 앱 설정
HOST = os.getenv("MCP_HOST", "localhost")
PORT = int(os.getenv("MCP_PORT", 8080))
WS_URI = f"ws://{HOST}:{PORT}"

# 툴 서버 설정 (예시)
TOOL_BASE_URL = os.getenv("TOOL_BASE_URL", "http://localhost:8000/tools")
