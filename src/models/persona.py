import random
from enum import Enum
from typing import Dict, List, Optional

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
    status: SalesStatus = SalesStatus.INITIAL
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

    def update_situation(self, days_passed: int) -> None:
        """経過日数に応じて企業の状況を更新する"""
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

            change_rate = random.uniform(-volatility, volatility)
            new_sales = current_sales * (1 + change_rate)
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

            change_rate = random.uniform(-volatility, volatility)
            self.employee_count = int(self.employee_count * (1 + change_rate))
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
