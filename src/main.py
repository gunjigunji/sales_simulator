# %%
import json
import os
from datetime import datetime

from src.config.settings import (
    DEFAULT_BANK_METADATA,
    DEFAULT_PROMPTS,
    DEFAULT_SIMULATION_CONFIG,
)
from src.services.openai_client import OpenAIClient
from src.services.simulation_service import SimulationService


def ensure_output_directory():
    """出力ディレクトリが存在することを確認"""
    os.makedirs("data/output", exist_ok=True)


def save_results(results_dict, timestamp):
    """結果をJSONファイルとして保存"""
    output_file = f"data/output/bank_sales_time_series_records_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_dict, f, ensure_ascii=False, indent=2)
    return output_file


def format_conversation_history(history):
    """対話履歴を整形して返す"""
    formatted_history = []
    current_role = "営業担当"  # 最初のメールは必ず営業担当から

    for entry in history:
        # システムメッセージはスキップ
        if entry.role == "system":
            continue

        # メール形式のメッセージを処理
        if "件名:" in entry.content:
            # メールの本文を抽出
            content_lines = entry.content.split("\n")
            body_start = next(
                i for i, line in enumerate(content_lines) if line.strip() == ""
            )
            content = "\n".join(content_lines[body_start:]).strip()

            formatted_history.append({"role": current_role, "content": content})

            # 役割を交互に切り替え
            current_role = "企業担当" if current_role == "営業担当" else "営業担当"
        else:
            # 非メール形式のメッセージは従来通り処理
            if entry.role == "assistant":
                if formatted_history and formatted_history[-1]["role"] == "営業担当":
                    role = "企業担当"
                else:
                    role = "営業担当"
                formatted_history.append({"role": role, "content": entry.content})
            elif entry.role == "user":
                content = entry.content.strip()
                if content:
                    if (
                        formatted_history
                        and formatted_history[-1]["role"] == "営業担当"
                    ):
                        role = "企業担当"
                    else:
                        role = "営業担当"
                    formatted_history.append({"role": role, "content": content})

    return formatted_history


def main():
    # サービスの初期化
    openai_client = OpenAIClient(DEFAULT_SIMULATION_CONFIG)
    simulation_service = SimulationService(
        openai_client=openai_client,
        prompts=DEFAULT_PROMPTS,
        bank_metadata=DEFAULT_BANK_METADATA,
        config=DEFAULT_SIMULATION_CONFIG,
    )

    # ペルソナの生成
    print("ペルソナを生成中...")
    company_personas = simulation_service.generate_personas(
        DEFAULT_PROMPTS.company_prompt, "company"
    )
    sales_personas = simulation_service.generate_personas(
        DEFAULT_PROMPTS.sales_prompt, "sales"
    )

    # 担当割り当て
    print("担当割り当てを実施中...")
    assignments = simulation_service.assign_companies_to_sales(
        sales_personas, company_personas
    )

    # シミュレーションの実行
    print("シミュレーションを実行中...")
    all_results = []
    for idx, assignment in enumerate(assignments, 1):
        sales_persona = assignment.sales_persona
        for comp_idx, company_persona in enumerate(assignment.assigned_companies, 1):
            print(
                f"\n=== 営業マン{idx} と 企業ペルソナ【担当企業{comp_idx}】 の時系列訪問シミュレーション ==="
            )
            result = simulation_service.simulate_time_series_visits(
                sales_persona, company_persona
            )
            all_results.append(result)

    # 結果の保存
    print("結果を保存中...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ensure_output_directory()

    # 営業側と企業側の情報を含めたデータ構造
    results_dict = {
        "metadata": {
            "generated_at": timestamp,
            "bank_info": DEFAULT_BANK_METADATA.__dict__,
            "simulation_config": DEFAULT_SIMULATION_CONFIG.__dict__,
        },
        "personas": {
            "sales": [
                {
                    "id": persona.id,
                    "name": persona.name,
                    "age": persona.age,
                    "area": persona.area,
                    "experience_level": persona.experience_level.value,
                    "personality_traits": [
                        trait.value for trait in persona.personality_traits
                    ],
                    "achievements": persona.achievements,
                    "specialties": persona.specialties,
                    "characteristics": persona.characteristics,
                    "communication_style": persona.communication_style,
                    "stress_tolerance": persona.stress_tolerance,
                    "adaptability": persona.adaptability,
                    "product_knowledge": persona.product_knowledge,
                    "success_rate": persona.success_rate,
                }
                for persona in sales_personas
            ],
            "companies": [
                {
                    "id": persona.id,
                    "name": persona.name,
                    "location": persona.location,
                    "industry": persona.industry,
                    "business_description": persona.business_description,
                    "employee_count": persona.employee_count,
                    "annual_sales": persona.annual_sales,
                    "funding_status": persona.funding_status,
                    "future_plans": persona.future_plans,
                    "banking_relationships": persona.banking_relationships,
                    "financial_needs": persona.financial_needs,
                    "personality_traits": [
                        trait.value for trait in persona.personality_traits
                    ],
                    "decision_making_style": persona.decision_making_style,
                    "risk_tolerance": persona.risk_tolerance,
                    "financial_literacy": persona.financial_literacy,
                    "interest_products": {
                        product_type.value: score
                        for product_type, score in persona.interest_products.items()
                    },
                    "contact_person": {
                        "name": persona.contact_person.name,
                        "position": persona.contact_person.position,
                        "age": persona.contact_person.age,
                        "years_in_company": persona.contact_person.years_in_company,
                        "personality_traits": [
                            trait.value
                            for trait in persona.contact_person.personality_traits
                        ],
                        "decision_making_style": persona.contact_person.decision_making_style,
                        "risk_tolerance": persona.contact_person.risk_tolerance,
                        "financial_literacy": persona.contact_person.financial_literacy,
                        "communication_style": persona.contact_person.communication_style,
                        "stress_tolerance": persona.contact_person.stress_tolerance,
                        "adaptability": persona.contact_person.adaptability,
                    }
                    if persona.contact_person
                    else None,
                }
                for persona in company_personas
            ],
        },
        "assignments": [
            {
                "sales_persona_id": assignment.sales_persona.id,
                "assigned_company_ids": [
                    comp.id for comp in assignment.assigned_companies
                ],
            }
            for assignment in assignments
        ],
        "simulation_results": [
            {
                "sales_persona_id": result.sales_persona.id,
                "company_persona_id": result.company_persona.id,
                "sessions": [
                    {
                        "session_num": log.session_num,
                        "timestamp": log.timestamp,
                        "visit_date": log.visit_date,
                        "conversation": format_conversation_history(log.history),
                        "meeting_log": next(
                            (
                                ml.content
                                for ml in result.individual_meeting_logs
                                if ml.session_num == log.session_num
                            ),
                            None,
                        ),
                        "status": log.final_status,
                        "matched_products": [
                            product.value for product in log.matched_products
                        ],
                    }
                    for log in result.session_logs
                ],
                "overall_meeting_log": result.overall_meeting_log,
                "final_status": result.final_status,
                "matched_products": [
                    product.value for product in result.matched_products
                ],
            }
            for result in all_results
        ],
    }

    output_file = save_results(results_dict, timestamp)
    print(f"\nすべての時系列訪問記録を {output_file} に保存しました。")


if __name__ == "__main__":
    main()
