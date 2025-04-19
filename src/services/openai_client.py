import json
import os
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, cast

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from src.exceptions import APIError, ConfigurationError
from src.models.settings import SimulationConfig

T = TypeVar("T", bound=BaseModel)


class OpenAIClient:
    def __init__(self, config: SimulationConfig):
        self.config = config
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set your OpenAI API key in the environment variables."
            )
        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize OpenAI client: {str(e)}")

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

        Raises:
            APIError: API呼び出しに失敗した場合
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            error_message = f"OpenAI API call failed: {str(e)}"
            print(error_message)
            raise APIError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error during API call: {str(e)}"
            print(error_message)
            raise APIError(error_message) from e

    def call_structured_api(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
    ) -> T:
        """
        構造化された応答を返すOpenAI Chat APIを呼び出す

        Args:
            messages: メッセージのリスト
            response_model: 応答を解析するためのPydanticモデル
            model: 使用するモデル（デフォルトは設定値）
            temperature: 温度パラメータ（デフォルトは設定値）
            max_tokens: 最大トークン数（デフォルトは設定値）
            max_retries: 解析エラー時の最大リトライ回数

        Returns:
            Pydanticモデルに解析された応答

        Raises:
            ValueError: 最大リトライ回数試行しても解析に失敗した場合
        """
        retry_count = 0
        last_error: Optional[Exception] = None

        # リトライループ
        while retry_count <= max_retries:
            try:
                # より低い温度で安定した出力を促進
                current_temp = (temperature or self.config.temperature) * (
                    0.7**retry_count
                )

                # モデルのJSONスキーマを含める
                json_schema = response_model.model_json_schema()
                formatted_messages = list(messages)  # メッセージリストをコピー

                # システムプロンプトを強化して構造化出力を促進
                schema_prompt = f"""
                あなたは構造化されたJSONを返すAPIです。
                応答は必ず以下のJSONスキーマに準拠したJSONオブジェクトのみを返してください。
                余分なテキストや説明は一切含めないでください。

                スキーマ:
                {json.dumps(json_schema, ensure_ascii=False, indent=2)}
                """

                # システムメッセージの更新または追加
                system_message_exists = False
                for msg in formatted_messages:
                    if msg["role"] == "system":
                        msg["content"] = f"{msg['content']}\n\n{schema_prompt}"
                        system_message_exists = True
                        break
                if not system_message_exists:
                    formatted_messages.insert(
                        0, {"role": "system", "content": schema_prompt}
                    )

                # APIを呼び出す
                response = self.client.chat.completions.create(
                    model=model or self.config.model,
                    messages=formatted_messages,
                    temperature=current_temp,
                    max_tokens=max_tokens or self.config.max_tokens,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content.strip()

                # JSONをパースして検証
                parsed_data = response_model.model_validate_json(content)
                return cast(T, parsed_data)

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                print(f"Attempt {retry_count + 1} failed to parse response: {e}")
                retry_count += 1

            except Exception as e:
                # OpenAI API 自体のエラーなど、予期しないエラー
                last_error = e
                print(f"An unexpected error occurred during API call or parsing: {e}")
                break

        # リトライ上限に達した場合
        raise ValueError(
            f"Failed to parse structured response after {max_retries + 1} attempts. Last error: {str(last_error)}"
        ) from last_error
