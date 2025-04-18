from pydantic import BaseModel, Field

from src.models.persona import ProductType


class ProposalAnalysis(BaseModel):
    """LLM が返す提案分析結果を厳格にバリデーションするためのモデル"""

    product_type: ProductType
    success_score: float = Field(ge=0.0, le=1.0)
    feedback: str
