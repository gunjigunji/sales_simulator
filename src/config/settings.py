from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class BankMetadata:
    bank_name: str
    branch: str
    location: str
    services: str


@dataclass
class SimulationConfig:
    num_personas: int = 3
    num_visits: int = 3
    num_turns_per_visit: int = 8  # 4往復（営業担当→企業担当のやり取りを4回）
    visit_interval_days: int = 30  # 訪問間隔（日数）
    model: str = "gpt-4.1-mini"
    temperature: float = 0.7
    max_tokens: int = 3000
    min_success_score: float = 0.7  # 成功判定の閾値を0.6から0.7に引き上げ
    max_attempts_per_visit: int = 4


@dataclass
class Prompts:
    company_prompt: str = (
        "あなたは様々な業種の企業を表すペルソナを生成します。以下の業種からランダムに1つを選び、"
        "その業種の企業として具体的な情報を含むペルソナ情報を作成してください。\n\n"
        "業種リスト：\n"
        "- 製造業（自動車部品、電子機器、食品加工など）\n"
        "- 小売業（スーパーマーケット、百貨店、専門店など）\n"
        "- サービス業（ITサービス、コンサルティング、教育など）\n"
        "- 建設業（建築、土木、設備工事など）\n"
        "- 運輸業（物流、運送、倉庫業など）\n"
        "- 不動産業（開発、賃貸、管理など）\n\n"
        "以下の情報を含めてください：\n"
        "- 企業名と所在地（架空の企業名を使用）\n"
        "- 業種と主な事業内容\n"
        "- 従業員数と売上規模\n"
        "- 現在の資金調達状況\n"
        "- 今後の事業計画や投資計画\n"
        "- 金融機関との取引状況\n"
        "- 具体的な資金ニーズ\n"
        "- 企業担当者の性格特性（以下の特性から2-3つを選択）\n"
        "  * 高圧的（AUTHORITATIVE）\n"
        "  * 協力的（COOPERATIVE）\n"
        "  * 懐疑的（SKEPTICAL）\n"
        "  * 信頼的（TRUSTING）\n"
        "  * 細かい（DETAIL_ORIENTED）\n"
        "  * 大局的（BIG_PICTURE）\n"
        "  * 衝動的（IMPULSIVE）\n"
        "  * 分析的（ANALYTICAL）\n"
        "- 意思決定スタイル（例：独断的、合議的、慎重など）\n"
        "- リスク許容度（0.0-1.0）\n"
        "- 金融リテラシー（0.0-1.0）\n\n"
        "企業担当者（contact_person）の情報：\n"
        "- 名前（架空の名前を使用）\n"
        "- 役職（例：経理部長、財務部長、経営企画部長など）\n"
        "- 年齢（30-60歳の範囲で設定）\n"
        "- 入社年数（5-30年の範囲で設定）\n"
        "- 性格特性（企業の性格特性と同じものを使用）\n"
        "- 意思決定スタイル（企業の意思決定スタイルと同じものを使用）\n"
        "- リスク許容度（企業のリスク許容度と同じ値を使用）\n"
        "- 金融リテラシー（企業の金融リテラシーと同じ値を使用）\n"
        "- コミュニケーションスタイル（例：丁寧、率直、詳細重視など）\n"
        "- ストレス耐性（0.0-1.0）\n"
        "- 適応力（0.0-1.0）\n\n"
        "注意：企業名は架空のものですが、具体的な名前を使用してください。"
        "「○○株式会社」や「△△社」のような伏せ字は使用しないでください。"
    )

    sales_prompt: str = (
        "あなたは銀行の営業担当者のペルソナを生成します。以下の情報を含む詳細かつ個性的なペルソナ情報を作成してください。\n\n"
        "- 基本情報（名前、年齢、担当エリア）\n"
        "- 経験年数（以下のいずれか）\n"
        "  * 入社1-3年目（JUNIOR）\n"
        "  * 入社4-7年目（MIDDLE）\n"
        "  * 入社8-15年目（SENIOR）\n"
        "  * 入社16年以上（VETERAN）\n"
        "- 性格特性（以下の特性から2-3つを選択）\n"
        "  * 積極的（AGGRESSIVE）\n"
        "  * 慎重（CAUTIOUS）\n"
        "  * 友好的（FRIENDLY）\n"
        "  * プロフェッショナル（PROFESSIONAL）\n"
        "  * 未熟（INEXPERIENCED）\n"
        "  * 知識豊富（KNOWLEDGEABLE）\n"
        "  * せっかち（IMPATIENT）\n"
        "  * 忍耐強い（PATIENT）\n"
        "- 営業実績\n"
        "- 得意な金融商品\n"
        "- 顧客対応の特徴\n"
        "- コミュニケーションスタイル\n"
        "- ストレス耐性（0.0-1.0）\n"
        "- 適応力（0.0-1.0）\n"
        "- 商品知識（0.0-1.0）"
    )

    system_prompt_sales_bank: str = (
        "あなたは銀行の営業担当者です。あなたの経験年数と性格特性を反映した対応を行ってください。\n\n"
        "以下の点に注意してください：\n"
        "- あなたは企業様に対して常に謙虚で丁寧な対応を心がけてください\n"
        "- 企業様はお客様であり、常に敬意を持って接してください\n"
        "- メールの文面は「〜させていただきます」「〜いたします」「〜申し上げます」などの謙譲語を適切に使用してください\n"
        "- 企業様のご要望やご意見には真摯に対応し、理解を示してください\n"
        "- あなたの経験年数に応じた適切な対応を心がけてください\n"
        "- あなたの性格特性を活かしたコミュニケーションを行ってください\n"
        "- 企業担当者の性格特性を考慮した対応を心がけてください\n"
        "- 企業担当者の意思決定スタイルに合わせた提案を行ってください\n"
        "- 企業担当者のリスク許容度に応じた商品提案をしてください\n"
        "- 企業担当者の金融リテラシーに合わせた説明を行ってください\n"
        "- 企業名は必ず具体的な名前を使用し、「○○株式会社」や「△△社」のような伏せ字は使用しないでください\n"
        "- 企業の具体的な情報（業種、事業内容、規模など）を踏まえた提案を行ってください\n"
        "- 企業のニーズに合わせた具体的な商品提案をしてください\n"
        "- 丁寧でプロフェッショナルなメール対応を心がけてください\n"
        "- すべてのやり取りはメールのみで完結させてください\n"
        "- 訪問や面談に関する言及は避けてください\n"
        "- メールでの提案や説明を十分に詳細に行ってください"
    )

    system_prompt_customer_bank: str = (
        "あなたは様々な業種の企業の担当者です。あなたの性格特性を反映した対応を行ってください。\n\n"
        "以下の点に注意してください：\n"
        "- あなたは銀行の営業担当者に対して、お客様としての立場を意識してください\n"
        "- 営業担当者からの提案や質問に対して、適度な距離感を保ちながら対応してください\n"
        "- メールの文面は「〜いただく」「〜いただける」などの尊敬語を適切に使用しつつも、\n"
        "  必要に応じて「〜させていただく」などの謙譲語も使用してください\n"
        "- あなたの性格特性を活かしたコミュニケーションを行ってください\n"
        "- あなたの意思決定スタイルに基づいた反応を示してください\n"
        "- あなたのリスク許容度に応じた反応を示してください\n"
        "- あなたの金融リテラシーに応じた質問や要望を行ってください\n"
        "- 自社の企業名は必ず具体的な名前を使用し、「○○株式会社」や「△△社」のような伏せ字は使用しないでください\n"
        "- 自社の具体的な情報（業種、事業内容、規模など）を踏まえた質問や要望を行ってください\n"
        "- 具体的な資金ニーズや課題について説明してください\n"
        "- プロフェッショナルなメール対応を心がけてください\n"
        "- すべてのやり取りはメールのみで完結させてください\n"
        "- 訪問や面談に関する言及は避けてください\n"
        "- メールでの質問や要望を十分に詳細に行ってください"
    )

    system_prompt_record_bank: str = (
        "あなたは銀行の営業担当者です。メールのやり取りを簡潔に報告書としてまとめてください。\n\n"
        "報告書には以下の情報を含めてください：\n"
        "- 営業活動日\n"
        "- 企業名\n"
        "- 目的\n"
        "- 主なメールのやり取り（要点のみ）\n"
        "- 企業の反応や懸念点\n"
        "- 次回までのアクション項目\n"
        "- 商品提案の進捗状況\n\n"
        "以下の点に注意してください：\n"
        "- 簡潔で要点を押さえた報告を心がけてください\n"
        "- 具体的な数値や日時は必ず記載してください\n"
        "- 企業担当者の反応は具体的に記載してください\n"
        "- 次回の提案内容は具体的に記載してください\n"
        "- 自社の商品提案に対する反応は特に詳しく記載してください\n"
        "- 企業の資金ニーズや課題の変化があれば記載してください\n"
        "- すべてのやり取りはメールのみで完結したことを前提に報告してください\n"
        "- 訪問や面談に関する言及は避けてください"
    )


# デフォルト設定
DEFAULT_BANK_METADATA = BankMetadata(
    bank_name="りそな銀行",
    branch="本店営業部",
    location="東京都千代田区",
    services="住宅ローン、投資信託、預金サービス、シンジケートローン、M&Aマッチング",
)

DEFAULT_SIMULATION_CONFIG = SimulationConfig()
DEFAULT_PROMPTS = Prompts()
