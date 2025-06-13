# llm/llm_chain.py

from typing import List
from mcp.message_schema import ChatMessage, ChatCompletion, ToolInvocation
from llm.groq_client import call_llm
import json

class LLMChain:
    """
    대화 히스토리를 받아 LLM 호출 → 도구 호출 지시 처리 → 재호출 흐름 담당
    """

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def _format_history(self, history: List[ChatMessage]) -> str:
        parts = [f"{m.role.upper()}: {m.content}" for m in history]
        return "\n".join(["SYSTEM: " + self.system_prompt] + parts)

    def run(self, history: List[ChatMessage]):
        prompt = self._format_history(history)
        raw = call_llm(prompt)
        # LLM이 JSON tool 지시를 내렸으면 파싱
        try:
            obj = json.loads(raw)
            if obj.get("type") == "tool_invocation":
                return ToolInvocation.parse_obj(obj)
        except Exception:
            pass
        # 아니면 일반 대화 응답
        msg = ChatMessage(role="assistant", content=raw)
        return ChatCompletion(type="chat_completion", messages=[msg])
