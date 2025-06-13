# mcp/message_schema.py

from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, List, Union

class RegisterAgent(BaseModel):
    type: Literal["register_agent"]
    agent_id: str = Field(..., description="Unique identifier for this agent")

class ToolInvocation(BaseModel):
    type: Literal["tool_invocation"]
    tool_name: str = Field(..., description="Name of the tool to invoke")
    args: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool")

class ToolResponse(BaseModel):
    type: Literal["tool_response"]
    tool_name: str
    result: Any = Field(..., description="Result returned by the tool")

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatCompletion(BaseModel):
    type: Literal["chat_completion"]
    messages: List[ChatMessage]

# 예시: MCP 전체 메시지 타입 유니언
MCPMessage = Union[RegisterAgent, ToolInvocation, ToolResponse, ChatCompletion]

class A2AMessage(BaseModel):
    type: Literal["ExecuteTool", "ToolResult"]
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
