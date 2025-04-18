import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, ValidationError

from src.config.settings import BankMetadata, Prompts, SimulationConfig
from src.models.persona import (
    Assignment,
    CompanyPersona,
    CustomerPersonalityTrait,
    EmailMessage,
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
from src.models.proposal_analysis import ProposalAnalysis
from src.services.openai_client import OpenAIClient


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
        PersonaModel: Type[Union[SalesPersona, CompanyPersona]] = (
            SalesPersona if persona_type == "sales" else CompanyPersona
        )

        # プロンプトにJSON出力の指示を追加
        system_prompt = f"""
        {prompt}

        あなたは指定されたペルソナタイプの情報を生成するエキスパートです。
        応答は必ず指定されたJSONスキーマに準拠したJSONオブジェクトのみを返してください。
        余分なテキストや説明は一切含めないでください。
        `annual_sales` は必ず「XX億円」のような文字列形式で出力してください。
        """

        for i in range(self.config.num_personas):
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"ペルソナ{i + 1}の情報を生成してください。",
                },
            ]

            try:
                # call_structured_api を使用
                persona = self.openai_client.call_structured_api(
                    messages,
                    response_model=PersonaModel,
                    temperature=0.3,  # 低めの温度で安定性を高める
                    max_tokens=3000,
                )
                # IDとタイプが未設定の場合に設定 (LLMが省略することがあるため)
                if not persona.id:
                    persona.id = f"{persona_type}_{i + 1}"
                if not persona.type:
                    persona.type = persona_type
                personas.append(persona)

            except (ValueError, ValidationError) as e:
                print(f"Error generating/parsing persona {i + 1}: {e}")
                # エラー発生時はフォールバックとしてデフォルトペルソナを追加（ログ出力のみでも可）
                # ここではログ出力のみとし、リストには追加しない方針も検討可能
                print(f"Falling back to default persona for {persona_type} {i + 1}")

        return personas

    def assign_companies_to_sales(
        self, sales_personas: List[SalesPersona], company_personas: List[CompanyPersona]
    ) -> List[Assignment]:
        """営業担当者に企業を割り当てる"""
        assignments = []
        # 会社リストが空でないことを確認
        if not company_personas:
            print("Warning: No company personas available for assignment.")
            return []

        for sales in sales_personas:
            # 割り当てる会社数を会社の総数以下に制限
            max_assign = min(len(company_personas), 2)
            num_assigned = random.randint(
                1, max_assign
            )  # Use randint for 1 to max_assign inclusive
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
        current_visit_date = visit_date or datetime.now()

        if prev_history:
            prev_summary = f"""
            前回の訪問内容：
            {prev_history}
            ...
            """  # （内容は変更なし）
            session_history.append(SessionHistory(role="system", content=prev_summary))

        # 初回と2回目以降でプロンプトを分岐
        if session_num == 1:
            initial_greeting_prompt = f"""
            以下の情報に基づいて、営業担当者として企業担当者に送る初回メールを生成してください。
            メールは必ず指定されたJSONスキーマに準拠した形式で返してください。

            営業担当者情報：
            - 名前：{sales_persona.name}
            - 所属：{self.bank_metadata.bank_name} {self.bank_metadata.branch}
            - 経験年数：{sales_persona.experience_level.value}
            - 性格特性：{", ".join([t.value for t in sales_persona.personality_traits])}

            企業情報：
            - 企業名：{company_persona.name}
            - 業種：{company_persona.industry}
            - 事業内容：{company_persona.business_description}
            - 担当者特性：{", ".join([t.value for t in company_persona.personality_traits])}

            営業活動日：{current_visit_date.strftime("%Y年%m月%d日")}

            初回のメールであることを考慮し、適切な挨拶と自己紹介を含めてください。
            """
        else:
            # 前回のやり取りから商品提案の進捗状況を抽出
            previous_products = []
            previous_status = None
            if session_history:
                for history in session_history:
                    if history.product_type:
                        previous_products.append(history.product_type)
                    if history.success_score is not None:
                        previous_status = (
                            "前向き"
                            if history.success_score >= 0.7
                            else "検討中"
                            if history.success_score >= 0.4
                            else "消極的"
                        )

            initial_greeting_prompt = f"""
            以下の情報に基づいて、営業担当者として企業担当者に送るメールを生成してください。
            メールは必ず指定されたJSONスキーマに準拠した形式で返してください。

            営業担当者情報：
            - 名前：{sales_persona.name}
            - 所属：{self.bank_metadata.bank_name} {self.bank_metadata.branch}
            - 経験年数：{sales_persona.experience_level.value}
            - 性格特性：{", ".join([t.value for t in sales_persona.personality_traits])}

            企業情報：
            - 企業名：{company_persona.name}
            - 業種：{company_persona.industry}
            - 事業内容：{company_persona.business_description}
            - 担当者特性：{", ".join([t.value for t in company_persona.personality_traits])}

            営業活動日：{current_visit_date.strftime("%Y年%m月%d日")}

            前回のやり取りの状況：
            - 提案した商品：{", ".join([p.value for p in previous_products]) if previous_products else "なし"}
            - 企業様の反応：{previous_status if previous_status else "不明"}

            前回のやり取りを踏まえて、適切なフォローアップと新たな提案を行ってください。
            前回の提案に対する企業様の反応を考慮し、必要に応じて提案内容を調整してください。
            """

        try:
            initial_email = self.openai_client.call_structured_api(
                [{"role": "user", "content": initial_greeting_prompt}],
                response_model=EmailMessage,
                temperature=0.3,
            )
            initial_email.sender = sales_persona.name
            initial_email.recipient = company_persona.name
            session_history.append(
                SessionHistory(
                    role="assistant",
                    content=initial_email.format_as_email(),
                    product_type=initial_email.product_type,
                    success_score=initial_email.success_score,
                )
            )
        except Exception as e:
            print(f"Error generating initial email: {e}")
            # エラー時はデフォルトのメールを使用
            if session_num == 1:
                default_email = EmailMessage(
                    subject="ご挨拶と今後のご提案について",
                    body=f"""
                    {company_persona.name} 御中

                    平素より大変お世話になっております。
                    {self.bank_metadata.bank_name} {self.bank_metadata.branch}の{sales_persona.name}と申します。

                    この度は貴社のご発展を心よりお慶び申し上げます。
                    つきましては、貴社のご要望に沿った金融商品のご提案をさせていただきたく、
                    ご連絡させていただきました。

                    貴社のご要望やご質問がございましたら、メールにて承りますので、
                    お気軽にご連絡ください。

                    何卒よろしくお願い申し上げます。
                    """,
                    sender=sales_persona.name,
                    recipient=company_persona.name,
                )
            else:
                default_email = EmailMessage(
                    subject="前回のご提案についてのフォローアップ",
                    body=f"""
                    {company_persona.name} 御中

                    平素より大変お世話になっております。
                    {self.bank_metadata.bank_name} {self.bank_metadata.branch}の{sales_persona.name}でございます。

                    前回のご提案について、ご検討いただきありがとうございます。
                    この度は、前回のご提案内容を踏まえまして、より具体的なご提案をさせていただきたく、
                    ご連絡させていただきました。

                    ご質問やご要望がございましたら、メールにて承りますので、
                    お気軽にご連絡ください。

                    何卒よろしくお願い申し上げます。
                    """,
                    sender=sales_persona.name,
                    recipient=company_persona.name,
                )
            session_history.append(
                SessionHistory(
                    role="assistant",
                    content=default_email.format_as_email(),
                )
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
                # 営業担当者からのメールを生成
                sales_email_prompt = f"""
                以下の会話履歴に基づいて、営業担当者として企業担当者に送るメールを生成してください。
                メールは必ず指定されたJSONスキーマに準拠した形式で返してください。

                営業担当者情報：
                - 名前：{sales_persona.name}
                - 所属：{self.bank_metadata.bank_name} {self.bank_metadata.branch}
                - 経験年数：{sales_persona.experience_level.value}
                - 性格特性：{", ".join([t.value for t in sales_persona.personality_traits])}

                企業情報：
                - 企業名：{company_persona.name}
                - 業種：{company_persona.industry}
                - 事業内容：{company_persona.business_description}
                - 担当者特性：{", ".join([t.value for t in company_persona.personality_traits])}

                会話履歴：
                {[h.content for h in session_history]}
                """

                try:
                    sales_email = self.openai_client.call_structured_api(
                        [{"role": "user", "content": sales_email_prompt}],
                        response_model=EmailMessage,
                        temperature=0.3,
                    )
                    sales_email.sender = sales_persona.name
                    sales_email.recipient = company_persona.name

                    # 提案内容の分析
                    analysis_messages = [
                        {
                            "role": "system",
                            "content": """
                            以下の営業提案を分析し、企業の反応を予測してください。
                            分析結果は必ず指定されたJSONスキーマに準拠した形式で返してください。
                            """,
                        },
                        {
                            "role": "user",
                            "content": f"""
                            提案内容：
                            {sales_email.body}

                            企業情報：
                            {company_persona.model_dump_json()}

                            前回のやり取り：
                            {[h.content for h in session_history]}

                            前回のやり取りを踏まえて、以下の点を分析してください：
                            - 今回の提案が前回のやり取りとどのように関連しているか
                            - 企業の反応が前回のやり取りからどのように変化しているか
                            - 提案の進捗状況と今後の見通し
                            """,
                        },
                    ]

                    analysis_data = self.openai_client.call_structured_api(
                        analysis_messages,
                        response_model=ProposalAnalysis,
                        temperature=0.3,
                    )

                    sales_email.product_type = analysis_data.product_type
                    sales_email.success_score = (
                        analysis_data.success_score
                        * sales_persona.calculate_success_rate()
                    )

                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=sales_email.format_as_email(),
                            product_type=sales_email.product_type,
                            success_score=sales_email.success_score,
                        )
                    )

                    if sales_email.success_score >= self.config.min_success_score:
                        matched_products.append(sales_email.product_type)
                        final_status = SalesStatus.SUCCESS
                    elif sales_email.success_score < 0.4:
                        final_status = SalesStatus.FAILED
                    else:
                        final_status = SalesStatus.PENDING

                    attempts += 1

                except Exception as e:
                    print(f"Error generating sales email: {e}")
                    final_status = SalesStatus.PENDING
                    attempts += 1

                current_role = "customer"
            else:
                # 企業担当者からのメールを生成
                customer_email_prompt = f"""
                以下の情報に基づいて、企業担当者として営業担当者に送るメールを生成してください。
                メールは必ず指定されたJSONスキーマに準拠した形式で返してください。

                企業情報：
                - 企業名：{company_persona.name}
                - 業種：{company_persona.industry}
                - 事業内容：{company_persona.business_description}
                - 担当者特性：{", ".join([t.value for t in company_persona.personality_traits])}
                - 意思決定スタイル：{company_persona.decision_making_style}
                - リスク許容度：{company_persona.risk_tolerance}
                - 金融リテラシー：{company_persona.financial_literacy}

                営業担当者情報：
                - 名前：{sales_persona.name}
                - 所属：{self.bank_metadata.bank_name} {self.bank_metadata.branch}
                - 経験年数：{sales_persona.experience_level.value}
                - 性格特性：{", ".join([t.value for t in sales_persona.personality_traits])}

                会話履歴：
                {[h.content for h in session_history]}

                前回のやり取りを踏まえて、適切な返信を行ってください。
                営業担当者の提案に対する反応は、あなたの性格特性、意思決定スタイル、リスク許容度、金融リテラシーを反映してください。
                すべてのやり取りはメールのみで完結させ、訪問や面談に関する言及は避けてください。
                メールでの質問や要望は十分に詳細に行ってください。
                """

                try:
                    customer_email = self.openai_client.call_structured_api(
                        [{"role": "user", "content": customer_email_prompt}],
                        response_model=EmailMessage,
                        temperature=0.3,
                    )
                    customer_email.sender = company_persona.name
                    customer_email.recipient = sales_persona.name

                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=customer_email.format_as_email(),
                        )
                    )
                except Exception as e:
                    print(f"Error generating customer email: {e}")
                    # エラー時はデフォルトのメールを使用
                    default_customer_email = EmailMessage(
                        subject="ご提案について",
                        body=f"""
                        {sales_persona.name} 様

                        ご連絡ありがとうございます。
                        ご提案いただいた内容について、社内で検討させていただきます。

                        何卒よろしくお願い申し上げます。
                        """,
                        sender=company_persona.name,
                        recipient=sales_persona.name,
                    )
                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=default_customer_email.format_as_email(),
                        )
                    )

                current_role = "sales"

        history_dicts = [h.to_dict() for h in session_history]

        return SessionSummary(
            session_num=session_num,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            visit_date=current_visit_date.strftime("%Y-%m-%d"),
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
        # メールの履歴から訪問内容を抽出
        email_history = []
        for history in session_summary.history:
            if "件名:" in history.content:
                email_history.append(history.content)

        # 営業担当者目線での報告書生成用プロンプト
        report_prompt = f"""
        訪問先：{company_persona.name}
        訪問日：{session_summary.visit_date}
        訪問回数：{session_summary.session_num}回目

        メールのやり取り：
        {chr(10).join(email_history)}

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
