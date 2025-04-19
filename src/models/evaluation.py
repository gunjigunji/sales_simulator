from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.settings import SimulationConfig


class EvaluationCriteria(str, Enum):
    """評価基準を表す列挙型"""

    COST = "cost"  # コスト面
    RISK = "risk"  # リスク面
    BENEFIT = "benefit"  # メリット面
    FEASIBILITY = "feasibility"  # 実現可能性
    SUPPORT = "support"  # サポート体制
    TRACK_RECORD = "track_record"  # 実績


class InterestLevel(str, Enum):
    """興味レベルを表す列挙型"""

    VERY_HIGH = "very_high"  # 非常に興味あり（スコア: 80-100）
    HIGH = "high"  # 興味あり（スコア: 60-79）
    MODERATE = "moderate"  # やや興味あり（スコア: 40-59）
    LOW = "low"  # あまり興味なし（スコア: 20-39）
    VERY_LOW = "very_low"  # 全く興味なし（スコア: 0-19）


class InterestScore(BaseModel):
    """興味度スコアを表現するモデル"""

    score: float = Field(ge=0.0, le=100.0, description="興味度スコア（0-100）")
    product_type: Optional[str] = Field(
        default=None, description="評価対象の商品タイプ"
    )
    level: InterestLevel = Field(description="興味レベルの判定結果")
    factors: Dict[str, Any] = Field(
        default_factory=dict, description="スコアに影響を与えた要因"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="評価時刻"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "score": 75.5,
                "product_type": "LOAN",
                "level": "HIGH",
                "factors": {
                    "cooperative_trait": 1.2,
                    "product_interest": 0.8,
                    "content_analysis": 0.6,
                },
                "timestamp": "2024-01-01T12:00:00",
            }
        }

    @classmethod
    def model_validate(cls, value, **kwargs):
        if isinstance(value, dict) and "timestamp" not in value:
            value["timestamp"] = datetime.now().isoformat()
        return super().model_validate(value, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "score": self.score,
            "product_type": self.product_type,
            "level": self.level.value,
            "factors": self.factors,
            "timestamp": self.timestamp,
        }


class EvaluationResult(BaseModel):
    """提案評価結果を構造化するモデル"""

    decision: str
    scores: Dict[str, float]
    concerns: List[str]
    required_info: Optional[List[str]] = None
    evaluation_date: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        arbitrary_types_allowed = True


class Proposal(BaseModel):
    """提案内容モデル"""

    product_type: str
    terms: Dict[str, Any]
    benefits: List[str]
    risks: List[str]
    cost_information: Dict[str, Any]
    support_details: Dict[str, Any]
    track_record: List[Dict[str, Any]]
