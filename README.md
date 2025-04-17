# 営業シミュレーションシステム

## 概要
営業担当役のAIエージェント（LLM）と訪問先企業役のAIエージェントとが対話することにより、実際の営業活動をシミュレートすることで営業活動記録の擬似データを作り出す。
各AIエージェントには自動生成されたペルソナが与えられており、多様な営業活動内容が生成される。

## システム構成
このシステムは以下の主要なコンポーネントで構成されています：

### 1. 設定管理（`src/config/settings.py`）
- `BankMetadata`: 銀行の基本情報（名称、支店、所在地、提供サービス）を管理
- `SimulationConfig`: シミュレーションの設定（訪問回数、対話回数、モデル設定など）
  - `num_personas`: 生成するペルソナの数
  - `num_visits`: 訪問回数
  - `num_turns_per_visit`: 1回の訪問での対話回数
  - `visit_interval_days`: 訪問間隔（日数）
  - `model`: 使用するAIモデル
  - `temperature`: 生成の多様性を制御するパラメータ
  - `max_tokens`: 生成する最大トークン数
  - `min_success_score`: 成功判定の閾値
  - `max_attempts_per_visit`: 1回の訪問での最大試行回数
- `Prompts`: 各AIエージェントのプロンプトテンプレートを管理
  - `company_prompt`: 企業ペルソナ生成用プロンプト
  - `sales_prompt`: 営業担当ペルソナ生成用プロンプト
  - `system_prompt_sales_bank`: 営業担当の対話用プロンプト
  - `system_prompt_customer_bank`: 企業担当の対話用プロンプト
  - `system_prompt_record_bank`: 訪問記録生成用プロンプト

### 2. ペルソナ管理（`src/models/persona.py`）
- `SalesPersona`: 営業担当者の属性
  - 基本情報（名前、年齢、担当エリア）
  - 営業実績
  - 得意分野
  - 特徴
  - 営業成功率
- `CompanyPersona`: 企業の属性
  - 基本情報（企業名、所在地、業種）
  - 事業内容
  - 規模（従業員数、売上）
  - 資金調達状況
  - 今後の計画
  - 金融機関との取引状況
  - 資金ニーズ
  - 商品への興味度
- `SalesStatus`: 営業活動の状態
  - `INITIAL`: 初回訪問前
  - `IN_PROGRESS`: 営業中
  - `SUCCESS`: 成約
  - `FAILED`: 断られた
  - `PENDING`: 検討中
- `ProductType`: 金融商品の種類
  - `LOAN`: 融資
  - `INVESTMENT`: 投資商品
  - `DEPOSIT`: 預金商品
  - `INSURANCE`: 保険商品
  - `OTHER`: その他

### 3. シミュレーションサービス（`src/services/simulation_service.py`）
- `SimulationService`: 営業シミュレーションの主要ロジックを実装
  - ペルソナの生成
    - 企業と営業担当のペルソナを自動生成
    - 各ペルソナに詳細な属性情報を設定
  - 担当割り当て
    - 営業担当者と企業のペアをランダムに割り当て
    - 1人の営業担当者に1-2社の企業を担当させる
  - 訪問セッションのシミュレーション
    - 複数回の訪問を時系列でシミュレーション
    - 各訪問で以下の要素を考慮：
      - 前回の訪問内容
      - 企業の状況変化
      - 商品提案の成功度
      - 対話の自然な流れ
  - 訪問記録の生成
    - 各訪問セッションの詳細な記録を生成
    - 訪問日時、担当者、企業情報、対話内容、提案内容などを含む

### 4. OpenAIクライアント（`src/services/openai_client.py`）
- `OpenAIClient`: OpenAI APIとの通信を管理
  - チャットAPIの呼び出し
  - エラーハンドリング
  - モデルパラメータの制御

### 5. メイン実行（`src/main.py`）
- シミュレーションの実行フローを管理
  - サービスの初期化
  - ペルソナの生成
  - 担当割り当て
  - シミュレーションの実行
  - 結果の保存
- 結果の保存と出力
  - JSON形式での保存
  - タイムスタンプ付きのファイル名

## 主要な機能

### ペルソナ生成
- 営業担当者と企業のペルソナを自動生成
- 各ペルソナには詳細な属性情報が設定される
- 企業ペルソナは以下の業種からランダムに生成：
  - 製造業（自動車部品、電子機器、食品加工など）
  - 小売業（スーパーマーケット、百貨店、専門店など）
  - サービス業（ITサービス、コンサルティング、教育など）
  - 建設業（建築、土木、設備工事など）
  - 運輸業（物流、運送、倉庫業など）
  - 不動産業（開発、賃貸、管理など）

### 担当割り当て
- 営業担当者と企業のペアをランダムに割り当て
- 1人の営業担当者に1-2社の企業を担当させる
- 割り当て結果はJSON形式で保存

### 訪問シミュレーション
- 複数回の訪問を時系列でシミュレーション
- 各訪問で以下の要素を考慮：
  - 前回の訪問内容
  - 企業の状況変化
  - 商品提案の成功度
  - 対話の自然な流れ
- 訪問間隔は設定可能（デフォルト30日）
- 1回の訪問での対話回数は設定可能（デフォルト8回）

### 訪問記録生成
- 各訪問セッションの詳細な記録を生成
- 訪問日時、担当者、企業情報、対話内容、提案内容などを含む
- 訪問記録は以下の情報を含む：
  - セッション番号
  - タイムスタンプ
  - 訪問日
  - 対話履歴
  - 最終ステータス
  - マッチした商品タイプ

## 出力データ
シミュレーション結果は以下の情報を含むJSONファイルとして保存されます：
- メタデータ
  - 生成日時
  - 銀行情報
  - シミュレーション設定
- ペルソナ情報
  - 営業担当者の詳細
  - 企業の詳細
- 担当割り当て情報
  - 営業担当者ID
  - 担当企業ID
- シミュレーション結果
  - 各訪問の詳細記録
  - 全体の訪問記録
  - 最終ステータス
  - マッチした商品

## 使用方法
1. 必要な環境変数の設定（OpenAI APIキーなど）
2. `src/main.py`を実行
3. 結果は`data/output/`ディレクトリに保存される

## 設定のカスタマイズ
`src/config/settings.py`で以下の設定を変更可能：
- 訪問回数（`num_visits`）
- 対話回数（`num_turns_per_visit`）
- 訪問間隔（`visit_interval_days`）
- AIモデルの選択（`model`）
- プロンプトのカスタマイズ
- 成功判定の閾値（`min_success_score`）
- 最大試行回数（`max_attempts_per_visit`）

## 注意事項
- OpenAI APIキーが必要です
- 生成されるデータは架空のものです
- シミュレーション結果は設定に依存します
- 大量のAPIコールが発生する可能性があります


