
import os
import json
import random
import openai
from datetime import datetime

# APIキーの設定（環境変数などから取得してください）
openai.api_key = os.getenv("OPENAI_API_KEY")

def call_chat_api(messages, model="gpt-4.1", temperature=0.7, max_tokens=150):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message["content"].strip()

# ─────────────
# ペルソナ自動生成と担当割り当て
# ─────────────

def generate_personas(prompt, num_personas=3, model="gpt-4"):
    personas = []
    for i in range(num_personas):
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"ペルソナ{i+1}の情報を生成してください。"}
        ]
        persona = call_chat_api(messages, model=model, temperature=0.8, max_tokens=200)
        personas.append(persona)
    return personas

company_prompt = (
    "あなたは銀行の支店を表すペルソナを生成します。支店の名称、所在地、主な取扱い金融商品、"
    "経営理念や地域との連携など、具体的な情報を含むペルソナ情報を作成してください。"
)
sales_prompt = (
    "あなたは銀行の営業担当者のペルソナを生成します。担当エリア、営業実績、得意な金融商品、"
    "顧客対応の特徴など、詳細かつ個性的なペルソナ情報を作成してください。"
)

company_personas = generate_personas(company_prompt, num_personas=3)
sales_personas = generate_personas(sales_prompt, num_personas=3)

def assign_companies_to_sales(sales_personas, company_personas):
    assignments = []
    for sales in sales_personas:
        num_assigned = random.choice([1, 2])
        assigned_companies = random.sample(company_personas, k=num_assigned)
        assignments.append({
            "sales_persona": sales,
            "assigned_companies": assigned_companies
        })
    return assignments

assignments = assign_companies_to_sales(sales_personas, company_personas)

# ─────────────
# 銀行営業風のセッション毎の対話シミュレーション
# ─────────────

system_prompt_sales_bank = (
    "あなたは信頼と実績のある銀行の営業担当です。お客様に対して、最適な住宅ローンや投資商品のご提案を、"
    "豊富な実績と丁寧な説明で行います。"
)
system_prompt_customer_bank = (
    "あなたは銀行の顧客企業の担当者です。自社の資産運用や経営戦略を踏まえ、信頼性のある金融パートナーを求めています。"
)

def simulate_bank_conversation_session(sales_persona, company_persona, prev_history=None, session_num=1, num_turns=4):
    """
    1回の訪問（セッション）の対話シミュレーションを実施
    prev_history：前回セッションの要約など（文字列）
    session_num：訪問回数
    """
    session_history = []
    if prev_history:
        session_history.append({"role": "system", "content": f"【前回の振り返り】\n{prev_history}"})
    
    session_history.append({"role": "user", "content": "こんにちは。当行の住宅ローンや投資商品の詳細について教えていただけますか？"})
    current_role = "sales"
    
    for turn in range(num_turns):
        if current_role == "sales":
            messages = [{"role": "system", "content": system_prompt_sales_bank}]
            messages.append({"role": "assistant", "content": f"【営業担当ペルソナ】 {sales_persona}"})
            messages.extend(session_history)
            response = call_chat_api(messages)
            session_history.append({"role": "assistant", "content": response})
            current_role = "customer"
        else:
            messages = [{"role": "system", "content": system_prompt_customer_bank}]
            messages.append({"role": "assistant", "content": f"【企業ペルソナ】 {company_persona}"})
            messages.extend(session_history)
            user_question = "金利や返済プラン、その他サービスについてもう少し詳しく教えていただけますか？"
            messages.append({"role": "user", "content": user_question})
            response = call_chat_api(messages)
            session_history.append({"role": "assistant", "content": response})
            current_role = "sales"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_summary = f"【セッション{session_num} 終了時刻】 {timestamp}\n" + "\n".join(
        [f"{turn['role']}: {turn['content']}" for turn in session_history]
    )
    return session_summary

def record_bank_meeting_log(session_summary, sales_persona, company_persona, bank_meta, session_num):
    """
    1回の訪問セッションの対話記録と各ペルソナ情報、銀行情報を元に訪問記録を生成する
    """
    system_prompt_record_bank = (
        "あなたは銀行の渉外担当者です。以下は1回の訪問における対話記録、営業担当者のペルソナ、"
        "企業のペルソナ、及び銀行の基本情報です。これらを基に、本日の訪問報告書を作成してください。"
        "報告書には訪問日時、担当営業、担当企業、提供サービス、対話内容の概要および次回の提案内容を含め、"
        "分かりやすくまとめてください。"
    )
    
    sales_info = f"【営業担当ペルソナ】 {sales_persona}"
    company_info = f"【企業ペルソナ】 {company_persona}"
    bank_info_text = "\n".join([f"{key}: {value}" for key, value in bank_meta.items()])
    
    messages = [
        {"role": "system", "content": system_prompt_record_bank},
        {"role": "user", "content": f"【銀行情報】\n{bank_info_text}\n\n{sales_info}\n{company_info}\n\n【対話記録（セッション{session_num}）】\n{session_summary}"}
    ]
    record = call_chat_api(messages, max_tokens=300)
    return record

# ─────────────
# 複数回訪問のシミュレーション（各訪問毎に個別の訪問記録を生成）
# ─────────────

def simulate_time_series_visits(sales_persona, company_persona, num_visits=3, num_turns_per_visit=4):
    """
    複数回の訪問セッションをシミュレーション。各訪問ごとにセッションの対話記録と訪問記録を生成する。
    """
    session_logs = []
    meeting_logs = []  # 各訪問の個別記録を保存するリスト
    prev_summary = None
    for visit in range(1, num_visits + 1):
        print(f"\n=== 訪問セッション {visit} ===")
        session_summary = simulate_bank_conversation_session(
            sales_persona, company_persona, prev_history=prev_summary, session_num=visit, num_turns=num_turns_per_visit
        )
        session_logs.append(session_summary)
        # 個別訪問記録を生成
        meeting_log = record_bank_meeting_log(session_summary, sales_persona, company_persona, bank_metadata, session_num=visit)
        meeting_logs.append(meeting_log)
        print(f"\n[セッション {visit} の訪問記録]")
        print(meeting_log)
        # 次回の入力として直近セッションの要約を利用する
        prev_summary = session_summary
    return session_logs, meeting_logs

# 銀行基本情報
bank_metadata = {
    "bank_name": "みずほ銀行",
    "branch": "本店営業部",
    "location": "東京都千代田区",
    "services": "住宅ローン、投資信託、預金サービス等"
}

# ─────────────
# 各担当ペアごとに時系列シミュレーションと個別訪問記録の実行、保存
# ─────────────

all_meeting_records = []
for idx, assignment in enumerate(assignments, 1):
    sales_persona = assignment["sales_persona"]
    for comp_idx, company_persona in enumerate(assignment["assigned_companies"], 1):
        print(f"\n=== 営業マン{idx} と 企業ペルソナ【担当企業{comp_idx}】 の時系列訪問シミュレーション ===")
        session_logs, meeting_logs = simulate_time_series_visits(sales_persona, company_persona, num_visits=3, num_turns_per_visit=4)
        # 全セッションの記録（連結した対話履歴）
        full_history = "\n\n".join(session_logs)
        # 全体の訪問記録（各セッションの個別記録をまとめたもの）
        overall_meeting_log = "\n\n".join(meeting_logs)
        final_log = {
            "sales_persona": sales_persona,
            "company_persona": company_persona,
            "session_logs": session_logs,
            "individual_meeting_logs": meeting_logs,
            "overall_meeting_log": overall_meeting_log
        }
        all_meeting_records.append(final_log)

# すべての記録をJSON形式で保存
with open("bank_sales_time_series_records.json", "w", encoding="utf-8") as f:
    json.dump(all_meeting_records, f, ensure_ascii=False, indent=2)

print("\nすべての時系列訪問記録を bank_sales_time_series_records.json に保存しました。")
