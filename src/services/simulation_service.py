import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.config.settings import BankMetadata, Prompts, SimulationConfig
from src.models.persona import (
    Assignment,
    CompanyPersona,
    CustomerPersonalityTrait,
    ExperienceLevel,
    MeetingLog,
    PersonalityTrait,
    ProductType,
    SalesPersona,
    SalesProgress,
    SalesStatus,
    SessionHistory,
    SessionSummary,
    SimulationResult,
)
from src.services.openai_client import OpenAIClient


class SessionHistory(BaseModel):
    role: str
    content: str
    product_type: Optional[ProductType] = None
    success_score: Optional[float] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    def to_dict(self) -> Dict[str, Any]:
        """会話履歴を辞書形式に変換"""
        result = {
            "role": self.role,
            "timestamp": self.timestamp,
            "content": self.content,
        }
        if self.product_type:
            result["product_type"] = self.product_type.value
        if self.success_score is not None:
            result["success_score"] = self.success_score
        return result


class SimulationService:
    def __init__(
        self,
        openai_client: OpenAIClient,
        prompts: Prompts,
        bank_metadata: BankMetadata,
        config: SimulationConfig,
    ):
        self.openai_client = openai_client
        self.prompts = prompts
        self.bank_metadata = bank_metadata
        self.config = config

    def generate_personas(
        self, prompt: str, persona_type: str
    ) -> List[Union[SalesPersona, CompanyPersona]]:
        """ペルソナを生成する"""
        personas = []
        for i in range(self.config.num_personas):
            # JSONスキーマを取得
            schema = self._get_persona_schema(persona_type)

            # より具体的な指示を含むプロンプトを作成
            enhanced_prompt = f"""
            {prompt}

            以下の点に注意してください：
            1. 出力は必ずJSON形式で行ってください
            2. 以下のJSONスキーマに厳密に従ってください
            3. 数値は必ず数値型として出力してください（文字列ではありません）
            4. 配列は必ず配列として出力してください
            5. 列挙型の値は指定された値のいずれかを使用してください
            6. 余分なテキストや説明は含めないでください
            7. JSONの開始と終了を示す中括弧のみを出力してください
            8. 文字列型のフィールド（例：name, location, annual_salesなど）は必ず文字列として出力してください
            9. annual_salesは必ず「XX億円」のような文字列形式で出力してください

            JSONスキーマ：
            {schema}
            """

            messages = [
                {"role": "system", "content": enhanced_prompt},
                {
                    "role": "user",
                    "content": f"ペルソナ{i + 1}の情報を生成してください。",
                },
            ]

            # 温度パラメータを下げて、より確実なJSON生成を促す
            response = self.openai_client.call_chat_api(
                messages, temperature=0.3, max_tokens=3000
            )

            try:
                # JSONレスポンスをパース
                persona_data = json.loads(response)
                # 元のテキスト形式の内容も保持
                persona_data["content"] = response

                if persona_type == "sales":
                    persona = SalesPersona(**persona_data)
                else:
                    # annual_salesが数値型の場合は文字列型に変換
                    if isinstance(persona_data.get("annual_sales"), (int, float)):
                        persona_data["annual_sales"] = (
                            f"{persona_data['annual_sales']}億円"
                        )
                    persona = CompanyPersona(**persona_data)

                personas.append(persona)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Raw response: {response}")
                # フォールバックとして元の実装を使用
                personas.append(
                    SalesPersona(
                        id=f"{persona_type}_{i + 1}",
                        type=persona_type,
                        name="",
                        age=0,
                        area="",
                        experience_level=ExperienceLevel.JUNIOR,
                        personality_traits=[PersonalityTrait.INEXPERIENCED],
                        achievements=[],
                        specialties=[],
                        characteristics=[],
                        communication_style="",
                        stress_tolerance=0.5,
                        adaptability=0.5,
                        product_knowledge=0.5,
                        content=response,
                    )
                    if persona_type == "sales"
                    else CompanyPersona(
                        id=f"{persona_type}_{i + 1}",
                        type=persona_type,
                        name="",
                        location="",
                        industry="",
                        business_description="",
                        employee_count=0,
                        annual_sales="0億円",
                        funding_status="",
                        future_plans="",
                        banking_relationships="",
                        financial_needs="",
                        personality_traits=[CustomerPersonalityTrait.COOPERATIVE],
                        decision_making_style="慎重",
                        risk_tolerance=0.5,
                        financial_literacy=0.5,
                        interest_products={
                            ProductType.LOAN: 0.5,
                            ProductType.INVESTMENT: 0.5,
                            ProductType.DEPOSIT: 0.5,
                            ProductType.INSURANCE: 0.5,
                            ProductType.OTHER: 0.5,
                        },
                        content=response,
                    )
                )
        return personas

    def _get_persona_schema(self, persona_type: str) -> str:
        """ペルソナタイプに応じたJSONスキーマを返す"""
        if persona_type == "sales":
            return """{
                "id": "sales_1",
                "type": "sales",
                "name": "営業担当者の名前",
                "age": 35,
                "area": "担当エリア",
                "experience_level": "junior|middle|senior|veteran",
                "personality_traits": ["aggressive", "cautious", "friendly", "professional", "inexperienced", "knowledgeable", "impatient", "patient"],
                "achievements": ["営業実績1", "営業実績2"],
                "specialties": ["得意商品1", "得意商品2"],
                "characteristics": ["特徴1", "特徴2"],
                "communication_style": "コミュニケーションスタイル",
                "stress_tolerance": 0.8,
                "adaptability": 0.7,
                "product_knowledge": 0.9
            }"""
        else:
            return """{
                "id": "company_1",
                "type": "company",
                "name": "企業名",
                "location": "所在地",
                "industry": "業種",
                "business_description": "事業内容",
                "employee_count": 100,
                "annual_sales": "売上規模（例：32億円）",
                "funding_status": "資金調達状況",
                "future_plans": "今後の事業計画",
                "banking_relationships": "金融機関との取引状況",
                "financial_needs": "具体的な資金ニーズ",
                "personality_traits": ["authoritative", "cooperative", "skeptical", "trusting", "detail_oriented", "big_picture", "impulsive", "analytical"],
                "decision_making_style": "独断的|合議的|慎重",
                "risk_tolerance": 0.5,
                "financial_literacy": 0.7,
                "interest_products": {
                    "loan": 0.5,
                    "investment": 0.5,
                    "deposit": 0.5,
                    "insurance": 0.5,
                    "other": 0.5
                }
            }"""

    def assign_companies_to_sales(
        self, sales_personas: List[SalesPersona], company_personas: List[CompanyPersona]
    ) -> List[Assignment]:
        """営業担当者に企業を割り当てる"""
        assignments = []
        for sales in sales_personas:
            num_assigned = random.choice([1, 2])
            assigned_companies = random.sample(company_personas, k=num_assigned)
            assignments.append(
                Assignment(sales_persona=sales, assigned_companies=assigned_companies)
            )
        return assignments

    def simulate_bank_conversation_session(
        self,
        sales_persona: SalesPersona,
        company_persona: CompanyPersona,
        progress: SalesProgress,
        prev_history: Optional[str] = None,
        session_num: int = 1,
        visit_date: Optional[datetime] = None,
    ) -> SessionSummary:
        """1回の訪問セッションのシミュレーションを実施"""
        session_history = []
        if prev_history:
            session_history.append(
                SessionHistory(
                    role="system",
                    content=(
                        f"前回の訪問内容を踏まえて、以下の点に注意して会話を進めてください：\n"
                        f"- 前回の提案に対する企業の反応や懸念点を考慮する\n"
                        f"- 前回の会話で得られた情報を活かした提案を行う\n"
                        f"- 前回の訪問から{self.config.visit_interval_days}日が経過していることを考慮する\n"
                        f"- 企業の状況変化を確認する\n"
                        f"- 前回の訪問で提案した商品やサービスの進捗状況を確認する\n"
                        f"- 企業のニーズや課題がどのように変化したかを確認する"
                    ),
                )
            )

        # 営業担当者の初期挨拶プロンプト
        initial_greeting_prompt = f"""
        訪問先：{company_persona.name}
        訪問日：{visit_date.strftime("%Y年%m月%d日") if visit_date else "本日"}
        訪問回数：{session_num}回目
        {"前回の訪問から約1ヶ月が経過しています。" if session_num > 1 else "初回訪問です。"}

        企業情報：
        - 業種：{company_persona.industry}
        - 事業内容：{company_persona.business_description}
        - 従業員数：{company_persona.employee_count}名
        - 売上規模：{company_persona.annual_sales}
        - 資金ニーズ：{company_persona.financial_needs}

        前回の訪問内容：
        {prev_history if prev_history else "初回訪問"}

        以下の点に注意して会話を進めてください：
        - 企業担当者の性格特性を考慮したコミュニケーションを心がけてください
        - 企業担当者の意思決定スタイルに合わせた提案を行ってください
        - 企業担当者のリスク許容度に応じた商品提案をしてください
        - 企業担当者の金融リテラシーに合わせた説明を行ってください
        - 企業の具体的な情報を踏まえた提案を行ってください
        - 企業のニーズに合わせた具体的な商品提案をしてください
        - {f"前回の訪問内容を踏まえて、企業の反応や懸念点を考慮した提案を行ってください" if session_num > 1 else ""}
        - {f"前回の訪問から{self.config.visit_interval_days}日が経過していることを考慮してください" if session_num > 1 else ""}
        - {f"前回の訪問で提案した商品やサービスの進捗状況を確認してください" if session_num > 1 else ""}
        - {f"企業のニーズや課題がどのように変化したかを確認してください" if session_num > 1 else ""}
        """

        messages = [
            {"role": "system", "content": self.prompts.system_prompt_sales_bank},
            {"role": "user", "content": initial_greeting_prompt},
        ]

        initial_greeting = self.openai_client.call_chat_api(messages)
        session_history.append(
            SessionHistory(role="assistant", content=initial_greeting)
        )

        current_role = "customer"
        attempts = 0
        matched_products = []
        final_status = SalesStatus.IN_PROGRESS

        while (
            attempts < self.config.max_attempts_per_visit
            and final_status == SalesStatus.IN_PROGRESS
        ):
            if current_role == "sales":
                # 営業担当者の発言
                messages = [
                    {"role": "system", "content": self.prompts.system_prompt_sales_bank}
                ]
                messages.extend(
                    [{"role": h.role, "content": h.content} for h in session_history]
                )
                response = self.openai_client.call_chat_api(messages)

                # 提案内容の分析とスコアリング
                analysis_prompt = f"""
                以下の営業提案を分析し、以下の情報を厳密にJSON形式で出力してください。
                他のテキストは一切含めないでください。

                評価基準：
                - 成功スコア（0.0-1.0）は以下の要素を考慮して決定してください：
                  * 提案内容が企業のニーズに合致しているか（0.25）
                  * 提案の具体性と実現可能性（0.20）
                  * 提案条件の競争力（金利、期間、担保等）（0.15）
                  * 企業の財務状況との整合性（0.15）
                  * 企業の反応の予測（0.25）

                - 企業の反応は以下のような要素を考慮して予測してください：
                  * 提案内容への関心度
                  * 現在の経営状況との整合性
                  * 資金調達の緊急性
                  * 既存の金融機関との関係性
                  * 市場環境や業界動向との整合性
                  * 意思決定までの社内プロセス
                  * 競合他社からの提案状況
                  * 企業担当者の性格特性
                  * 企業担当者の意思決定スタイル
                  * 企業担当者のリスク許容度
                  * 企業担当者の金融リテラシー

                {{
                    "product_type": "loan|investment|deposit|insurance|other",
                    "success_score": 0.0から1.0の数値,
                    "feedback": "企業の反応の予測（具体的な理由を含めて）"
                }}

                提案内容：
                {response}

                企業情報：
                {company_persona.json()}

                JSONのみを出力してください。
                """

                analysis = self.openai_client.call_chat_api(
                    [{"role": "user", "content": analysis_prompt}],
                    temperature=0.3,
                    max_tokens=3000,
                )

                try:
                    # JSONの開始と終了を探して抽出
                    json_start = analysis.find("{")
                    json_end = analysis.rfind("}") + 1
                    if json_start != -1 and json_end != -1:
                        json_str = analysis[json_start:json_end]
                        # JSONの形式をチェック
                        if not json_str.strip().startswith(
                            "{"
                        ) or not json_str.strip().endswith("}"):
                            raise json.JSONDecodeError(
                                "Invalid JSON format", json_str, 0
                            )
                        analysis_data = json.loads(json_str)
                    else:
                        raise json.JSONDecodeError("No JSON object found", analysis, 0)

                    # 必須フィールドのチェック
                    required_fields = ["product_type", "success_score", "feedback"]
                    for field in required_fields:
                        if field not in analysis_data:
                            raise KeyError(f"Missing required field: {field}")

                    # 型チェック
                    if not isinstance(analysis_data["success_score"], (int, float)):
                        raise ValueError("success_score must be a number")
                    if not isinstance(analysis_data["product_type"], str):
                        raise ValueError("product_type must be a string")
                    if not isinstance(analysis_data["feedback"], str):
                        raise ValueError("feedback must be a string")

                    product_type = ProductType(analysis_data["product_type"])
                    success_score = float(analysis_data["success_score"])

                    # 営業担当者の経験値と性格特性によるスコア調整
                    success_score *= sales_persona.calculate_success_rate()

                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=response,
                            product_type=product_type,
                            success_score=success_score,
                        )
                    )

                    if success_score >= self.config.min_success_score:  # 0.75以上で成功
                        matched_products.append(product_type)
                        final_status = SalesStatus.SUCCESS
                    elif success_score < 0.4:  # 0.4未満で失敗
                        final_status = SalesStatus.FAILED
                    else:  # 0.4-0.75はPENDING
                        final_status = SalesStatus.PENDING

                    attempts += 1
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Error analyzing proposal: {e}")
                    print(f"Raw analysis response: {analysis}")
                    # エラー時はデフォルト値を使用
                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=response,
                            product_type=ProductType.OTHER,
                            success_score=0.5,
                        )
                    )
                    final_status = SalesStatus.PENDING
                    attempts += 1

                current_role = "customer"
            else:
                # 顧客企業の担当者の発言
                messages = [
                    {
                        "role": "system",
                        "content": self.prompts.system_prompt_customer_bank,
                    }
                ]
                messages.extend(
                    [{"role": h.role, "content": h.content} for h in session_history]
                )

                response = self.openai_client.call_chat_api(messages)
                session_history.append(
                    SessionHistory(role="assistant", content=response)
                )
                current_role = "sales"

        # SessionHistoryオブジェクトを辞書に変換
        history_dicts = [h.to_dict() for h in session_history]

        return SessionSummary(
            session_num=session_num,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            visit_date=visit_date.strftime("%Y-%m-%d")
            if visit_date
            else datetime.now().strftime("%Y-%m-%d"),
            history=history_dicts,
            final_status=final_status,
            matched_products=matched_products,
        )

    def record_bank_meeting_log(
        self,
        session_summary: SessionSummary,
        sales_persona: SalesPersona,
        company_persona: CompanyPersona,
    ) -> MeetingLog:
        """訪問記録を生成する"""
        # 営業担当者目線での報告書生成用プロンプト
        report_prompt = f"""
        訪問先：{company_persona.name}
        訪問日：{session_summary.visit_date}
        訪問回数：{session_summary.session_num}回目

        前回の訪問内容：
        {session_summary.history[-2].content if len(session_summary.history) > 1 else "初回訪問"}

        本日の訪問内容：
        {session_summary.history[-1].content}

        商品提案の進捗：
        {", ".join([p.value for p in session_summary.matched_products]) if session_summary.matched_products else "提案中"}
        """

        messages = [
            {"role": "system", "content": self.prompts.system_prompt_record_bank},
            {"role": "user", "content": report_prompt},
        ]

        content = self.openai_client.call_chat_api(messages, max_tokens=3000)
        return MeetingLog(
            session_num=session_summary.session_num,
            visit_date=session_summary.visit_date,
            content=content,
            status=session_summary.final_status,
            matched_products=session_summary.matched_products,
        )

    def simulate_time_series_visits(
        self, sales_persona: SalesPersona, company_persona: CompanyPersona
    ) -> SimulationResult:
        """複数回の訪問セッションをシミュレーション"""
        session_logs = []
        meeting_logs = []
        prev_summary = None
        progress = SalesProgress()
        current_date = datetime.now()

        for visit in range(1, self.config.num_visits + 1):
            # 訪問日を更新
            if visit > 1:
                current_date = current_date + timedelta(
                    days=self.config.visit_interval_days
                )

            # 企業の状況を更新
            days_passed = (visit - 1) * self.config.visit_interval_days
            company_persona.update_situation(days_passed)

            # 前回の訪問内容を準備
            if visit > 1:
                prev_summary = "\n".join(
                    [
                        f"【前回の訪問内容（{visit - 1}回目）】",
                        f"訪問日: {session_logs[-1].visit_date}",
                        f"最終ステータス: {session_logs[-1].final_status}",
                        f"マッチした商品: {', '.join([p.value for p in session_logs[-1].matched_products])}",
                        "会話の要約:",
                        *[f"{h.role}: {h.content}" for h in session_logs[-1].history],
                    ]
                )

            session_summary = self.simulate_bank_conversation_session(
                sales_persona,
                company_persona,
                progress,
                prev_history=prev_summary,
                session_num=visit,
                visit_date=current_date,
            )
            session_logs.append(session_summary)

            meeting_log = self.record_bank_meeting_log(
                session_summary, sales_persona, company_persona
            )
            meeting_logs.append(meeting_log)

            # 進捗状況を更新（ただし、SUCCESSやFAILEDでも次の訪問を継続）
            progress.status = session_summary.final_status
            progress.matched_products.extend(session_summary.matched_products)
            progress.current_visit = visit

        # 最終的なステータスを決定（すべての訪問が終わった後）
        final_status = (
            SalesStatus.SUCCESS
            if any(log.final_status == SalesStatus.SUCCESS for log in session_logs)
            else SalesStatus.FAILED
            if all(log.final_status == SalesStatus.FAILED for log in session_logs)
            else SalesStatus.PENDING
        )

        return SimulationResult(
            sales_persona=sales_persona,
            company_persona=company_persona,
            session_logs=session_logs,
            individual_meeting_logs=meeting_logs,
            overall_meeting_log="\n\n".join([log.content for log in meeting_logs]),
            final_status=final_status,
            matched_products=progress.matched_products,
        )
