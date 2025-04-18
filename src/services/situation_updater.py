import random
from typing import Dict, Optional

from src.models.persona import (
    CompanyContactPersona,
    CustomerPersonalityTrait,
    ProductType,
)


class SituationUpdater:
    """企業の状況を更新するクラス"""

    def __init__(
        self,
        personality_traits: list[CustomerPersonalityTrait],
        contact_person: Optional[CompanyContactPersona] = None,
    ):
        self.personality_traits = personality_traits
        self.contact_person = contact_person

    def update_sales(self, current_sales: str) -> tuple[str, float]:
        """売上規模の更新"""
        try:
            sales_str = "".join(filter(str.isdigit, current_sales))
            if not sales_str:
                current_sales_value = 10.0
            else:
                current_sales_value = float(sales_str)

            volatility = self._calculate_sales_volatility()
            sales_change_rate = random.uniform(-volatility, volatility)
            new_sales = current_sales_value * (1 + sales_change_rate)

            return f"{new_sales:.1f}億円", sales_change_rate
        except (ValueError, AttributeError):
            return current_sales, 0.0

    def update_employee_count(self, current_count: int) -> tuple[int, float]:
        """従業員数の更新"""
        try:
            volatility = self._calculate_employee_volatility()
            employee_change_rate = random.uniform(-volatility, volatility)
            new_count = int(current_count * (1 + employee_change_rate))

            return max(1, new_count), employee_change_rate
        except (ValueError, AttributeError):
            return current_count, 0.0

    def update_financial_needs(self, current_needs: str, days_passed: int) -> str:
        """資金ニーズの更新"""
        try:
            urgency = (
                "緊急"
                if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits
                else "計画"
            )

            if "設備投資" in current_needs:
                return current_needs.replace(
                    "設備投資", f"設備投資（{urgency}、{days_passed}日経過）"
                )
            elif "運転資金" in current_needs:
                return current_needs.replace(
                    "運転資金", f"運転資金（{urgency}、{days_passed}日経過）"
                )
            return current_needs
        except (ValueError, AttributeError):
            return current_needs

    def update_product_interest(
        self, current_interest: Dict[ProductType, float]
    ) -> Dict[ProductType, float]:
        """商品への興味度の更新"""
        try:
            updated_interest = current_interest.copy()
            base_change = self._calculate_interest_change_rate()

            for product_type in current_interest:
                change = random.uniform(-base_change, base_change)
                updated_interest[product_type] = max(
                    0.0, min(1.0, current_interest[product_type] + change)
                )
            return updated_interest
        except (ValueError, AttributeError):
            return current_interest

    def update_contact_person(
        self,
        sales_change_rate: float,
        employee_change_rate: float,
        financial_needs: str,
    ) -> None:
        """企業担当者の状態を更新"""
        if not self.contact_person:
            return

        try:
            # ストレス耐性の更新
            stress_change = self._calculate_stress_change(
                sales_change_rate, financial_needs
            )
            self.contact_person.stress_tolerance = max(
                0.0,
                min(1.0, self.contact_person.stress_tolerance - stress_change),
            )

            # 適応力の更新
            adaptability_change = self._calculate_adaptability_change(
                sales_change_rate, employee_change_rate
            )
            self.contact_person.adaptability = max(
                0.0,
                min(1.0, self.contact_person.adaptability + adaptability_change),
            )
        except (ValueError, AttributeError):
            pass

    def _calculate_sales_volatility(self) -> float:
        """売上の変動幅を計算"""
        volatility = 0.05  # 基本変動幅
        if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits:
            volatility *= 1.5
        if CustomerPersonalityTrait.CAUTIOUS in self.personality_traits:
            volatility *= 0.7
        return volatility

    def _calculate_employee_volatility(self) -> float:
        """従業員数の変動幅を計算"""
        volatility = 0.02  # 基本変動幅
        if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits:
            volatility *= 1.5
        if CustomerPersonalityTrait.CAUTIOUS in self.personality_traits:
            volatility *= 0.7
        return volatility

    def _calculate_interest_change_rate(self) -> float:
        """興味度の変動幅を計算"""
        base_change = 0.1
        if CustomerPersonalityTrait.IMPULSIVE in self.personality_traits:
            base_change *= 1.5
        if CustomerPersonalityTrait.CAUTIOUS in self.personality_traits:
            base_change *= 0.7
        if CustomerPersonalityTrait.ANALYTICAL in self.personality_traits:
            base_change *= 0.8
        return base_change

    def _calculate_stress_change(
        self, sales_change_rate: float, financial_needs: str
    ) -> float:
        """ストレス変化量を計算"""
        stress_change = 0.0

        # 売上減少や資金ニーズの緊急性による影響
        if sales_change_rate < 0:
            stress_change += 0.1
        if "緊急" in financial_needs:
            stress_change += 0.15

        # 基本変動
        base_stress_change = random.uniform(-0.05, 0.05)
        stress_change += base_stress_change

        # 性格特性による調整
        if self.contact_person:
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

        return stress_change

    def _calculate_adaptability_change(
        self, sales_change_rate: float, employee_change_rate: float
    ) -> float:
        """適応力の変化量を計算"""
        adaptability_change = 0.0

        # 大きな変化があった場合の影響
        if abs(sales_change_rate) > 0.1 or abs(employee_change_rate) > 0.1:
            adaptability_change += 0.05

        # 基本変動
        base_adaptability_change = random.uniform(-0.03, 0.03)
        adaptability_change += base_adaptability_change

        # 性格特性による調整
        if self.contact_person:
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

        return adaptability_change
