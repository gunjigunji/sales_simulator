import os
from typing import Dict, List, Optional

from openai import OpenAI

from src.config.settings import SimulationConfig


class OpenAIClient:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set")

    def call_chat_api(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        OpenAI Chat APIを呼び出す

        Args:
            messages: メッセージのリスト
            model: 使用するモデル（デフォルトは設定値）
            temperature: 温度パラメータ（デフォルトは設定値）
            max_tokens: 最大トークン数（デフォルトは設定値）

        Returns:
            APIからの応答テキスト
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {str(e)}")
