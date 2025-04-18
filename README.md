# 営業シミュレーションシステム

## 概要
営業担当役のAIエージェント（LLM）と企業担当役のAIエージェントとがメールでのやり取りを行うことにより、実際の営業活動をシミュレートすることで営業活動記録の擬似データを作り出す。
各AIエージェントには自動生成されたペルソナが与えられており、多様な営業活動内容が生成される。

## 処理の流れ
1. ペルソナの生成
   - OpenAI APIを使用して営業担当者と企業のペルソナを生成
   - 性格特性、経験、意思決定スタイルなどの属性を自動設定
   - 生成されたペルソナは一貫性のある行動を取るよう設計

2. 担当割り当て
   - 営業担当者と企業をランダムにマッチング
   - 1人の営業担当者に1-2社を担当させる
   - 割り当て結果はJSONで保存

3. メール交換シミュレーション
   - 設定された回数（デフォルト3回）のメール交換を実施
   - 各回で以下のステップを実行：
     a. 企業の状況を更新（売上、従業員数、ニーズなどの変動）
     b. 営業担当者が初回メールを作成
     c. 企業担当者が返信を生成
     d. 提案内容の評価と応答の決定
     e. 会話の進行と記録

4. 評価と判断
   - 各提案に対して多面的な評価を実施
   - 評価基準に基づいてスコアリング
   - 企業の特性に応じた判断を生成

5. 結果の保存
   - すべての情報をJSON形式で出力
   - 時系列での変化も記録

## システム構成
このシステムは以下の主要なコンポーネントで構成されています：

### 1. モデル定義
#### 設定モデル（`src/models/settings.py`）
- `BankMetadata`: 銀行の基本情報（名称、支店、所在地、提供サービス）を定義
- `SimulationConfig`: シミュレーションの設定を定義
  - `num_personas`: 生成するペルソナの数
  - `num_visits`: メール交換の回数
  - `num_turns_per_visit`: 1回のメール交換での対話回数
  - `visit_interval_days`: メール交換の間隔（日数）
  - `model`: 使用するAIモデル
  - `temperature`: 生成の多様性を制御するパラメータ（0.0-1.0）
    - 低い値：より一貫性のある出力
    - 高い値：より創造的な出力
  - `max_tokens`: 生成する最大トークン数
  - `min_success_score`: 成功判定の閾値（0.0-1.0）
  - `max_attempts_per_visit`: 1回のメール交換での最大試行回数
  - `interest_score_thresholds`: 興味度スコアの閾値設定
    - very_high: 80点以上で非常に興味あり
    - high: 60-79点で興味あり
    - moderate: 40-59点でやや興味あり
    - low: 20-39点であまり興味なし
  - `response_type_thresholds`: 応答タイプの閾値設定
    - acceptance: 80点以上で受諾
    - positive: 60点以上で前向き
    - question: 40点以上で質問
    - neutral: 20点以上で中立
  - `keyword_weights`: キーワードの重み付け設定
    - positive: ポジティブワードの重み（+5.0）
    - negative: ネガティブワードの重み（-5.0）
  - `memory_retention_visits`: 記憶として保持する訪問回数

#### ペルソナモデル（`src/models/persona.py`）
- `SalesPersona`: 営業担当者の属性
  - 基本情報（名前、年齢、担当エリア）
  - 経験レベル（4段階）
    - JUNIOR: 入社1-3年目（基本成功率0.7倍）
    - MIDDLE: 入社4-7年目（基本成功率0.85倍）
    - SENIOR: 入社8-15年目（基本成功率1.0倍）
    - VETERAN: 入社16年以上（基本成功率1.2倍）
  - 性格特性（複数選択）
    - 積極的: 成功率1.1倍
    - 慎重: 成功率0.9倍
    - 友好的: 成功率1.05倍
    - プロフェッショナル: 成功率1.15倍
    - 未熟: 成功率0.8倍
    - 知識豊富: 成功率1.1倍
    - せっかち: 成功率0.9倍
    - 忍耐強い: 成功率1.05倍
  - 営業実績: 過去の成功事例リスト
  - 得意分野: 得意な商品や顧客層
  - 特徴: 営業スタイルの特徴
  - 営業成功率: 経験と性格から計算（0.0-1.0）
  - コミュニケーションスタイル: メールの文体や対応方法
  - ストレス耐性: ストレス状況での対応力（0.0-1.0）
  - 適応力: 状況変化への対応力（0.0-1.0）
  - 商品知識: 商品理解度（0.0-1.0）

- `CompanyPersona`: 企業の属性
  - 基本情報
    - 企業名: 架空の企業名（○○株式会社形式は不可）
    - 所在地: 具体的な地域
    - 業種: 6業種から選択
  - 事業内容: 具体的な事業説明
  - 規模
    - 従業員数: 実数
    - 売上: ○○億円形式
  - 資金調達状況: 現在の資金調達方法
  - 今後の計画: 事業展開予定
  - 金融機関との取引状況: 現在の取引行
  - 資金ニーズ: 具体的な資金需要
  - 商品への興味度: 各商品タイプごとに0.0-1.0で設定
  - 性格特性（複数選択）
    - 高圧的: 対応の厳しさ
    - 協力的: 提案への受容性
    - 懐疑的: 慎重な判断
    - 信頼的: 関係構築の容易さ
    - 細かい: 詳細への注目
    - 大局的: 全体視点
    - 衝動的: 早い判断
    - 分析的: データ重視
  - 意思決定スタイル: 判断の特徴
  - リスク許容度: リスクへの態度（0.0-1.0）
  - 金融リテラシー: 金融知識レベル（0.0-1.0）
  - 会話コンテキスト: 過去の対話履歴
  - 商談進捗状況: 現在の商談段階
  - 意思決定プロセス: 判断の進め方

- `CompanyContactPersona`: 企業担当者の属性
  - 基本情報
    - 名前: 担当者名
    - 役職: 部長、課長など
    - 年齢: 30-60歳
    - 入社年数: 5-30年
  - 性格特性: 企業の特性を反映
  - 意思決定スタイル: 判断の特徴
  - リスク許容度: リスクへの態度（0.0-1.0）
  - 金融リテラシー: 金融知識レベル（0.0-1.0）
  - コミュニケーションスタイル: メール対応の特徴
  - ストレス耐性: ストレス状況での対応力（0.0-1.0）
  - 適応力: 状況変化への対応力（0.0-1.0）

#### 状態管理モデル
- `SalesStatus`: 営業活動の状態を管理
  - `INITIAL`: 初回メール前の状態
  - `IN_PROGRESS`: 営業活動進行中
  - `SUCCESS`: 提案が受け入れられた
  - `FAILED`: 提案が断られた
  - `PENDING`: 検討中・保留状態

- `ProductType`: 提案可能な金融商品の種類
  - `LOAN`: 融資商品全般
  - `INVESTMENT`: 投資商品（投資信託など）
  - `DEPOSIT`: 預金商品
  - `INSURANCE`: 保険商品
  - `OTHER`: その他の金融商品

- `NegotiationStage`: 商談の進行段階を管理
  - `INITIAL`: 初期検討段階
    - 初回接触
    - 基本情報の収集
    - ニーズの概要把握
  - `INFORMATION_GATHERING`: 情報収集段階
    - 詳細なニーズヒアリング
    - 財務状況の確認
    - 具体的な要望の把握
  - `DETAILED_REVIEW`: 詳細検討段階
    - 具体的な提案内容の説明
    - 条件の詳細確認
    - 導入効果の説明
  - `FINAL_EVALUATION`: 最終評価段階
    - 提案内容の最終確認
    - 残存する懸念事項の解消
    - 導入判断の材料提供
  - `DECISION_MAKING`: 意思決定段階
    - 最終判断
    - 契約条件の確定
    - 今後の進め方の確認

### 2. サービス層
#### シミュレーションサービス（`src/services/simulation_service.py`）
主要な処理を実装するコアコンポーネント：
- ペルソナの生成と管理
  - OpenAI APIを使用したペルソナ生成
  - 属性の自動設定と整合性チェック
  - ペルソナ間の関係性管理
- メール交換セッションのシミュレーション
  - メール内容の生成と評価
  - 対話の進行管理
  - 状況変化の反映
- 商談進捗の管理
  - 段階の遷移制御
  - 成功確率の計算
  - 判断基準の適用
- 結果の記録と分析
  - 詳細なログ記録
  - 成功要因の分析
  - 改善点の特定

#### 評価サービス（`src/services/evaluation_service.py`）
提案内容を評価する専門サービス：
- 提案内容の評価
  - コスト評価（年商比率による判断）
  - リスク評価（リスク数と重要度）
  - メリット評価（具体的な利点）
  - 実現可能性評価（企業規模との整合性）
  - サポート体制評価（サポート充実度）
  - 実績評価（成功事例と業界適合性）
- 評価基準の管理
  - 基準値の設定
  - 重み付けの調整
  - 閾値の管理
- スコアリングロジックの実装
  - 各要素のスコア計算
  - 総合評価の算出
  - 調整要因の適用
- 判断基準の適用
  - 成功判定（スコア0.8以上）
  - 失敗判定（スコア0.4以下）
  - 保留判定（中間値）

#### 状況更新サービス（`src/services/situation_updater.py`）
企業と担当者の状態を更新する機能：
- 企業状況の時系列更新
  - 売上の変動（基本変動幅±5%）
  - 従業員数の変化（基本変動幅±2%）
  - 資金ニーズの変化（緊急性の変化）
  - 商品興味度の変動（基本変動幅±10%）
- 担当者の状態更新
  - ストレス耐性の変化
    - 売上減少時: -10%
    - 緊急ニーズ発生時: -15%
  - 適応力の変動
    - 大きな変化時: +5%
    - 通常時: ±3%
  - 意思決定スタイルの影響
    - 性格特性による調整
    - 状況変化への反応

#### OpenAIクライアント（`src/services/openai_client.py`）
AIモデルとの通信を管理：
- OpenAI APIとの通信管理
  - API呼び出しの制御
  - レート制限の管理
  - エラーハンドリング
- 構造化データの生成
  - JSON形式での出力
  - スキーマ検証
  - 型変換処理
- エラーハンドリング
  - API エラーの処理
  - 再試行ロジック
  - エラーログ記録
- レスポンスの検証
  - データ形式の確認
  - 整合性チェック
  - 必須項目の確認

### 3. 例外処理（`src/exceptions.py`）
システム全体の例外を管理：
- `SimulationError`: 基本例外クラス
  - シミュレーション全般のエラー
- `PersonaGenerationError`: ペルソナ生成時のエラー
  - API呼び出しエラー
  - データ検証エラー
- `EvaluationError`: 提案評価時のエラー
  - スコア計算エラー
  - 判定基準エラー
- `ConversationError`: 会話シミュレーションエラー
  - メール生成エラー
  - 対話進行エラー
- `SituationUpdateError`: 状況更新エラー
  - 数値計算エラー
  - データ更新エラー
- `APIError`: API呼び出しエラー
  - 通信エラー
  - レート制限エラー
- `ValidationError`: データ検証エラー
  - スキーマ検証エラー
  - 型変換エラー
- `ConfigurationError`: 設定エラー
  - パラメータエラー
  - 設定値の範囲エラー

### 4. 定数と設定（`src/config/constants.py`）
システム全体で使用する定数を管理：
- 評価関連の閾値
  - コスト評価基準
  - リスク評価基準
  - 成功判定基準
- 状況更新のパラメータ
  - 変動幅の設定
  - 調整係数
  - 更新頻度
- 判断基準の設定
  - スコアの閾値
  - 重み付けの係数
  - 判定条件
- メッセージ分析のキーワード
  - ポジティブワード
  - ネガティブワード
  - 重要フレーズ
- 応答タイプの閾値
  - 各応答の判定基準
  - スコアの範囲
  - 確率設定
- 性格特性による調整値
  - 特性ごとの係数
  - 組み合わせ効果
  - 影響度

## 主要な機能

### ペルソナ生成
自然な営業シナリオを実現するための詳細なペルソナを生成：
- 営業担当者と企業のペルソナを自動生成
  - OpenAI APIを使用
  - 詳細な属性情報を設定
  - 一貫性のある行動パターンを定義
- 企業ペルソナは以下の業種からランダムに生成：
  - 製造業（自動車部品、電子機器、食品加工など）
  - 小売業（スーパーマーケット、百貨店、専門店など）
  - サービス業（ITサービス、コンサルティング、教育など）
  - 建設業（建築、土木、設備工事など）
  - 運輸業（物流、運送、倉庫業など）
  - 不動産業（開発、賃貸、管理など）

### メール交換シミュレーション
リアルな営業活動を再現するメールのやり取り：
- 複数回のメール交換を時系列でシミュレーション
  - 前回のメール交換内容を考慮
  - 企業の状況変化を反映
  - 商品提案の成功度を評価
  - メールの自然な流れを維持
  - 企業担当者の性格特性を反映
  - 意思決定スタイルを考慮
  - リスク許容度に応じた提案
  - 金融リテラシーに合わせた説明
- メール交換間隔は設定可能（デフォルト1日）
- 1回のメール交換での対話回数は設定可能（デフォルト8回）

### 提案評価システム
提案内容を多角的に評価：
- 提案内容の多面的評価
  - コスト面
    - 年商比率による判断
    - 支払い条件の評価
  - リスク面
    - リスク要因の数
    - 各リスクの重要度
  - メリット面
    - 具体的な利点
    - 導入効果
  - 実現可能性
    - 企業規模との整合性
    - 実施時期の適切さ
  - サポート体制
    - サポート内容の充実度
    - 対応時間と方法
  - 実績
    - 成功事例数
    - 同業種での実績
- 評価結果に基づく応答生成
  - スコアに応じた返答
  - 懸念点への対応
- 懸念事項の特定と管理
  - 重要度の判定
  - 解決策の提案
- 追加情報要求の生成
  - 必要な情報の特定
  - 質問内容の生成

### 状況更新システム
時間経過による状況変化を管理：
- 企業状況の定期的更新
  - 売上規模の変動
    - 基本変動幅: ±5%
    - 性格による調整
  - 従業員数の変化
    - 基本変動幅: ±2%
    - 業績連動
  - 資金ニーズの変化
    - 緊急性の変化
    - 新規需要の発生
  - 商品興味度の変動
    - 基本変動幅: ±10%
    - 提案影響度
- 担当者状態の更新
  - ストレス耐性の変化
    - 業績影響
    - 商談進捗影響
  - 適応力の変動
    - 状況変化対応
    - 経験値増加
  - 意思決定スタイルの影響
    - 性格特性反映
    - 状況適応

## 出力データ
シミュレーション結果は以下の情報を含むJSONファイルとして保存：
- メタデータ
  - 生成日時
  - 銀行情報
  - シミュレーション設定
- ペルソナ情報
  - 営業担当者の詳細
  - 企業の詳細
  - 企業担当者の詳細
- シミュレーション結果
  - 各メール交換の詳細記録
  - 商談進捗状況
  - 評価結果
  - 最終ステータス
  - マッチした商品

## 使用方法
1. 必要な環境変数の設定
```bash
export OPENAI_API_KEY=your_api_key
```

2. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

必要な依存関係：
- jupyterlab >= 4.4.0
- openai >= 1.74.0
- pydantic >= 2.11.3
- python-dotenv >= 1.1.0

Python 3.11以上が必要です。

3. シミュレーションの実行
```bash
python src/main.py
```

## 設定のカスタマイズ
`src/config/settings.py`で以下の設定を変更可能：
- メール交換回数（`num_visits`）
- 対話回数（`num_turns_per_visit`）
- メール交換間隔（`visit_interval_days`）
- AIモデルの選択（`model`）
- プロンプトのカスタマイズ
- 成功判定の閾値（`min_success_score`）
- 最大試行回数（`max_attempts_per_visit`）
- 興味度スコアの閾値（`interest_score_thresholds`）
- 応答タイプの閾値（`response_type_thresholds`）
- キーワードの重み（`keyword_weights`）
- 記憶保持期間（`memory_retention_visits`）

## 注意事項
- OpenAI APIキーが必要です
- 生成されるデータは架空のものです
- シミュレーション結果は設定に依存します
- 大量のAPIコールが発生する可能性があります
- すべてのやり取りはメールのみで完結します
- 訪問や面談に関する言及は含まれません


