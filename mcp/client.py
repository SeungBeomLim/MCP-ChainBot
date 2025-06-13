# mcp/client.py

import json
from typing import List, Union

from pydantic import ValidationError
from mcp.message_schema import (
    ChatMessage,
    ChatCompletion,
    ToolInvocation,
    ToolResponse,
)
from llm.groq_client import call_llm
from utils.logger import logger

class Client:
    """
    LLM 호출 및 ToolInvocation 결과 처리용 클래스
    """

    def __init__(self, system_prompt: str = "You are a helpful assistant."):
        self.system_prompt = system_prompt

    def _build_prompt(self, history: List[ChatMessage]) -> str:
        # POC: 간단히 메시지 배열을 하나의 prompt 문자열로 합칩니다.
        parts = [f"{msg.role.upper()}: {msg.content}" for msg in history]
        return "\n".join(["SYSTEM: " + self.system_prompt] + parts)

    def chat(self, history: List[ChatMessage]) -> Union[ChatCompletion, ToolInvocation]:
        """
        1) history → prompt
        2) Groq API 호출
        3) JSON 응답 → ChatCompletion / ToolInvocation 처리
        """
        prompt = self._build_prompt(history)
        logger.info(f"[Client] Sending prompt to LLM:\n{prompt}")

        # 2) LLM 호출 (blocking)
        raw = call_llm(prompt)
        logger.debug(f"[Client] Raw LLM response: {raw}")

        # 3) LLM이 직접 반환한 JSON(tool call 지시 등)을 파싱
        try:
            payload = json.loads(raw)
            # tool 호출 지시가 명확하면 ToolInvocation 으로 변환
            if payload.get("type") == "tool_invocation":
                tool_inv = ToolInvocation.parse_obj(payload)
                return tool_inv
        except json.JSONDecodeError:
            # JSON이 아니거나 빈 응답 → 일반 채팅 응답으로 간주
            pass
        except ValidationError as e:
            # JSON은 맞지만 schema 불일치 → 일반 채팅 응답
            logger.debug(f"[Client] Payload not matching tool schema: {e}")

        # 4) 일반 채팅 응답
        chat_msg = ChatMessage(role="assistant", content=raw)
        return ChatCompletion(type="chat_completion", messages=[chat_msg])
