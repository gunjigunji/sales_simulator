from src.models.settings import BankMetadata, Prompts, SimulationConfig

# デフォルト設定
DEFAULT_BANK_METADATA = BankMetadata(
    bank_name="りそな銀行",
    branch="本店営業部",
    location="東京都千代田区",
    services="住宅ローン、投資信託、預金サービス、シンジケートローン、M&Aマッチング",
)

DEFAULT_SIMULATION_CONFIG = SimulationConfig()
DEFAULT_PROMPTS = Prompts()
