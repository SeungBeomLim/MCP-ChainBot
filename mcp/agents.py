import re, json

from mcp.message_schema import A2AMessage, ChatMessage, ChatCompletion
from urllib.parse import quote
from aiohttp import ClientResponseError

class BaseAgent:
    def __init__(self, manager):
        self.manager = manager
        self.agent_id = self.__class__.__name__

    async def handle(self, msg: A2AMessage):
        raise NotImplementedError


class UserAgent(BaseAgent):
    async def handle(self, msg: A2AMessage):
        if msg.type == "ExecuteTool":
            return await self.manager.send_to_agent(msg)

        elif msg.type == "ToolResult":
            # 1) 툴 결과 포맷팅
            raw = msg.payload["result"]
            if isinstance(raw, dict):
                body = json.dumps(raw, ensure_ascii=False, indent=2)
            else:
                body = str(raw)
            tool_text = f"🔧 tool result:\n{body}"

            # 2) LLM 히스토리에 assistant 메시지로 쌓기
            hist = self.manager.histories.setdefault(msg.from_agent, [])
            hist.append(ChatMessage(role="system", content=tool_text))

            # 3) LLM 호출
            llm_resp = self.manager.client.chat(hist)
            if isinstance(llm_resp, ChatCompletion):
                # 히스토리에 LLM 답변도 추가
                hist.extend(llm_resp.messages)
                # Host/Streamlit에는 LLM 메시지만 전달
                return self.manager.wrap_chat(
                    # 1) tool result as an assistant message
                    [ {"role": "assistant", "content": tool_text} ]
                    # 2) then all the LLM-generated assistant messages
                    + [ {"role": m.role, "content": m.content} for m in llm_resp.messages ]
                )


class WeatherAgent(BaseAgent):
    async def handle(self, msg: A2AMessage):
        city = msg.payload["city"]
        # 직접 호출 (Manager._invoke_tool 재사용)
        data = await self.manager._invoke_tool("weather", {"city": city})
        return A2AMessage(
            type="ToolResult",
            from_agent=self.agent_id,
            to_agent=msg.from_agent,
            payload={"result": data}
        )


class WikiAgent(BaseAgent):
    async def handle(self, msg: A2AMessage):
        raw = msg.payload["query"]
        words = re.sub(r'[_\s]+', ' ', raw).strip().split()
        title = "_".join(w.capitalize() for w in words)
        # URL-encode (혹시 스페셜문자 있을 때 대비)
        query = quote(title, safe='')

        # 2) 호출 및 에러 핸들링
        try:
            data = await self.manager._invoke_tool("wiki", {"query": query})
            text = f"**{data.get('title', title)}**\n\n{data.get('extract','No summary.')}\n\n{data.get('url','')}"
        except ClientResponseError as e:
            # HTTP 404 등 에러 나면
            text = f"죄송해요, '{raw}'에 대한 Wikipedia 페이지를 찾을 수 없어요."
        except Exception as e:
            text = "Internal error occurred while fetching Wikipedia summary."

        # 3) ToolResult 로 보내기
        return A2AMessage(
            type="ToolResult",
            from_agent=self.agent_id,
            to_agent=msg.from_agent,
            payload={"result": text}
        )


class ExchangeAgent(BaseAgent):
    async def handle(self, msg: A2AMessage):
        base, symbol = msg.payload["base"], msg.payload["symbol"]
        data = await self.manager._invoke_tool("exchange", {"base": base, "symbol": symbol, "amount": 1})
        return A2AMessage(
            type="ToolResult",
            from_agent=self.agent_id,
            to_agent=msg.from_agent,
            payload={"result": data}
        )
