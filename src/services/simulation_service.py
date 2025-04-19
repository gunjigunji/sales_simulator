import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, ValidationError

from src.models.evaluation import EvaluationResult
from src.models.persona import (
    Assignment,
    CompanyPersona,
    CustomerPersonalityTrait,
    EmailMessage,
    EvaluationCriteria,
    ExperienceLevel,
    MeetingLog,
    NegotiationStage,
    PersonalityTrait,
    ProductType,
    Proposal,
    ResponseType,
    SalesPersona,
    SalesProgress,
    SalesStatus,
    SessionHistory,
    SessionSummary,
    SimulationResult,
)
from src.models.proposal_analysis import ProposalAnalysis
from src.models.settings import BankMetadata, Prompts, SimulationConfig
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
        # 企業担当者の情報が存在することを確認
        if not company_persona.contact_person:
            raise ValueError(
                f"企業担当者の情報が設定されていません: {company_persona.name}"
            )

        session_history = []
        current_visit_date = visit_date or datetime.now()

        # 会話コンテキストの更新
        company_persona.conversation_context.last_contact_date = current_visit_date
        company_persona.conversation_context.cleanup_old_records(
            retention_visits=self.config.memory_retention_visits
        )

        if prev_history:
            prev_summary = f"""
            前回の訪問内容：
            {prev_history}
            ...
            """
            session_history.append(SessionHistory(role="system", content=prev_summary))

        # 商談進捗の更新
        self._update_negotiation_stage(company_persona, session_num)

        # 初回と2回目以降でプロンプトを分岐
        if session_num == 1:
            initial_greeting_prompt = self._create_initial_greeting_prompt(
                sales_persona, company_persona, current_visit_date
            )
        else:
            initial_greeting_prompt = self._create_followup_greeting_prompt(
                sales_persona, company_persona, current_visit_date, session_history
            )

        try:
            initial_email = self._generate_email_message(
                initial_greeting_prompt, sales_persona, company_persona
            )

            # 提案内容の評価と応答タイプの決定
            evaluation_result = self._evaluate_proposal_and_determine_response(
                company_persona, initial_email
            )

            session_history.append(
                SessionHistory(
                    role="assistant",
                    content=initial_email.format_as_email(),
                    product_type=initial_email.product_type,
                    success_score=evaluation_result.scores.get(
                        EvaluationCriteria.BENEFIT.value, 0.5
                    ),
                )
            )

            # 会話コンテキストの更新
            self._update_conversation_context(
                company_persona, initial_email, evaluation_result
            )

        except Exception as e:
            print(f"Error generating initial email: {e}")
            initial_email = self._create_default_email(
                sales_persona, company_persona, session_num
            )
            session_history.append(
                SessionHistory(
                    role="assistant",
                    content=initial_email.format_as_email(),
                )
            )

        current_role = "customer"
        attempts = 1
        matched_products = []
        current_status = SalesStatus.IN_PROGRESS

        while (
            attempts <= self.config.num_turns_per_visit
            and current_status == SalesStatus.IN_PROGRESS
        ):
            if current_role == "sales":
                try:
                    sales_email = self._generate_sales_email(
                        sales_persona, company_persona, session_history, attempts
                    )

                    evaluation_result = self._evaluate_proposal_and_determine_response(
                        company_persona, sales_email
                    )

                    if evaluation_result.decision == "success":
                        matched_products.append(sales_email.product_type)

                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=sales_email.format_as_email(),
                            product_type=sales_email.product_type,
                            success_score=evaluation_result.scores.get(
                                EvaluationCriteria.BENEFIT.value, 0.5
                            ),
                        )
                    )

                    self._update_conversation_context(
                        company_persona, sales_email, evaluation_result
                    )

                except Exception as e:
                    print(f"Error generating sales email: {e}")
                    attempts += 1
                    continue

                current_role = "customer"
            else:
                try:
                    customer_email = self._generate_customer_email(
                        company_persona, sales_persona, session_history, attempts
                    )

                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=customer_email.format_as_email(),
                        )
                    )

                except Exception as e:
                    print(f"Error generating customer email: {e}")
                    customer_email = self._create_default_customer_email(
                        company_persona, sales_persona
                    )
                    session_history.append(
                        SessionHistory(
                            role="assistant",
                            content=customer_email.format_as_email(),
                        )
                    )

                current_role = "sales"
                attempts += 1

                # 応答タイプに基づいてステータスを更新
                current_status = self._determine_current_status(
                    company_persona, customer_email
                )

        # 最終的なステータスを判定
        final_status = self._determine_final_status(
            current_status, matched_products, company_persona
        )

        history_dicts = [h.to_dict() for h in session_history]

        return SessionSummary(
            session_num=session_num,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            visit_date=current_visit_date.strftime("%Y-%m-%d"),
            history=history_dicts,
            final_status=final_status,
            matched_products=matched_products,
        )

    def _update_negotiation_stage(
        self, company_persona: CompanyPersona, session_num: int
    ) -> None:
        """商談進捗のステージを更新"""
        if session_num == 1:
            company_persona.negotiation_progress.update_stage(NegotiationStage.INITIAL)
        elif company_persona.negotiation_progress.stage == NegotiationStage.INITIAL:
            company_persona.negotiation_progress.update_stage(
                NegotiationStage.INFORMATION_GATHERING
            )
        elif len(company_persona.negotiation_progress.required_information) == 0:
            if (
                company_persona.negotiation_progress.stage
                == NegotiationStage.INFORMATION_GATHERING
            ):
                company_persona.negotiation_progress.update_stage(
                    NegotiationStage.DETAILED_REVIEW
                )
            elif (
                company_persona.negotiation_progress.stage
                == NegotiationStage.DETAILED_REVIEW
                and company_persona.current_interest_score.score >= 80.0
            ):
                company_persona.negotiation_progress.update_stage(
                    NegotiationStage.FINAL_EVALUATION
                )

    def _evaluate_proposal_and_determine_response(
        self, company_persona: CompanyPersona, email: EmailMessage
    ) -> EvaluationResult:
        """提案を評価し応答タイプを決定"""
        proposal = Proposal(
            product_type=email.product_type or ProductType.OTHER,
            terms={},
            benefits=[],
            risks=[],
            cost_information={},
            support_details={},
            track_record=[],
        )

        evaluation = company_persona.evaluate_proposal(proposal)

        # 興味度スコアの更新
        interest_score = company_persona.calculate_interest_score(
            email.body, email.product_type
        )
        company_persona.current_interest_score = interest_score
        company_persona.conversation_context.interest_history.append(interest_score)

        return evaluation

    def _update_conversation_context(
        self,
        company_persona: CompanyPersona,
        email: EmailMessage,
        evaluation: EvaluationResult,
    ) -> None:
        """会話コンテキストを更新"""
        if email.product_type:
            company_persona.conversation_context.add_product_discussion(
                email.product_type
            )

        # メール内容から話題を抽出して追加
        topics = self._extract_topics_from_email(email)
        for topic in topics:
            company_persona.conversation_context.add_topic(topic)

        # 約束事項を抽出して追加
        actions = self._extract_actions_from_email(email)
        for action in actions:
            company_persona.conversation_context.add_action(action)

        # 評価結果に基づく懸念事項の更新
        for concern in evaluation.concerns:
            company_persona.negotiation_progress.add_concern(concern)

        # 必要な追加情報の更新
        if evaluation.required_info:
            company_persona.negotiation_progress.required_information = (
                evaluation.required_info
            )

    def _determine_current_status(
        self, company_persona: CompanyPersona, email: EmailMessage
    ) -> SalesStatus:
        """現在のステータスを判定"""
        response_type = company_persona.determine_response_type(
            company_persona.current_interest_score
        )

        if response_type == ResponseType.ACCEPTANCE:
            return SalesStatus.SUCCESS
        elif response_type == ResponseType.REJECTION:
            return SalesStatus.FAILED
        else:
            return SalesStatus.IN_PROGRESS

    def _determine_final_status(
        self,
        current_status: SalesStatus,
        matched_products: List[ProductType],
        company_persona: CompanyPersona,
    ) -> SalesStatus:
        """最終的なステータスを判定"""
        # 商品がマッチしていない場合は成功としない
        if not matched_products:
            if (
                current_status == SalesStatus.FAILED
                or company_persona.current_interest_score.score < 20.0
            ):
                return SalesStatus.FAILED
            return SalesStatus.PENDING

        # 商品がマッチしている場合
        if current_status == SalesStatus.SUCCESS and matched_products:
            return SalesStatus.SUCCESS
        elif current_status == SalesStatus.FAILED:
            return SalesStatus.FAILED
        else:
            return SalesStatus.PENDING

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

        企業担当者情報：
        - 名前：{company_persona.contact_person.name}
        - 役職：{company_persona.contact_person.position}
        - 年齢：{company_persona.contact_person.age}
        - 入社年数：{company_persona.contact_person.years_in_company}
        - 性格特性：{", ".join([t.value for t in company_persona.contact_person.personality_traits])}
        - 意思決定スタイル：{company_persona.contact_person.decision_making_style}
        - リスク許容度：{company_persona.contact_person.risk_tolerance}
        - 金融リテラシー：{company_persona.contact_person.financial_literacy}
        - コミュニケーションスタイル：{company_persona.contact_person.communication_style}
        - ストレス耐性：{company_persona.contact_person.stress_tolerance}
        - 適応力：{company_persona.contact_person.adaptability}

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

            # 進捗状況を更新（成功した商品と訪問回数のみ）
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

    def _create_initial_greeting_prompt(
        self,
        sales_persona: SalesPersona,
        company_persona: CompanyPersona,
        visit_date: datetime,
    ) -> str:
        """初回訪問時のプロンプトを作成"""
        return f"""
        あなたは以下の特性を持つ銀行の営業担当者として、初回のメールを作成してください：

        営業担当者情報：
        - 名前：{sales_persona.name}
        - 経験：{sales_persona.experience_level.value}
        - 性格：{", ".join([trait.value for trait in sales_persona.personality_traits])}
        - 得意分野：{", ".join(sales_persona.specialties)}

        企業情報：
        - 企業名：{company_persona.name}
        - 業種：{company_persona.industry}
        - 事業内容：{company_persona.business_description}
        - 資金ニーズ：{company_persona.financial_needs}
        
        企業担当者情報：
        - 名前：{company_persona.contact_person.name if company_persona.contact_person else "不明"}
        - 役職：{company_persona.contact_person.position if company_persona.contact_person else "不明"}

        以下の点に注意してメールを作成してください：
        1. 初回訪問であることを意識した内容にする
        2. 企業の事業内容や資金ニーズに言及する
        3. 具体的な商品提案は控えめにし、まずは関係構築を重視する
        4. 企業担当者の性格特性に合わせたトーンで書く
        5. メールは必ず以下の形式で記載する：

        件名: [ここに件名]
        送信者: {sales_persona.name}
        受信者: {company_persona.contact_person.name if company_persona.contact_person else "ご担当者様"}
        日時: {visit_date.strftime("%Y-%m-%d %H:%M:%S")}

        [ここに本文]
        """

    def _create_followup_greeting_prompt(
        self,
        sales_persona: SalesPersona,
        company_persona: CompanyPersona,
        visit_date: datetime,
        session_history: List[SessionHistory],
    ) -> str:
        """フォローアップ訪問時のプロンプトを作成"""
        # 直近の会話履歴を取得
        recent_history = "\n".join(
            [
                f"{h.role}: {h.content}"
                for h in session_history[-3:]
                if h.role != "system"
            ]
        )

        # 商談進捗状況
        negotiation_stage = company_persona.negotiation_progress.stage.value
        key_concerns = (
            ", ".join(company_persona.negotiation_progress.key_concerns) or "特になし"
        )
        required_info = (
            ", ".join(company_persona.negotiation_progress.required_information)
            or "特になし"
        )

        return f"""
        あなたは以下の特性を持つ銀行の営業担当者として、フォローアップのメールを作成してください：

        営業担当者情報：
        - 名前：{sales_persona.name}
        - 経験：{sales_persona.experience_level.value}
        - 性格：{", ".join([trait.value for trait in sales_persona.personality_traits])}
        - 得意分野：{", ".join(sales_persona.specialties)}

        企業情報：
        - 企業名：{company_persona.name}
        - 業種：{company_persona.industry}
        - 資金ニーズ：{company_persona.financial_needs}
        
        商談状況：
        - 商談ステージ：{negotiation_stage}
        - 主な懸念事項：{key_concerns}
        - 必要な追加情報：{required_info}
        - 現在の興味度：{company_persona.current_interest_score.score:.1f}

        直近の会話履歴：
        {recent_history}

        以下の点に注意してメールを作成してください：
        1. 前回までの会話内容を踏まえた内容にする
        2. 商談ステージに応じた適切な提案や質問を行う
        3. 懸念事項や必要な情報に関する確認を含める
        4. 企業担当者の反応に基づいて提案内容を調整する
        5. メールは必ず以下の形式で記載する：

        件名: [ここに件名]
        送信者: {sales_persona.name}
        受信者: {company_persona.contact_person.name if company_persona.contact_person else "ご担当者様"}
        日時: {visit_date.strftime("%Y-%m-%d %H:%M:%S")}

        [ここに本文]
        """

    def _generate_email_message(
        self,
        prompt: str,
        sales_persona: SalesPersona,
        company_persona: CompanyPersona,
    ) -> EmailMessage:
        """プロンプトに基づいてメールメッセージを生成"""
        try:
            messages = [
                {"role": "system", "content": self.prompts.system_prompt_sales_bank},
                {"role": "user", "content": prompt},
            ]

            response = self.openai_client.call_chat_api(messages)

            # メール形式の応答をパース
            lines = response.strip().split("\n")
            subject = ""
            sender = ""
            recipient = ""
            date = ""
            body = []
            header_section = True

            for line in lines:
                line = line.strip()
                if not line and header_section:
                    header_section = False
                    continue

                if header_section:
                    if line.startswith("件名:"):
                        subject = line.replace("件名:", "").strip()
                    elif line.startswith("送信者:"):
                        sender = line.replace("送信者:", "").strip()
                    elif line.startswith("受信者:"):
                        recipient = line.replace("受信者:", "").strip()
                    elif line.startswith("日時:"):
                        date = line.replace("日時:", "").strip()
                else:
                    body.append(line)

            return EmailMessage(
                subject=subject,
                body="\n".join(body),
                sender=sender,
                recipient=recipient,
                date=date,
            )

        except Exception as e:
            print(f"Error generating email message: {e}")
            return self._create_default_email(sales_persona, company_persona)

    def _create_default_email(
        self,
        sales_persona: SalesPersona,
        company_persona: CompanyPersona,
        session_num: int = 1,
    ) -> EmailMessage:
        """デフォルトのメールメッセージを作成"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if session_num == 1:
            subject = (
                f"初回のご挨拶 - {sales_persona.name}（{self.bank_metadata.bank_name}）"
            )
            body = f"""
{company_persona.contact_person.name if company_persona.contact_person else "ご担当者様"}

{self.bank_metadata.bank_name} {self.bank_metadata.branch}の{sales_persona.name}でございます。

この度は、お客様の事業についてお話をさせていただく機会をいただき、誠にありがとうございます。
弊行では、お客様の事業発展のお手伝いができればと考えております。

お客様のご要望やご不明な点などございましたら、お気軽にご相談いただけますと幸いです。

今後ともよろしくお願い申し上げます。

{sales_persona.name}
{self.bank_metadata.bank_name} {self.bank_metadata.branch}
"""
        else:
            subject = f"ご提案のご相談 - {sales_persona.name}（{self.bank_metadata.bank_name}）"
            body = f"""
{company_persona.contact_person.name if company_persona.contact_person else "ご担当者様"}

{self.bank_metadata.bank_name} {self.bank_metadata.branch}の{sales_persona.name}でございます。

前回のご連絡に引き続き、お客様のニーズに合わせた提案をさせていただければと存じます。

ご多忙のところ恐縮ではございますが、ご検討いただけますと幸いです。

今後ともよろしくお願い申し上げます。

{sales_persona.name}
{self.bank_metadata.bank_name} {self.bank_metadata.branch}
"""

        return EmailMessage(
            subject=subject,
            body=body,
            sender=sales_persona.name,
            recipient=company_persona.contact_person.name
            if company_persona.contact_person
            else "ご担当者様",
            date=current_time,
        )

    def _generate_customer_email(
        self,
        company_persona: CompanyPersona,
        sales_persona: SalesPersona,
        session_history: List[SessionHistory],
        attempts: int,
    ) -> EmailMessage:
        """企業担当者からのメールを生成"""
        try:
            # 直近の会話履歴を取得
            recent_history = "\n".join(
                [
                    f"{h.role}: {h.content}"
                    for h in session_history[-3:]
                    if h.role != "system"
                ]
            )

            prompt = f"""
企業情報：
- 企業名：{company_persona.name}
- 業種：{company_persona.industry}
- 事業内容：{company_persona.business_description}
- 資金ニーズ：{company_persona.financial_needs}

企業担当者情報：
- 名前：{company_persona.contact_person.name if company_persona.contact_person else "不明"}
- 役職：{company_persona.contact_person.position if company_persona.contact_person else "不明"}
- 性格：{", ".join([trait.value for trait in company_persona.personality_traits])}
- 意思決定スタイル：{company_persona.decision_making_style}

直近の会話履歴：
{recent_history}

以下の点に注意してメールを作成してください：
1. 企業担当者の立場から返信を作成
2. 性格特性と意思決定スタイルを反映
3. 企業の状況やニーズを踏まえた内容
4. メールは必ず以下の形式で記載：

件名: [ここに件名]
送信者: {company_persona.contact_person.name if company_persona.contact_person else "ご担当者"}
受信者: {sales_persona.name}
日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

[ここに本文]
"""

            messages = [
                {"role": "system", "content": self.prompts.system_prompt_customer_bank},
                {"role": "user", "content": prompt},
            ]

            response = self.openai_client.call_chat_api(messages)

            # メール形式の応答をパース
            lines = response.strip().split("\n")
            subject = ""
            sender = ""
            recipient = ""
            date = ""
            body = []
            header_section = True

            for line in lines:
                line = line.strip()
                if not line and header_section:
                    header_section = False
                    continue

                if header_section:
                    if line.startswith("件名:"):
                        subject = line.replace("件名:", "").strip()
                    elif line.startswith("送信者:"):
                        sender = line.replace("送信者:", "").strip()
                    elif line.startswith("受信者:"):
                        recipient = line.replace("受信者:", "").strip()
                    elif line.startswith("日時:"):
                        date = line.replace("日時:", "").strip()
                else:
                    body.append(line)

            return EmailMessage(
                subject=subject,
                body="\n".join(body),
                sender=sender,
                recipient=recipient,
                date=date,
            )

        except Exception as e:
            print(f"Error generating customer email: {e}")
            return self._create_default_customer_email(company_persona, sales_persona)

    def _create_default_customer_email(
        self,
        company_persona: CompanyPersona,
        sales_persona: SalesPersona,
    ) -> EmailMessage:
        """デフォルトの企業担当者からのメールを作成"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subject = f"Re: ご提案について"
        body = f"""
{sales_persona.name}様

お世話になっております。
{company_persona.name}の{company_persona.contact_person.name if company_persona.contact_person else "担当者"}でございます。

ご提案ありがとうございます。
内容を確認させていただき、検討させていただきます。

何かございましたら、改めてご連絡させていただきます。

よろしくお願いいたします。

{company_persona.contact_person.name if company_persona.contact_person else "担当者"}
{company_persona.name}
"""

        return EmailMessage(
            subject=subject,
            body=body,
            sender=company_persona.contact_person.name
            if company_persona.contact_person
            else "担当者",
            recipient=sales_persona.name,
            date=current_time,
        )

    def _generate_sales_email(
        self,
        sales_persona: SalesPersona,
        company_persona: CompanyPersona,
        session_history: List[SessionHistory],
        attempts: int,
    ) -> EmailMessage:
        """営業担当者からのメールを生成"""
        try:
            # 直近の会話履歴を取得
            recent_history = "\n".join(
                [
                    f"{h.role}: {h.content}"
                    for h in session_history[-3:]
                    if h.role != "system"
                ]
            )

            prompt = f"""
営業担当者情報：
- 名前：{sales_persona.name}
- 経験：{sales_persona.experience_level.value}
- 性格：{", ".join([trait.value for trait in sales_persona.personality_traits])}
- 得意分野：{", ".join(sales_persona.specialties)}

企業情報：
- 企業名：{company_persona.name}
- 業種：{company_persona.industry}
- 資金ニーズ：{company_persona.financial_needs}

直近の会話履歴：
{recent_history}

以下の点に注意してメールを作成してください：
1. 営業担当者の経験と性格特性を反映
2. 企業の状況やニーズに合わせた提案
3. 前回までの会話を踏まえた内容
4. メールは必ず以下の形式で記載：

件名: [ここに件名]
送信者: {sales_persona.name}
受信者: {company_persona.contact_person.name if company_persona.contact_person else "ご担当者様"}
日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

[ここに本文]
"""

            messages = [
                {"role": "system", "content": self.prompts.system_prompt_sales_bank},
                {"role": "user", "content": prompt},
            ]

            response = self.openai_client.call_chat_api(messages)

            # メール形式の応答をパース
            lines = response.strip().split("\n")
            subject = ""
            sender = ""
            recipient = ""
            date = ""
            body = []
            header_section = True

            for line in lines:
                line = line.strip()
                if not line and header_section:
                    header_section = False
                    continue

                if header_section:
                    if line.startswith("件名:"):
                        subject = line.replace("件名:", "").strip()
                    elif line.startswith("送信者:"):
                        sender = line.replace("送信者:", "").strip()
                    elif line.startswith("受信者:"):
                        recipient = line.replace("受信者:", "").strip()
                    elif line.startswith("日時:"):
                        date = line.replace("日時:", "").strip()
                else:
                    body.append(line)

            return EmailMessage(
                subject=subject,
                body="\n".join(body),
                sender=sender,
                recipient=recipient,
                date=date,
            )

        except Exception as e:
            print(f"Error generating sales email: {e}")
            return self._create_default_email(sales_persona, company_persona)

    def _extract_topics_from_email(self, email: EmailMessage) -> List[str]:
        """メール内容から話題を抽出"""
        try:
            prompt = f"""
            以下のメール内容から主要な話題を抽出してください。
            箇条書きで3つまで抽出してください。

            メール内容：
            {email.body}
            """

            messages = [
                {
                    "role": "system",
                    "content": "あなたはメール内容から主要な話題を抽出する専門家です。",
                },
                {"role": "user", "content": prompt},
            ]

            response = self.openai_client.call_chat_api(
                messages, temperature=0.3, max_tokens=200
            )

            # 箇条書きの応答を行ごとに分割し、先頭の記号を削除
            topics = [
                line.strip().lstrip("・-*").strip()
                for line in response.split("\n")
                if line.strip() and any(c.isalnum() for c in line)
            ]

            return topics[:3]  # 最大3つまでの話題を返す

        except Exception as e:
            print(f"Error extracting topics from email: {e}")
            return []

    def _extract_actions_from_email(self, email: EmailMessage) -> List[str]:
        """メール内容から約束事項を抽出"""
        try:
            prompt = f"""
            以下のメール内容から約束事項や次のアクションを抽出してください。
            箇条書きで3つまで抽出してください。
            期限や具体的な行動が含まれているものを優先してください。

            メール内容：
            {email.body}
            """

            messages = [
                {
                    "role": "system",
                    "content": "あなたはメール内容から約束事項やアクションアイテムを抽出する専門家です。",
                },
                {"role": "user", "content": prompt},
            ]

            response = self.openai_client.call_chat_api(
                messages, temperature=0.3, max_tokens=200
            )

            # 箇条書きの応答を行ごとに分割し、先頭の記号を削除
            actions = [
                line.strip().lstrip("・-*").strip()
                for line in response.split("\n")
                if line.strip() and any(c.isalnum() for c in line)
            ]

            return actions[:3]  # 最大3つまでのアクションを返す

        except Exception as e:
            print(f"Error extracting actions from email: {e}")
            return []
