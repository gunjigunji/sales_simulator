class SimulationError(Exception):
    """シミュレーション関連の基本例外クラス"""

    pass


class PersonaGenerationError(SimulationError):
    """ペルソナ生成時のエラー"""

    pass


class EvaluationError(SimulationError):
    """提案評価時のエラー"""

    pass


class ConversationError(SimulationError):
    """会話シミュレーション時のエラー"""

    pass


class SituationUpdateError(SimulationError):
    """状況更新時のエラー"""

    pass


class APIError(SimulationError):
    """API呼び出し時のエラー"""

    pass


class ValidationError(SimulationError):
    """データ検証時のエラー"""

    pass


class ConfigurationError(SimulationError):
    """設定関連のエラー"""

    pass
