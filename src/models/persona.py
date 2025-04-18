import random
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class BasePersona(BaseModel):
    id: str
    type: str  # "sales" or "company"


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


class CompanyContactPersona(BaseModel):
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
    content: str  # 元のテキスト形式の内容を保持
    personality_traits: List[CustomerPersonalityTrait]
    decision_making_style: str  # 意思決定スタイル
    risk_tolerance: float = Field(ge=0.0, le=1.0)  # リスク許容度
    financial_literacy: float = Field(ge=0.0, le=1.0)  # 金融リテラシー
    interest_products: Dict[ProductType, float] = Field(
        default_factory=lambda: {
            ProductType.LOAN: 0.5,
            ProductType.INVESTMENT: 0.5,
            ProductType.DEPOSIT: 0.5,
            ProductType.INSURANCE: 0.5,
            ProductType.OTHER: 0.5,
        }
    )
    contact_person: Optional[CompanyContactPersona] = None  # 企業担当者を追加

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
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

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
