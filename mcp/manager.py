# mcp/manager.py

import json
import os
import re
from typing import Dict, List

import aiohttp
from mcp.message_schema import (
    MCPMessage,
    RegisterAgent,
    ChatCompletion,
    ChatMessage,
    ToolInvocation,
    ToolResponse,
    A2AMessage,
)

from mcp.client import Client
from mcp.agents import UserAgent, WeatherAgent, WikiAgent, ExchangeAgent
from utils.logger import logger


def clean_query(text: str) -> str:
        # 1. 소문자로 변환 후 관사 제거
        text = text.lower()
        text = re.sub(r'^(the|a|an)\s+', '', text)

        # 2. 남은 특수문자 제거 및 공백 → `_` 변환
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip().replace(' ', '_')


class Manager:
    def __init__(self, server_list_path: str = None):
        # Load tool endpoints and spawn CLI servers
        server_list_path = server_list_path or os.path.join(
            os.path.dirname(__file__), "servers.json"
        )
        with open(server_list_path, "r", encoding="utf-8") as f:
            servers = json.load(f)

        # Build tool_endpoints map
        self.tool_endpoints: Dict[str, str] = {}
        for s in servers:
            proto = "https" if s.get("secure") else "http"
            url = f"{proto}://{s['host']}:{s['port']}{s['path']}"
            self.tool_endpoints[s["tool"]] = url

        logger.info(f"[Manager] Loaded tool endpoints: {self.tool_endpoints}")

        # Conversation histories and LLM client
        self.histories: Dict[str, List[ChatMessage]] = {}
        self.client = Client()

        # 1) 에이전트 인스턴스 생성 & registry
        self.agents = {
            "UserAgent": UserAgent(self),
            "WeatherAgent": WeatherAgent(self),
            "WikiAgent": WikiAgent(self),
            "ExchangeAgent": ExchangeAgent(self),
        }
        

    async def send_to_agent(self, a2a_msg: A2AMessage) -> MCPMessage:
        """
        Agent 간 메시지를 중계하는 헬퍼.
        - a2a_msg.to_agent 에 해당하는 에이전트의 handle() 호출
        - 그 응답이 A2AMessage 면 다시 handle_message 순환
        - ChatCompletion 이면 반환
        """
        agent = self.agents.get(a2a_msg.to_agent)
        if not agent:
            raise RuntimeError(f"No such agent: {a2a_msg.to_agent}")
        resp = await agent.handle(a2a_msg)
        # 만약 응답이 또 A2AMessage 라면 순환 처리
        if isinstance(resp, A2AMessage):
            return await self.handle_message(resp)
        # ChatCompletion 이면 그대로 반환
        return resp
    
    def wrap_chat(self, msgs: List[Dict[str, str]]) -> ChatCompletion:
        """
        Turn a list of {"role":..., "content":...} dicts into a ChatCompletion
        """
        chat_msgs = [ChatMessage(role=m["role"], content=m["content"]) for m in msgs]
        return ChatCompletion(type="chat_completion", messages=chat_msgs)

    async def handle_message(self, msg: MCPMessage) -> MCPMessage:
        # 1) RegisterAgent 시 UserAgent 등록
        if isinstance(msg, RegisterAgent):
            self.histories[msg.agent_id] = []
            return msg

        # 2) ChatCompletion → UserAgent로 변환
        if isinstance(msg, ChatCompletion):

            user_text = msg.messages[-1].content.lower()

            # —— WeatherAgent 호출 —— #
            if "weather in" in user_text:
                raw = msg.messages[-1].content
                city = raw.split("weather in")[-1].strip()
                city = city.rstrip("?!.").strip()
                a2a = A2AMessage(
                    type="ExecuteTool",
                    from_agent="UserAgent",
                    to_agent="WeatherAgent",
                    payload={"city": city}
                )
                return await self.send_to_agent(a2a)
            
            # —— WikiAgent 호출 —— #
            if any(user_text.startswith(k) for k in ("tell me about", "who is", "what is")) or "from wikipedia" in user_text:
                # 1) 엔티티 이름 정리
                raw_query = re.sub(
                    r'^(tell me about|who is|what is)\s+',
                    '',
                    user_text.rstrip(' ?!'),
                    flags=re.IGNORECASE
                )
                query = clean_query(raw_query)
                logger.info(f"[Manager] A2A wiki invoke for {query}")

                # 2) A2A 메시지 생성 & 전송
                a2a = A2AMessage(
                    type="ExecuteTool",
                    from_agent="UserAgent",
                    to_agent="WikiAgent",
                    payload={"query": query}
                )
                return await self.send_to_agent(a2a)
            
            # —— ExchangeAgent 호출 —— #
            if "exchange rate" in user_text:
                txt_clean = user_text.rstrip('?.!')
                base = symbol = None

                # 1) "from USD to KRW"
                m = re.search(r'from\s+([a-z]{3})\s+to\s+([a-z]{3})', txt_clean)
                if m:
                    base, symbol = m.group(1).upper(), m.group(2).upper()

                # 2) "USD to KRW"
                elif re.search(r'([a-z]{3})\s+to\s+([a-z]{3})', txt_clean):
                    m2 = re.search(r'([a-z]{3})\s+to\s+([a-z]{3})', txt_clean)
                    base, symbol = m2.group(1).upper(), m2.group(2).upper()

                # 3) "in korea" 스타일
                elif re.search(r'in\s+([a-z\s]+)', txt_clean):
                    country = re.search(r'in\s+([a-z\s]+)', txt_clean).group(1).strip()
                    country_map = {
                        "korea": "KRW", "south korea": "KRW",
                        "japan": "JPY", "china": "CNY",
                        "us": "USD", "usa": "USD",
                        "europe": "EUR", "uk": "GBP", "canada": "CAD"
                    }
                    if country in country_map:
                        base, symbol = "USD", country_map[country]

                # 4) 기본값
                if base is None or symbol is None:
                    base, symbol = "USD", "KRW"
                    
                a2a = A2AMessage(
                    type="ExecuteTool",
                    from_agent="UserAgent",
                    to_agent="ExchangeAgent",
                    payload={"base": base, "symbol": symbol}
                )
                return await self.send_to_agent(a2a)

            # —— 그 외: LLM 그대로 응답 —— #
            return msg

        # 3) A2AMessage 직접 처리
        if isinstance(msg, A2AMessage):
            # send_to_agent를 통해 처리 흐름 순환
            return await self.send_to_agent(msg)

        # 4) ToolInvocation: call endpoint
        if isinstance(msg, ToolInvocation):
            logger.info(f"[Manager] Invoking tool: {msg.tool_name} with args {msg.args}")
            result = await self._invoke_tool(msg.tool_name, msg.args)
            resp = ToolResponse(type="tool_response", tool_name=msg.tool_name, result=result)
            agent_id = getattr(msg, "agent_id", "default")
            self.histories.setdefault(agent_id, []).append(
                ChatMessage(role="assistant", content=json.dumps(result))
            )
            return resp

        # 5) ToolResponse: add to history and re-query LLM
        if isinstance(msg, ToolResponse):
            agent_id = getattr(msg, "agent_id", "default")
            self.histories.setdefault(agent_id, []).append(
                ChatMessage(role="tool", content=json.dumps(msg.result))
            )
            llm_resp = self.client.chat(self.histories[agent_id])
            if isinstance(llm_resp, ChatCompletion):
                self.histories[agent_id].extend(llm_resp.messages)
            return llm_resp

        # 5) 그 외는 echo
        logger.warning(f"[Manager] Unhandled message type: {type(msg)}")
        return msg

    async def _invoke_tool(self, tool_name: str, args: dict) -> dict:
        """
        Dynamically route to whichever tool server is in servers.json
        """
        if tool_name not in self.tool_endpoints:
            raise RuntimeError(f"No endpoint configured for tool `{tool_name}`")
        url = self.tool_endpoints[tool_name]
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=args) as resp:
                resp.raise_for_status()
                return await resp.json()