"""定数と設定値の定義"""

# 評価関連の定数
EVALUATION_THRESHOLDS = {
    "cost": {
        "very_low": 0.01,  # 年商の1%未満
        "low": 0.05,  # 年商の5%未満
        "score_adjustment": {
            "very_low": 0.3,  # スコア加算値
            "low": 0.1,  # スコア加算値
            "high": -0.2,  # スコア減算値
        },
    },
    "risk": {
        "no_risk": 0.3,  # リスクなしの場合のスコア加算値
        "low_risk": 0.1,  # 低リスクの場合のスコア加算値
        "risk_penalty": 0.1,  # リスク1件あたりのスコア減算値
    },
    "benefit": {
        "per_benefit": 0.1,  # メリット1件あたりのスコア加算値
    },
    "feasibility": {
        "base_score": 0.7,  # 基本スコア
        "sales_ratio": {
            "high": 0.5,  # 年商の50%を超える場合
            "medium": 0.3,  # 年商の30%を超える場合
            "penalty": {
                "high": 0.3,  # スコア減算値
                "medium": 0.1,  # スコア減算値
            },
        },
    },
    "support": {
        "dedicated": 0.2,  # 専任サポートのスコア加算値
        "online": 0.1,  # オンラインサポートのスコア加算値
        "24h": 0.1,  # 24時間サポートのスコア加算値
    },
    "track_record": {
        "success_ratio": 0.3,  # 成功率によるスコア加算係数
        "industry_match": 0.2,  # 同業種実績のスコア加算値
    },
}

# 状況更新関連の定数
SITUATION_UPDATE = {
    "sales": {
        "base_volatility": 0.05,  # 基本変動幅
        "impulsive_multiplier": 1.5,  # 衝動的な性格の場合の乗数
        "cautious_multiplier": 0.7,  # 慎重な性格の場合の乗数
    },
    "employee": {
        "base_volatility": 0.02,  # 基本変動幅
        "impulsive_multiplier": 1.5,
        "cautious_multiplier": 0.7,
    },
    "interest": {
        "base_change": 0.1,  # 基本変動幅
        "impulsive_multiplier": 1.5,
        "cautious_multiplier": 0.7,
        "analytical_multiplier": 0.8,
    },
    "stress": {
        "base_range": (-0.05, 0.05),  # 基本変動範囲
        "sales_decrease_penalty": 0.1,  # 売上減少時のストレス増加
        "urgent_need_penalty": 0.15,  # 緊急ニーズ時のストレス増加
        "impulsive_multiplier": 1.2,
        "cautious_multiplier": 0.8,
    },
    "adaptability": {
        "base_range": (-0.03, 0.03),  # 基本変動範囲
        "significant_change_bonus": 0.05,  # 大きな変化があった場合の適応力向上
        "analytical_multiplier": 1.1,
        "impulsive_multiplier": 0.9,
    },
}

# 判断基準関連の定数
DECISION_CRITERIA = {
    "min_score": 0.7,  # 基準を満たすための最小スコア
    "min_info_score": 0.4,  # 情報が十分とみなす最小スコア
    "max_concerns": 2,  # 許容される最大懸念事項数
    "final_decision": {
        "success": 0.8,  # 成功判定の閾値
        "failure": 0.4,  # 失敗判定の閾値
    },
    "personality_adjustment": {
        "cautious": 0.9,  # 慎重な性格の場合の乗数
        "cooperative": 1.1,  # 協力的な性格の場合の乗数
    },
}

# メッセージ分析関連の定数
MESSAGE_ANALYSIS = {
    "positive_keywords": [
        "ご検討",
        "興味",
        "詳細",
        "ご提案",
        "承知",
        "ありがとう",
        "期待",
        "前向き",
    ],
    "negative_keywords": [
        "結構です",
        "見送り",
        "他社",
        "予算",
        "時期",
        "難しい",
        "検討中",
        "保留",
    ],
    "keyword_weights": {
        "positive": 5.0,
        "negative": -5.0,
    },
}

# 応答タイプの閾値
RESPONSE_THRESHOLDS = {
    "acceptance": 80.0,
    "positive": 60.0,
    "question": 40.0,
    "neutral": 20.0,
    "no_response_probability": 0.3,  # 返信なしの確率
}

# 性格特性による閾値調整
PERSONALITY_THRESHOLD_ADJUSTMENTS = {
    "cooperative": 5.0,  # 協力的な性格の場合の閾値調整値
    "skeptical": -5.0,  # 懐疑的な性格の場合の閾値調整値
}
