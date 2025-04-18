import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from pydantic import BaseModel, Field, ValidationError

from src.models.evaluation import (
    EvaluationCriteria,
    EvaluationResult,
    InterestLevel,
    InterestScore,
    Proposal,
)
from src.models.settings import SimulationConfig
from src.services.evaluation_service import ProposalEvaluator
from src.services.openai_client import OpenAIClient


class InterestScoreResponse(BaseModel):
    """LLMからの興味度評価レスポンスを構造化するモデル"""

    interest_score: float = Field(ge=0.0, le=100.0, description="興味度スコア（0-100）")
    reasoning: str = Field(description="スコア評価の理由説明")
    key_factors: List[str] = Field(description="評価に考慮した主な要因のリスト")

    class Config:
        json_schema_extra = {
            "example": {
                "interest_score": 75.5,
                "reasoning": "提案内容が企業のニーズと合致しており、具体的な数値も示されている",
                "key_factors": ["ニーズとの適合性", "提案の具体性", "実現可能性"],
            }
        }


class SalesStatus(str, Enum):
    INITIAL = "initial"  # 初回訪問前
    IN_PROGRESS = "in_progress"  # 営業中
    SUCCESS = "success"  # 成約
    FAILED = "failed"  # 断られた
    PENDING = "pending"  # 検討中


class ProductType(str, Enum):
    LOAN = "loan"  # 融資
    INVESTMENT = "investment"  # 投資商品
    DEPOSIT = "deposit"  # 預金商品
    INSURANCE = "insurance"  # 保険商品
    OTHER = "other"  # その他


class ExperienceLevel(str, Enum):
    JUNIOR = "junior"  # 入社1-3年目
    MIDDLE = "middle"  # 入社4-7年目
    SENIOR = "senior"  # 入社8-15年目
    VETERAN = "veteran"  # 入社16年以上


class PersonalityTrait(str, Enum):
    # 営業担当者の性格特性
    AGGRESSIVE = "aggressive"  # 積極的
    CAUTIOUS = "cautious"  # 慎重
    FRIENDLY = "friendly"  # 友好的
    PROFESSIONAL = "professional"  # プロフェッショナル
    INEXPERIENCED = "inexperienced"  # 未熟
    KNOWLEDGEABLE = "knowledgeable"  # 知識豊富
    IMPATIENT = "impatient"  # せっかち
    PATIENT = "patient"  # 忍耐強い


class CustomerPersonalityTrait(str, Enum):
    # 企業担当者の性格特性
    AUTHORITATIVE = "authoritative"  # 高圧的
    COOPERATIVE = "cooperative"  # 協力的
    SKEPTICAL = "skeptical"  # 懐疑的
    TRUSTING = "trusting"  # 信頼的
    DETAIL_ORIENTED = "detail_oriented"  # 細かい
    BIG_PICTURE = "big_picture"  # 大局的
    IMPULSIVE = "impulsive"  # 衝動的
    ANALYTICAL = "analytical"  # 分析的


class RejectionReason(str, Enum):
    """商品・提案の拒否理由"""

    BUDGET_CONSTRAINT = "budget_constraint"  # 予算制約
    LOW_PRIORITY = "low_priority"  # 優先度が低い
    VENDOR_SWITCH_CONCERN = "vendor_switch_concern"  # 他社への乗り換え懸念
    COMPLEX_APPROVAL = "complex_approval"  # 社内決裁プロセスの複雑さ
    TIMING_ISSUE = "timing_issue"  # タイミングが合わない
    RISK_CONCERN = "risk_concern"  # リスクへの懸念
    ALTERNATIVE_SOLUTION = "alternative_solution"  # 代替案の存在
    INTERNAL_RESISTANCE = "internal_resistance"  # 社内の抵抗
    COST_CONCERN = "cost_concern"  # コストへの懸念
    FEATURE_MISMATCH = "feature_mismatch"  # 機能のミスマッチ


class ResponseType(str, Enum):
    """メールの応答タイプ"""

    POSITIVE = "positive"  # 前向きな返信
    NEUTRAL = "neutral"  # 中立的な返信
    NEGATIVE = "negative"  # 否定的な返信
    NO_RESPONSE = "no_response"  # 返信なし
    REJECTION = "rejection"  # 明確な拒否
    QUESTION = "question"  # 追加質問
    ACCEPTANCE = "acceptance"  # 提案受諾


class ConversationContext(BaseModel):
    """会話コンテキスト管理モデル"""

    last_contact_date: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(), description="最終接触日"
    )
    discussed_topics: List[str] = Field(
        default_factory=list, description="議論されたトピックのリスト"
    )
    promised_actions: List[str] = Field(
        default_factory=list, description="約束された行動のリスト"
    )
    interest_history: List[InterestScore] = Field(
        default_factory=list, description="興味度の履歴"
    )
    rejection_history: List[RejectionReason] = Field(
        default_factory=list, description="拒否理由の履歴"
    )
    product_discussions: Dict[ProductType, List[str]] = Field(
        default_factory=lambda: {pt: [] for pt in ProductType},
        description="商品タイプごとの議論履歴",
    )

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        # 商品タイプごとの議論履歴の初期化を確実に行う
        if not self.product_discussions:
            self.product_discussions = {pt: [] for pt in ProductType}

    def cleanup_old_records(self, retention_visits: int = 3):
        """古い記録を削除"""
        if len(self.interest_history) > retention_visits:
            self.interest_history = self.interest_history[-retention_visits:]
        if len(self.rejection_history) > retention_visits:
            self.rejection_history = self.rejection_history[-retention_visits:]
        if len(self.discussed_topics) > retention_visits * 2:
            self.discussed_topics = self.discussed_topics[-(retention_visits * 2) :]
        if len(self.promised_actions) > retention_visits * 2:
            self.promised_actions = self.promised_actions[-(retention_visits * 2) :]

        # 商品別議論履歴の整理
        current_time = datetime.now()
        for product_type in self.product_discussions:
            # retention_visits * 30日より古い記録を削除
            self.product_discussions[product_type] = [
                date_str
                for date_str in self.product_discussions[product_type]
                if (current_time - datetime.fromisoformat(date_str)).days
                <= retention_visits * 30
            ]

    def add_topic(self, topic: str):
        """話題を追加"""
        if topic not in self.discussed_topics:
            self.discussed_topics.append(topic)

    def add_action(self, action: str):
        """約束した行動を追加"""
        if action not in self.promised_actions:
            self.promised_actions.append(action)

    def add_product_discussion(self, product_type: ProductType):
        """商品の議論を記録"""
        if product_type not in self.product_discussions:
            self.product_discussions[product_type] = []
        self.product_discussions[product_type].append(datetime.now().isoformat())

    def get_recent_topics(self, limit: int = 3) -> List[str]:
        """最近の話題を取得"""
        return self.discussed_topics[-limit:]

    def get_recent_actions(self, limit: int = 3) -> List[str]:
        """最近の約束した行動を取得"""
        return self.promised_actions[-limit:]

    def get_product_discussion_frequency(
        self, product_type: ProductType, days: int = 90
    ) -> int:
        """指定期間内の商品議論回数を取得"""
        if product_type not in self.product_discussions:
            return 0

        current_time = datetime.now()
        return sum(
            1
            for date_str in self.product_discussions[product_type]
            if (current_time - datetime.fromisoformat(date_str)).days <= days
        )


class BasePersona(BaseModel):
    id: str
    type: str  # "sales" or "company"


class SalesAttempt(BaseModel):
    product_type: ProductType
    description: str
    success_score: float = Field(ge=0.0, le=1.0)
    feedback: str
    timestamp: str


class SalesProgress(BaseModel):
    status: SalesStatus = SalesStatus.IN_PROGRESS
    current_visit: int = 1
    attempts: List[SalesAttempt] = Field(default_factory=list)
    total_score: float = 0.0
    matched_products: List[ProductType] = Field(default_factory=list)
    customer_interest: Dict[ProductType, float] = Field(default_factory=dict)


class SalesPersona(BasePersona):
    name: str
    age: int
    area: str
    experience_level: ExperienceLevel
    personality_traits: List[PersonalityTrait]
    achievements: List[str] = Field(description="営業実績のリスト")
    specialties: List[str] = Field(description="得意な金融商品のリスト")
    characteristics: List[str] = Field(description="顧客対応の特徴のリスト")
    content: str  # 元のテキスト形式の内容を保持
    success_rate: float = Field(ge=0.0, le=1.0, default=0.5)  # 営業成功率
    communication_style: str  # コミュニケーションスタイル
    stress_tolerance: float = Field(ge=0.0, le=1.0)  # ストレス耐性
    adaptability: float = Field(ge=0.0, le=1.0)  # 適応力
    product_knowledge: float = Field(ge=0.0, le=1.0)  # 商品知識

    def calculate_success_rate(self) -> float:
        """経験値と性格特性に基づいて成功率を計算"""
        base_rate = 0.5

        # 経験値による調整
        experience_multiplier = {
            ExperienceLevel.JUNIOR: 0.7,
            ExperienceLevel.MIDDLE: 0.85,
            ExperienceLevel.SENIOR: 1.0,
            ExperienceLevel.VETERAN: 1.2,
        }

        # 性格特性による調整
        trait_multipliers = {
            PersonalityTrait.AGGRESSIVE: 1.1,
            PersonalityTrait.CAUTIOUS: 0.9,
            PersonalityTrait.FRIENDLY: 1.05,
            PersonalityTrait.PROFESSIONAL: 1.15,
            PersonalityTrait.INEXPERIENCED: 0.8,
            PersonalityTrait.KNOWLEDGEABLE: 1.1,
            PersonalityTrait.IMPATIENT: 0.9,
            PersonalityTrait.PATIENT: 1.05,
        }

        # 基本成功率の計算
        success_rate = base_rate * experience_multiplier[self.experience_level]

        # 性格特性による調整
        for trait in self.personality_traits:
            success_rate *= trait_multipliers[trait]

        # その他の属性による調整
        success_rate *= 0.3 + 0.7 * self.stress_tolerance
        success_rate *= 0.3 + 0.7 * self.adaptability
        success_rate *= 0.3 + 0.7 * self.product_knowledge

        return min(1.0, max(0.0, success_rate))


class CompanyContactPersona(BasePersona):
    """企業担当者のペルソナ"""

    name: str
    position: str  # 役職
    age: int
    years_in_company: int  # 入社年数
    personality_traits: List[CustomerPersonalityTrait]
    decision_making_style: str  # 意思決定スタイル
    risk_tolerance: float = Field(ge=0.0, le=1.0)  # リスク許容度
    financial_literacy: float = Field(ge=0.0, le=1.0)  # 金融リテラシー
    communication_style: str  # コミュニケーションスタイル
    stress_tolerance: float = Field(ge=0.0, le=1.0)  # ストレス耐性
    adaptability: float = Field(ge=0.0, le=1.0)  # 適応力
    content: str  # 元のテキスト形式の内容を保持

    def calculate_response_style(self) -> Dict[str, float]:
        """性格特性に基づいて応答スタイルを計算"""
        style = {
            "formality": 0.5,  # フォーマル度
            "detail": 0.5,  # 詳細度
            "speed": 0.5,  # 返信速度
            "cooperation": 0.5,  # 協力度
        }

        # 性格特性による調整
        for trait in self.personality_traits:
            if trait == CustomerPersonalityTrait.AUTHORITATIVE:
                style["formality"] += 0.2
                style["cooperation"] -= 0.1
            elif trait == CustomerPersonalityTrait.COOPERATIVE:
                style["cooperation"] += 0.2
                style["speed"] += 0.1
            elif trait == CustomerPersonalityTrait.SKEPTICAL:
                style["detail"] += 0.2
                style["speed"] -= 0.1
            elif trait == CustomerPersonalityTrait.TRUSTING:
                style["cooperation"] += 0.2
                style["speed"] += 0.1
            elif trait == CustomerPersonalityTrait.DETAIL_ORIENTED:
                style["detail"] += 0.3
                style["speed"] -= 0.2
            elif trait == CustomerPersonalityTrait.BIG_PICTURE:
                style["detail"] -= 0.2
                style["speed"] += 0.1
            elif trait == CustomerPersonalityTrait.IMPULSIVE:
                style["speed"] += 0.3
                style["detail"] -= 0.2
            elif trait == CustomerPersonalityTrait.ANALYTICAL:
                style["detail"] += 0.3
                style["speed"] -= 0.2

        # その他の属性による調整
        style["formality"] += (
            0.1 * self.years_in_company / 10
        )  # 年数によるフォーマル度の増加
        style["detail"] += (
            0.2 * self.financial_literacy
        )  # 金融リテラシーによる詳細度の増加
        style["speed"] += 0.2 * self.adaptability  # 適応力による速度の増加
        style["cooperation"] += (
            0.2 * self.stress_tolerance
        )  # ストレス耐性による協力度の増加

        # 値を0.0-1.0の範囲に制限
        for key in style:
            style[key] = max(0.0, min(1.0, style[key]))

        return style


class NegotiationStage(str, Enum):
    """商談の段階を表す列挙型"""

    INITIAL = "initial"  # 初期検討段階
    INFORMATION_GATHERING = "information_gathering"  # 情報収集段階
    DETAILED_REVIEW = "detailed_review"  # 詳細検討段階
    FINAL_EVALUATION = "final_evaluation"  # 最終評価段階
    DECISION_MAKING = "decision_making"  # 意思決定段階


class NegotiationProgress(BaseModel):
    """商談進捗管理モデル"""

    stage: NegotiationStage = Field(default=NegotiationStage.INITIAL)
    key_concerns: List[str] = Field(default_factory=list)
    decision_criteria: List[str] = Field(default_factory=list)
    required_information: List[str] = Field(default_factory=list)
    evaluation_points: Dict[str, float] = Field(default_factory=dict)
    last_updated: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )  # datetimeの代わりにstrを使用

    def update_stage(self, new_stage: NegotiationStage):
        """商談段階を更新"""
        self.stage = new_stage
        self.last_updated = datetime.now().isoformat()

    def add_concern(self, concern: str):
        """懸念事項を追加"""
        if concern not in self.key_concerns:
            self.key_concerns.append(concern)

    def remove_concern(self, concern: str):
        """解決された懸念事項を削除"""
        if concern in self.key_concerns:
            self.key_concerns.remove(concern)

    def update_evaluation(self, criteria: str, score: float):
        """評価スコアを更新"""
        self.evaluation_points[criteria] = score

    @property
    def last_updated_datetime(self) -> datetime:
        """last_updatedをdatetime型で取得"""
        return datetime.fromisoformat(self.last_updated)

    class Config:
        json_schema_extra = {
            "example": {
                "stage": "initial",
                "key_concerns": [],
                "decision_criteria": [],
                "required_information": [],
                "evaluation_points": {},
                "last_updated": datetime.now().isoformat(),
            }
        }


class DecisionMaking(BaseModel):
    """意思決定モデル"""

    criteria_met: Dict[str, bool] = Field(default_factory=dict)
    remaining_concerns: List[str] = Field(default_factory=list)
    decision_factors: List[str] = Field(default_factory=list)
    final_decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decision_date: Optional[str] = None  # datetimeの代わりにstrを使用

    def record_decision(self, decision: str, reason: str):
        """最終判断を記録"""
        self.final_decision = decision
        self.decision_reason = reason
        self.decision_date = datetime.now().isoformat()

    @property
    def decision_date_datetime(self) -> Optional[datetime]:
        """decision_dateをdatetime型で取得"""
        return (
            datetime.fromisoformat(self.decision_date) if self.decision_date else None
        )

    class Config:
        json_schema_extra = {
            "example": {
                "criteria_met": {},
                "remaining_concerns": [],
                "decision_factors": [],
                "final_decision": None,
                "decision_reason": None,
                "decision_date": datetime.now().isoformat(),
            }
        }


class CompanyPersona(BasePersona):
    name: str
    location: str
    industry: str
    business_description: str
    employee_count: int
    annual_sales: str
    funding_status: str
    future_plans: str
    banking_relationships: str
    financial_needs: str
    content: str
    personality_traits: List[CustomerPersonalityTrait]
    decision_making_style: str
    risk_tolerance: float = Field(ge=0.0, le=1.0)
    financial_literacy: float = Field(ge=0.0, le=1.0)
    interest_products: Dict[ProductType, float] = Field(
        default_factory=lambda: {
            ProductType.LOAN: 0.5,
            ProductType.INVESTMENT: 0.5,
            ProductType.DEPOSIT: 0.5,
            ProductType.INSURANCE: 0.5,
            ProductType.OTHER: 0.5,
        }
    )
    contact_person: Optional[CompanyContactPersona] = None

    conversation_context: ConversationContext = Field(
        default_factory=ConversationContext
    )
    current_interest_score: InterestScore = Field(
        default_factory=lambda: InterestScore(
            score=50.0,
            level=InterestLevel.MODERATE,
            factors={},
            timestamp=datetime.now().isoformat(),
        )
    )
    rejection_reasons: List[RejectionReason] = Field(default_factory=list)
    response_history: List[ResponseType] = Field(default_factory=list)
    negotiation_progress: NegotiationProgress = Field(
        default_factory=lambda: NegotiationProgress(
            stage=NegotiationStage.INITIAL,
            key_concerns=[],
            decision_criteria=[],
            required_information=[],
            evaluation_points={},
            last_updated=datetime.now().isoformat(),
        )
    )
    decision_making: DecisionMaking = Field(default_factory=DecisionMaking)

    @classmethod
    def model_validate(cls, value, **kwargs):
        if isinstance(value, dict):
            # current_interest_scoreのデフォルト値を設定
            if (
                "current_interest_score" not in value
                or not value["current_interest_score"]
            ):
                value["current_interest_score"] = InterestScore(
                    score=50.0,
                    level=InterestLevel.MODERATE,
                    factors={},
                    timestamp=datetime.now().isoformat(),
                ).model_dump()
            # negotiation_progressのデフォルト値を設定
            if "negotiation_progress" not in value:
                value["negotiation_progress"] = NegotiationProgress().model_dump()
            elif isinstance(value["negotiation_progress"], dict):
                # 既存のnegotiation_progressを補完
                default_progress = NegotiationProgress().model_dump()
                for key, default_value in default_progress.items():
                    if (
                        key not in value["negotiation_progress"]
                        or not value["negotiation_progress"][key]
                    ):
                        value["negotiation_progress"][key] = default_value
            # conversation_contextのデフォルト値を設定
            if "conversation_context" not in value:
                value["conversation_context"] = ConversationContext().model_dump()
            # interest_productsのデフォルト値を設定
            if "interest_products" not in value:
                value["interest_products"] = {
                    ProductType.LOAN.value: 0.5,
                    ProductType.INVESTMENT.value: 0.5,
                    ProductType.DEPOSIT.value: 0.5,
                    ProductType.INSURANCE.value: 0.5,
                    ProductType.OTHER.value: 0.5,
                }

        return super().model_validate(value, **kwargs)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "サンプル株式会社",
                "location": "東京都千代田区",
                "industry": "製造業",
                "business_description": "電子部品の製造",
                "employee_count": 100,
                "annual_sales": "10億円",
                "funding_status": "安定",
                "future_plans": "海外展開を検討中",
                "banking_relationships": "メインバンクとして取引中",
                "financial_needs": "運転資金",
                "content": "",
                "personality_traits": ["analytical", "cooperative"],
                "decision_making_style": "慎重",
                "risk_tolerance": 0.5,
                "financial_literacy": 0.7,
                "current_interest_score": {
                    "score": 50.0,
                    "level": "moderate",
                    "factors": {},
                    "timestamp": datetime.now().isoformat(),
                },
                "negotiation_progress": {
                    "stage": "initial",
                    "key_concerns": [],
                    "decision_criteria": [],
                    "required_information": [],
                    "evaluation_points": {},
                    "last_updated": datetime.now().isoformat(),
                },
            }
        }

    def __init__(self, **data):
        super().__init__(**data)
        # 会話コンテキストの初期化を確実に行う
        if not hasattr(self, "conversation_context"):
            self.conversation_context = ConversationContext()
        # 興味度スコアの初期化
        if not hasattr(self, "current_interest_score"):
            self.current_interest_score = InterestScore(
                score=50.0,
                level=InterestLevel.MODERATE,
                factors={},
            )
        # 商品への興味度の初期化
        if not hasattr(self, "interest_products"):
            self.interest_products = {product_type: 0.5 for product_type in ProductType}

    def validate_product_type(
        self, product_type: Optional[ProductType]
    ) -> Optional[ProductType]:
        """
        商品タイプの妥当性を検証

        Args:
            product_type: 検証する商品タイプ

        Returns:
            検証済みの商品タイプ、または None

        Raises:
            ValueError: 無効な商品タイプの場合
        """
        if product_type is None:
            return None
        try:
            return ProductType(product_type.value)
        except ValueError:
            print(f"Warning: Invalid product type {product_type}, defaulting to None")
            return None

    def calculate_interest_score_with_llm(
        self,
        message_content: str,
        product_type: Optional[ProductType] = None,
        config: Optional[SimulationConfig] = None,
        openai_client: Optional[OpenAIClient] = None,
    ) -> InterestScore:
        """LLMを使用してメッセージ内容から興味度スコアを計算"""
        if not openai_client:
            raise ValueError("OpenAI client is required for LLM-based scoring")

        # 商品タイプの検証
        validated_product_type = self.validate_product_type(product_type)

        try:
            # 企業担当者の視点でメッセージを評価するためのプロンプト
            prompt = f"""
            あなたは以下の特性を持つ企業の担当者です：

            企業情報：
            - 企業名：{self.name}
            - 業種：{self.industry}
            - 事業内容：{self.business_description}
            - 規模：従業員数{self.employee_count}名、売上{self.annual_sales}
            - 資金ニーズ：{self.financial_needs}

            あなたの特性：
            - 役職：{self.contact_person.position if self.contact_person else "不明"}
            - 性格：{", ".join([trait.value for trait in self.personality_traits])}
            - 意思決定スタイル：{self.decision_making_style}
            - リスク許容度：{self.risk_tolerance}
            - 金融リテラシー：{self.financial_literacy}

            以下の営業担当者からのメッセージに対する、あなたの興味度を0から100の数値で評価してください。
            評価の際は以下の要素を考慮してください：
            - メッセージの内容と自社のニーズとの適合性
            - 提案内容の具体性と実現可能性
            - 自社の状況との整合性
            - あなたの性格や意思決定スタイルとの相性

            商品タイプ：{validated_product_type.value if validated_product_type else "不明"}

            メッセージ内容：
            {message_content}

            以下のJSON形式で回答してください：
            {{
                "interest_score": 数値（0-100）,
                "reasoning": "スコアの理由の説明",
                "key_factors": ["考慮した主な要因をリストで"]
            }}
            """

            # LLMからの応答を取得
            try:
                response = openai_client.call_structured_api(
                    messages=[{"role": "user", "content": prompt}],
                    response_model=InterestScoreResponse,
                    temperature=0.3,  # 一貫性のために低めの温度を設定
                )
            except Exception as api_error:
                print(f"Error calling OpenAI API: {api_error}")
                raise

            # InterestScoreオブジェクトの作成
            try:
                factors = {
                    f"factor_{i}": factor
                    for i, factor in enumerate(response.key_factors)
                }
                factors["llm_reasoning"] = response.reasoning

                interest_score = InterestScore(
                    score=response.interest_score,
                    product_type=validated_product_type,
                    level=self._determine_interest_level(
                        response.interest_score, config
                    ),
                    factors=factors,
                    timestamp=datetime.now().isoformat(),
                )

                # 履歴の更新
                self.current_interest_score = interest_score
                self.conversation_context.interest_history.append(interest_score)

                return interest_score

            except Exception as processing_error:
                print(f"Error processing LLM response: {processing_error}")
                raise

        except Exception as e:
            print(f"Error in LLM-based scoring: {e}")
            return self.calculate_interest_score_keyword_based(
                message_content, validated_product_type, config
            )

    def calculate_interest_score_keyword_based(
        self,
        message_content: str,
        product_type: Optional[ProductType] = None,
        config: Optional[SimulationConfig] = None,
    ) -> InterestScore:
        """キーワードベースで興味度スコアを計算（従来の実装）"""
        evaluator = ProposalEvaluator(
            risk_tolerance=self.risk_tolerance,
            financial_literacy=self.financial_literacy,
            annual_sales=self.annual_sales,
            industry=self.industry,
            personality_traits=[trait.value for trait in self.personality_traits],
            interest_products={
                pt.value: score for pt, score in self.interest_products.items()
            },
        )

        product_type_str = product_type.value if product_type else None
        interest_score = evaluator.calculate_interest_score(
            message_content, product_type_str
        )

        # InterestScoreをProductTypeを使用する形式に変換
        converted_score = InterestScore(
            score=interest_score.score,
            product_type=ProductType(interest_score.product_type)
            if interest_score.product_type
            else None,
            level=interest_score.level,
            factors=interest_score.factors,
            timestamp=interest_score.timestamp,
        )

        # 履歴の更新
        self.current_interest_score = converted_score
        self.conversation_context.interest_history.append(converted_score)

        return converted_score

    def calculate_interest_score(
        self,
        message_content: str,
        product_type: Optional[ProductType] = None,
        config: Optional[SimulationConfig] = None,
        openai_client: Optional[OpenAIClient] = None,
    ) -> InterestScore:
        """
        メッセージ内容から興味度スコアを計算
        LLMベースの評価を優先し、エラー時にキーワードベースにフォールバック
        """
        try:
            if openai_client:
                return self.calculate_interest_score_with_llm(
                    message_content, product_type, config, openai_client
                )
            else:
                return self.calculate_interest_score_keyword_based(
                    message_content, product_type, config
                )
        except Exception as e:
            print(f"Error in interest score calculation: {e}")
            # 最終的なフォールバック：キーワードベース評価
            return self.calculate_interest_score_keyword_based(
                message_content, product_type, config
            )

    def determine_response_type(
        self,
        interest_score: Optional[InterestScore] = None,
        config: Optional[SimulationConfig] = None,
    ) -> ResponseType:
        """興味度スコアから応答タイプを決定"""
        # interest_scoreが指定されていない場合は現在のスコアを使用
        score_to_use = interest_score or self.current_interest_score

        # 性格特性による基準値の調整
        threshold_modifier = 0.0
        for trait in self.personality_traits:
            if trait == CustomerPersonalityTrait.COOPERATIVE:
                threshold_modifier += 5.0
            elif trait == CustomerPersonalityTrait.SKEPTICAL:
                threshold_modifier -= 5.0

        # 設定パラメータから閾値を取得
        thresholds = {
            "acceptance": 80.0,
            "positive": 60.0,
            "question": 40.0,
            "neutral": 20.0,
        }
        if config and config.response_type_thresholds:
            thresholds.update(config.response_type_thresholds)

        # スコアに基づく応答タイプの決定
        adjusted_score = score_to_use.score
        if adjusted_score >= (thresholds["acceptance"] + threshold_modifier):
            response_type = ResponseType.ACCEPTANCE
        elif adjusted_score >= (thresholds["positive"] + threshold_modifier):
            response_type = ResponseType.POSITIVE
        elif adjusted_score >= (thresholds["question"] + threshold_modifier):
            response_type = ResponseType.QUESTION
        elif adjusted_score >= (thresholds["neutral"] + threshold_modifier):
            response_type = ResponseType.NEUTRAL
        else:
            # 低スコアの場合、一定確率で明確な拒否か返信なしを選択
            if random.random() < 0.3:  # 30%の確率で
                response_type = ResponseType.NO_RESPONSE
            else:
                response_type = ResponseType.REJECTION

        # 履歴の更新
        self.response_history.append(response_type)
        return response_type

    def select_rejection_reason(self) -> RejectionReason:
        """現在の状況に基づいて適切な拒否理由を選択"""
        # 性格特性と過去の拒否理由を考慮
        available_reasons = list(RejectionReason)

        # 性格特性による重み付け
        weights = [1.0] * len(available_reasons)
        for trait in self.personality_traits:
            if trait == CustomerPersonalityTrait.ANALYTICAL:
                # 分析的な性格は予算やコストの懸念を重視
                weights[available_reasons.index(RejectionReason.BUDGET_CONSTRAINT)] *= (
                    1.5
                )
                weights[available_reasons.index(RejectionReason.COST_CONCERN)] *= 1.5
            elif trait == CustomerPersonalityTrait.SKEPTICAL:
                # 懐疑的な性格はリスクや代替案を重視
                weights[available_reasons.index(RejectionReason.RISK_CONCERN)] *= 1.5
                weights[
                    available_reasons.index(RejectionReason.ALTERNATIVE_SOLUTION)
                ] *= 1.5

        # 過去に使用した理由は避ける
        for used_reason in self.rejection_reasons[-3:]:  # 直近3回の理由
            if used_reason in available_reasons:
                idx = available_reasons.index(used_reason)
                weights[idx] *= 0.5

        # 重み付けに基づいて理由を選択
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        selected_reason = random.choices(available_reasons, normalized_weights, k=1)[0]

        # 履歴の更新
        self.rejection_reasons.append(selected_reason)
        return selected_reason

    def update_situation(self, days_passed: int) -> None:
        """経過日数に応じて企業の状況を更新する"""
        # 変化率の初期化
        sales_change_rate = 0.0
        employee_change_rate = 0.0

        # 売上規模の変化（性格特性に応じて変動幅を調整）
        try:
            sales_str = "".join(filter(str.isdigit, self.annual_sales))
            if not sales_str:
                current_sales = 10.0
            else:
                current_sales = float(sales_str)

            # 性格特性に応じた変動幅の調整
            volatility = 0.05  # 基本変動幅
            if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits:
                volatility *= 1.5
            if CustomerPersonalityTrait.CAUTIOUS in self.personality_traits:
                volatility *= 0.7

            sales_change_rate = random.uniform(-volatility, volatility)
            new_sales = current_sales * (1 + sales_change_rate)
            self.annual_sales = f"{new_sales:.1f}億円"
        except (ValueError, AttributeError):
            pass

        # 従業員数の変化（性格特性に応じて変動幅を調整）
        try:
            volatility = 0.02  # 基本変動幅
            if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits:
                volatility *= 1.5
            if CustomerPersonalityTrait.CAUTIOUS in self.personality_traits:
                volatility *= 0.7

            employee_change_rate = random.uniform(-volatility, volatility)
            self.employee_count = int(self.employee_count * (1 + employee_change_rate))
        except (ValueError, AttributeError):
            pass

        # 資金ニーズの変化（性格特性に応じて変化）
        try:
            if "設備投資" in self.financial_needs:
                urgency = (
                    "緊急"
                    if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits
                    else "計画"
                )
                self.financial_needs = self.financial_needs.replace(
                    "設備投資", f"設備投資（{urgency}、{days_passed}日経過）"
                )
            elif "運転資金" in self.financial_needs:
                urgency = (
                    "緊急"
                    if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits
                    else "計画"
                )
                self.financial_needs = self.financial_needs.replace(
                    "運転資金", f"運転資金（{urgency}、{days_passed}日経過）"
                )
        except (ValueError, AttributeError):
            pass

        # 商品への興味度の変化（性格特性に応じて変化）
        try:
            for product_type in self.interest_products:
                # 基本変動幅
                base_change = 0.1

                # 性格特性による調整
                if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits:
                    base_change *= 1.5
                if CustomerPersonalityTrait.CAUTIOUS in self.personality_traits:
                    base_change *= 0.7
                if CustomerPersonalityTrait.ANALYTICAL in self.personality_traits:
                    base_change *= 0.8

                change = random.uniform(-base_change, base_change)
                self.interest_products[product_type] = max(
                    0.0, min(1.0, self.interest_products[product_type] + change)
                )
        except (ValueError, AttributeError):
            pass

        # 企業担当者の状況も更新
        if self.contact_person:
            # ストレス耐性の変化（企業の状況に応じて）
            try:
                # 売上減少や資金ニーズの緊急性が高い場合、ストレスが増加
                stress_change = 0.0
                if "減少" in self.annual_sales:
                    stress_change += 0.1
                if "緊急" in self.financial_needs:
                    stress_change += 0.15

                # 基本変動
                base_stress_change = random.uniform(-0.05, 0.05)
                stress_change += base_stress_change

                # 性格特性による調整
                if (
                    CustomerPersonalityTrait.IMPULSIVE
                    in self.contact_person.personality_traits
                ):
                    stress_change *= 1.2
                if (
                    CustomerPersonalityTrait.CAUTIOUS
                    in self.contact_person.personality_traits
                ):
                    stress_change *= 0.8

                self.contact_person.stress_tolerance = max(
                    0.0, min(1.0, self.contact_person.stress_tolerance - stress_change)
                )
            except (ValueError, AttributeError):
                pass

            # 適応力の変化（企業の状況に応じて）
            try:
                # 企業の変化が大きい場合、適応力が向上
                adaptability_change = 0.0
                if (
                    abs(sales_change_rate) > 0.1 or abs(employee_change_rate) > 0.1
                ):  # 大きな変化があった場合
                    adaptability_change += 0.05

                # 基本変動
                base_adaptability_change = random.uniform(-0.03, 0.03)
                adaptability_change += base_adaptability_change

                # 性格特性による調整
                if (
                    CustomerPersonalityTrait.ANALYTICAL
                    in self.contact_person.personality_traits
                ):
                    adaptability_change *= 1.1
                if (
                    CustomerPersonalityTrait.IMPULSIVE
                    in self.contact_person.personality_traits
                ):
                    adaptability_change *= 0.9

                self.contact_person.adaptability = max(
                    0.0,
                    min(1.0, self.contact_person.adaptability + adaptability_change),
                )
            except (ValueError, AttributeError):
                pass

    def evaluate_proposal(self, proposal: Proposal) -> EvaluationResult:
        """提案内容を評価し、判断を行う"""
        evaluator = ProposalEvaluator(
            risk_tolerance=self.risk_tolerance,
            financial_literacy=self.financial_literacy,
            annual_sales=self.annual_sales,
            industry=self.industry,
            personality_traits=[trait.value for trait in self.personality_traits],
            interest_products={
                pt.value: score for pt, score in self.interest_products.items()
            },
        )
        return evaluator.evaluate_proposal(proposal)

    def _determine_interest_level(
        self, score: float, config: Optional[SimulationConfig] = None
    ) -> InterestLevel:
        """
        スコアから興味レベルを判定

        Args:
            score (float): 興味度スコア（0-100）
            config (Optional[SimulationConfig]): シミュレーション設定

        Returns:
            InterestLevel: 判定された興味レベル
        """
        if config and config.interest_score_thresholds:
            thresholds = config.interest_score_thresholds
            if score >= thresholds.get("very_high", 80.0):
                return InterestLevel.VERY_HIGH
            elif score >= thresholds.get("high", 60.0):
                return InterestLevel.HIGH
            elif score >= thresholds.get("moderate", 40.0):
                return InterestLevel.MODERATE
            elif score >= thresholds.get("low", 20.0):
                return InterestLevel.LOW
            else:
                return InterestLevel.VERY_LOW
        else:
            if score >= 80:
                return InterestLevel.VERY_HIGH
            elif score >= 60:
                return InterestLevel.HIGH
            elif score >= 40:
                return InterestLevel.MODERATE
            elif score >= 20:
                return InterestLevel.LOW
            else:
                return InterestLevel.VERY_LOW


class Assignment(BaseModel):
    sales_persona: SalesPersona
    assigned_companies: List[CompanyPersona]
    progress: Dict[str, SalesProgress] = Field(
        default_factory=dict
    )  # company_id -> progress


class SessionHistory(BaseModel):
    role: str
    content: str
    product_type: Optional[ProductType] = None
    success_score: Optional[float] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )  # ISO形式に統一

    def to_dict(self) -> Dict[str, Any]:
        """Convert the history entry to a plain dictionary."""
        result: Dict[str, Any] = {
            "role": self.role,
            "timestamp": self.timestamp,
            "content": self.content,
        }
        if self.product_type is not None:
            result["product_type"] = self.product_type.value
        if self.success_score is not None:
            result["success_score"] = self.success_score
        return result

    class Config:
        json_schema_extra = {
            "example": {
                "role": "assistant",
                "content": "メッセージ内容",
                "product_type": None,
                "success_score": None,
                "timestamp": datetime.now().isoformat(),
            }
        }


class SessionSummary(BaseModel):
    session_num: int
    timestamp: str
    visit_date: str  # 訪問日を追加
    history: List[SessionHistory]
    final_status: SalesStatus
    matched_products: List[ProductType]


class MeetingLog(BaseModel):
    session_num: int
    visit_date: str  # 訪問日を追加
    content: str
    status: SalesStatus
    matched_products: List[ProductType]


class SimulationResult(BaseModel):
    sales_persona: SalesPersona
    company_persona: CompanyPersona
    session_logs: List[SessionSummary]
    individual_meeting_logs: List[MeetingLog]
    overall_meeting_log: str
    final_status: SalesStatus
    matched_products: List[ProductType]


class ProposalAnalysis(BaseModel):
    """営業提案の分析結果を構造化するモデル"""

    product_type: ProductType
    success_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    customer_reaction: str
    next_steps: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)

    class Config:
        json_schema_extra = {
            "example": {
                "product_type": "loan",
                "success_score": 0.75,
                "reasoning": "企業の資金ニーズと商品の特徴が一致している",
                "customer_reaction": "前向きな反応を示している",
                "next_steps": ["詳細な条件提示", "審査書類の準備"],
                "concerns": ["金利水準", "担保条件"],
                "confidence": 0.85,
            }
        }


class EmailMessage(BaseModel):
    """メール形式のメッセージを構造化するモデル"""

    subject: str = Field(description="メールの件名")
    body: str = Field(description="メールの本文")
    sender: str = Field(description="送信者名")
    recipient: str = Field(description="受信者名")
    date: str = Field(
        description="送信日時",
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    product_type: Optional[ProductType] = Field(
        default=None, description="関連する商品タイプ"
    )
    success_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="成功スコア"
    )

    def to_dict(self) -> Dict[str, Any]:
        """メッセージを辞書形式に変換"""
        result: Dict[str, Any] = {
            "subject": self.subject,
            "body": self.body,
            "sender": self.sender,
            "recipient": self.recipient,
            "date": self.date,
        }
        if self.product_type is not None:
            result["product_type"] = self.product_type.value
        if self.success_score is not None:
            result["success_score"] = self.success_score
        return result

    def format_as_email(self) -> str:
        """メール形式で整形して返す"""
        return f"""
件名: {self.subject}
送信者: {self.sender}
受信者: {self.recipient}
日時: {self.date}

{self.body}
"""
