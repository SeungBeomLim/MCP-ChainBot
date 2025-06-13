# app/main_app.py

import os
import sys
import streamlit as st
import asyncio
import websockets
import json

# 프로젝트 루트를 import 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import WS_URI

st.set_page_config(page_title="MCP-ChainBot", layout="wide")

# 세션 상태 초기화
if "history" not in st.session_state:
    st.session_state.history = []
if "registered" not in st.session_state:
    st.session_state.registered = False

async def send_and_receive(user_text: str) -> dict:
    uri = WS_URI
    try:
        async with websockets.connect(uri) as ws:
            # 등록(Ack) 처리
            if not st.session_state.registered:
                reg_msg = {"type": "register_agent", "agent_id": "default"}
                await ws.send(json.dumps(reg_msg))
                # Ack 소비
                try:
                    await asyncio.wait_for(ws.recv(), timeout=5)
                except Exception:
                    pass
                st.session_state.registered = True

            # 사용자 메시지 전송
            chat_msg = {"type": "chat_completion", "messages": [{"role": "user", "content": user_text}]}
            await ws.send(json.dumps(chat_msg))

            # 응답 수신
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=10)
            except asyncio.TimeoutError:
                return {"type": "error", "message": "Response timed out"}
            except websockets.exceptions.ConnectionClosedOK:
                return {"type": "error", "message": "Connection closed before response"}
            except websockets.exceptions.ConnectionClosedError as e:
                return {"type": "error", "message": f"Connection error: {e}"}

            return json.loads(raw)
    except Exception as e:
        return {"type": "error", "message": f"Failed to connect to host: {e}"}

# ─── HEADER & INPUT ──────────────────────────────────────────
st.header("🤖 MCP-ChainBot")

# 1) 사용자 입력창 (단 한 번만 선언, 고유 key 지정)
user_input = st.chat_input("Your message...", key="chat_input")

# 2) 입력이 들어오면 즉시 처리
if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})
    response = asyncio.run(send_and_receive(user_input))

    if response.get("type") == "error":
        st.session_state.history.append({"role": "assistant", "content": f"❌ {response['message']}"})
    elif response.get("type") == "chat_completion":
        for msg in response["messages"]:
            st.session_state.history.append({"role": msg["role"], "content": msg["content"]})
    else:
        st.session_state.history.append({"role": "assistant", "content": str(response)})

# ─── CHAT HISTORY RENDERING ──────────────────────────────────
for turn in st.session_state.history:
    role = turn["role"]
    content = turn["content"].strip()

    # 1) Tool result → expander only, wrapped in assistant bubble
    if "🔧 tool result:" in content:
        body = content.split("🔧 tool result:",1)[1].strip()
        # wrap it in an assistant chat_message so the expander arrow shows up on the right
        with st.chat_message("assistant"):
            with st.expander("📚 출처 문서 보기", expanded=False):
                st.markdown(body)
        continue

    # 2) Normal chat bubbles for user / assistant
    if role in ("user", "assistant"):
        with st.chat_message(role):
            st.markdown(content)
        continue
