from openai import OpenAI
from typing import Dict, Any, Optional, Union
from langchain_core.runnables import Runnable
from langchain_core.pydantic_v1 import BaseModel
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import json

class OpenAIClient(Runnable, BaseModel):
    api_key: str
    model_id: str = "gpt-4o-mini"
    client: Any = None

    def __init__(self, api_key: str, model_id: str = "gpt-4o-mini", **kwargs):
        super().__init__(api_key=api_key, model_id=model_id, **kwargs)
        self.client = OpenAI(api_key=api_key)
        self.model_id = model_id

    def invoke(self, input: Union[Dict[str, Any], Any], config: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        try:
            # Validate and extract messages
            messages = self._extract_messages(input)
            
            # Filter valid OpenAI parameters
            allowed_params = {
                "model": self.model_id,
                "messages": messages,
                "temperature": input.get("temperature", 0.7) if isinstance(input, dict) else 0.7,
                "max_tokens": input.get("max_tokens", 1000) if isinstance(input, dict) else 1000,
            }
            
            # Add valid config parameters
            if config:
                allowed_params.update({
                    k: v for k, v in config.items() 
                    if k in ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"]
                })

            response = self.client.chat.completions.create(**allowed_params)
            return response.choices[0].message.content

        except Exception as e:
            error_msg = f"Lỗi khi gọi OpenAI API: {str(e)}"
            print(error_msg)
            return error_msg

    def _extract_messages(self, input: Union[Dict[str, Any], Any]) -> list:
        """Extract and validate messages from input"""
        if isinstance(input, dict):
            return [{"role": msg["role"], "content": msg["content"]} 
                   for msg in input.get("messages", [])]
        
        if hasattr(input, "messages"):
            messages = []
            for msg in input.messages:
                if isinstance(msg, SystemMessage):
                    messages.append({"role": "system", "content": msg.content})
                elif isinstance(msg, HumanMessage):
                    messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    messages.append({"role": "assistant", "content": msg.content})
                else:
                    raise TypeError(f"Loại tin nhắn không được hỗ trợ: {type(msg).__name__}")
            return messages
            
        raise TypeError(f"Định dạng input không được hỗ trợ: {type(input).__name__}")

    @property
    def InputType(self) -> type:
        return Dict[str, Any]

    @property 
    def OutputType(self) -> type:
        return str
