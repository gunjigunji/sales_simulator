from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.persona import (
    CustomerPersonalityTrait,
    EvaluationCriteria,
    EvaluationResult,
    Proposal,
)


class ProposalEvaluator:
    """提案評価を行うクラス"""

    def __init__(
        self,
        risk_tolerance: float,
        financial_literacy: float,
        annual_sales: str,
        industry: str,
        personality_traits: List[CustomerPersonalityTrait],
    ):
        self.risk_tolerance = risk_tolerance
        self.financial_literacy = financial_literacy
        self.annual_sales = annual_sales
        self.industry = industry
        self.personality_traits = personality_traits

    def evaluate_proposal(self, proposal: Proposal) -> EvaluationResult:
        """提案内容を評価し、判断を行う"""
        scores = self._calculate_evaluation_scores(proposal)
        concerns = self._identify_remaining_concerns(proposal)
        criteria_met = self._check_decision_criteria(proposal)

        if self._is_ready_for_decision(scores, concerns, criteria_met):
            decision = self._make_final_decision(scores, concerns, criteria_met)
            return EvaluationResult(
                decision=decision,
                scores=scores,
                concerns=concerns,
                required_info=None,
                evaluation_date=datetime.now(),
            )
        else:
            return EvaluationResult(
                decision="pending",
                scores=scores,
                concerns=concerns,
                required_info=self._identify_required_information(proposal),
                evaluation_date=datetime.now(),
            )

    def _calculate_evaluation_scores(self, proposal: Proposal) -> Dict[str, float]:
        """提案内容の各評価基準に対するスコアを計算"""
        return {
            EvaluationCriteria.COST.value: self._evaluate_cost(
                proposal.cost_information
            ),
            EvaluationCriteria.RISK.value: self._evaluate_risk(proposal.risks),
            EvaluationCriteria.BENEFIT.value: self._evaluate_benefits(
                proposal.benefits
            ),
            EvaluationCriteria.FEASIBILITY.value: self._evaluate_feasibility(proposal),
            EvaluationCriteria.SUPPORT.value: self._evaluate_support(
                proposal.support_details
            ),
            EvaluationCriteria.TRACK_RECORD.value: self._evaluate_track_record(
                proposal.track_record
            ),
        }

    def _evaluate_cost(self, cost_info: Dict[str, Any]) -> float:
        """コスト面の評価を行う"""
        base_score = 0.5

        if "total_cost" in cost_info:
            try:
                cost_ratio = cost_info["total_cost"] / float(self.annual_sales)
                if cost_ratio < 0.01:  # コストが年商の1%未満
                    base_score += 0.3
                elif cost_ratio < 0.05:  # コストが年商の5%未満
                    base_score += 0.1
                else:
                    base_score -= 0.2
            except (ValueError, TypeError):
                # 数値変換に失敗した場合はデフォルトスコアを返す
                return base_score

        # リスク許容度による調整
        base_score *= 0.5 + 0.5 * self.risk_tolerance

        return min(1.0, max(0.0, base_score))

    def _evaluate_risk(self, risks: List[str]) -> float:
        """リスク面の評価を行う"""
        base_score = 0.5
        risk_count = len(risks)

        # リスクの数による基本スコア調整
        if risk_count == 0:
            base_score += 0.3
        elif risk_count <= 2:
            base_score += 0.1
        else:
            base_score -= 0.1 * risk_count

        # リスク許容度による調整
        risk_tolerance_factor = 0.5 + 0.5 * self.risk_tolerance
        base_score *= risk_tolerance_factor

        return min(1.0, max(0.0, base_score))

    def _evaluate_benefits(self, benefits: List[str]) -> float:
        """メリット面の評価を行う"""
        base_score = 0.5
        benefit_count = len(benefits)

        # メリットの数による基本スコア調整
        base_score += 0.1 * benefit_count

        # 金融リテラシーによる調整
        literacy_factor = 0.5 + 0.5 * self.financial_literacy
        base_score *= literacy_factor

        return min(1.0, max(0.0, base_score))

    def _evaluate_feasibility(self, proposal: Proposal) -> float:
        """実現可能性の評価を行う"""
        base_score = 0.7  # 基本的に実現可能性は高めに設定

        # 商品タイプに応じた調整
        if proposal.product_type == "loan":
            # ローンの場合、財務状況との整合性を確認
            if "annual_sales" in proposal.terms:
                try:
                    sales_ratio = float(proposal.terms["annual_sales"]) / float(
                        self.annual_sales
                    )
                    if sales_ratio > 0.5:  # 年商の50%を超える場合
                        base_score -= 0.3
                    elif sales_ratio > 0.3:  # 年商の30%を超える場合
                        base_score -= 0.1
                except (ValueError, TypeError):
                    # 数値変換に失敗した場合はデフォルトスコアを返す
                    return base_score

        return min(1.0, max(0.0, base_score))

    def _evaluate_support(self, support_details: Dict[str, Any]) -> float:
        """サポート体制の評価を行う"""
        base_score = 0.5

        # サポート内容の充実度による調整
        if support_details.get("dedicated_support"):
            base_score += 0.2
        if support_details.get("online_support"):
            base_score += 0.1
        if support_details.get("24h_support"):
            base_score += 0.1

        return min(1.0, max(0.0, base_score))

    def _evaluate_track_record(self, track_record: List[Dict[str, Any]]) -> float:
        """実績の評価を行う"""
        base_score = 0.5

        if not track_record:
            return base_score

        # 実績数による調整
        success_count = sum(
            1 for record in track_record if record.get("success", False)
        )
        success_ratio = success_count / len(track_record)

        base_score += 0.3 * success_ratio

        # 同業種の実績による追加ボーナス
        industry_matches = sum(
            1 for record in track_record if record.get("industry") == self.industry
        )
        if industry_matches > 0:
            base_score += 0.2

        return min(1.0, max(0.0, base_score))

    def _identify_remaining_concerns(self, proposal: Proposal) -> List[str]:
        """未解決の懸念事項を特定"""
        concerns = []
        scores = self._calculate_evaluation_scores(proposal)

        # 各評価基準のスコアに基づいて懸念事項を特定
        if scores[EvaluationCriteria.COST.value] < 0.6:
            concerns.append("コストが高い")
        if scores[EvaluationCriteria.RISK.value] < 0.6:
            concerns.append("リスクが高い")
        if scores[EvaluationCriteria.FEASIBILITY.value] < 0.6:
            concerns.append("実現可能性に不安がある")
        if scores[EvaluationCriteria.SUPPORT.value] < 0.6:
            concerns.append("サポート体制が不十分")
        if scores[EvaluationCriteria.TRACK_RECORD.value] < 0.6:
            concerns.append("実績が不十分")

        return concerns

    def _check_decision_criteria(self, proposal: Proposal) -> Dict[str, bool]:
        """判断基準の充足状況を確認"""
        scores = self._calculate_evaluation_scores(proposal)
        return {
            criteria.value: scores.get(criteria.value, 0.0) >= 0.7
            for criteria in EvaluationCriteria
        }

    def _is_ready_for_decision(
        self,
        scores: Dict[str, float],
        concerns: List[str],
        criteria_met: Dict[str, bool],
    ) -> bool:
        """判断可能な状態かを確認"""
        essential_criteria = [
            EvaluationCriteria.COST.value,
            EvaluationCriteria.RISK.value,
            EvaluationCriteria.BENEFIT.value,
        ]

        # 重要な判断基準が満たされているか確認
        if not all(
            criteria_met.get(criteria, False) for criteria in essential_criteria
        ):
            return False

        # 重大な懸念事項が残っていないか確認
        if len(concerns) > 2:
            return False

        # 十分な情報が得られているか確認
        if min(scores.values()) < 0.4:
            return False

        return True

    def _make_final_decision(
        self,
        scores: Dict[str, float],
        concerns: List[str],
        criteria_met: Dict[str, bool],
    ) -> str:
        """最終判断を行う"""
        # 平均スコアの計算
        avg_score = sum(scores.values()) / len(scores)

        # 判断基準の充足率
        criteria_met_ratio = sum(1 for met in criteria_met.values() if met) / len(
            criteria_met
        )

        # 懸念事項の重要度評価
        concern_weight = len(concerns) * 0.1

        # 最終スコアの計算
        final_score = avg_score * (1 - concern_weight) * criteria_met_ratio

        # 性格特性による調整
        if CustomerPersonalityTrait.CAUTIOUS in self.personality_traits:
            final_score *= 0.9
        if CustomerPersonalityTrait.COOPERATIVE in self.personality_traits:
            final_score *= 1.1

        # 判断
        if final_score >= 0.8:
            return "success"
        elif final_score <= 0.4:
            return "failed"
        else:
            return "pending"

    def _identify_required_information(self, proposal: Proposal) -> List[str]:
        """追加で必要な情報を特定"""
        required_info = []

        # コスト情報の確認
        if not proposal.cost_information.get("total_cost"):
            required_info.append("総コストの詳細")
        if not proposal.cost_information.get("payment_terms"):
            required_info.append("支払条件の詳細")

        # リスク情報の確認
        if not proposal.risks:
            required_info.append("リスク評価の詳細")

        # サポート情報の確認
        if not proposal.support_details:
            required_info.append("サポート体制の詳細")

        # 実績情報の確認
        if not proposal.track_record:
            required_info.append("導入実績の詳細")
        elif not any(
            record.get("industry") == self.industry for record in proposal.track_record
        ):
            required_info.append("同業種での導入実績")

        return required_info
