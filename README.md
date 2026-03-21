# 🤖 Google Cloud Vertex AI (Gemini) Image Analyzer & Renamer

>**Version 1.0 (2026-03-06)**  
>**Version 1.1 (2026-03-06) 複数ファイルに対応**
>**Version 1.2 (2026-03-21) 複数ファイル利用時のAPI制限の対策を追加**
>**Version 1.3 (2026-03-21) 無害化（サニタイズ）: 「I/O」のような名前で発生していた [Errno 2] エラーを防ぐため、スラッシュ（/）をハイフン（-）に置換する行を追加**

> Google Cloud Vertex AI (Gemini) を利用して画像の内容を解析し、その内容にふさわしい接頭辞（プレフィックス）を生成して自動的にファイル名を変更・整理するツールです。

---
## 注意
複数ファイルを指定した場合、Vertex AIの制限よって、RPM制限（１分間に15回ぐらいが多いらしい）をうける可能性があります。実際1000枚ぐらいのテストをすると、14枚ぐらいでエラー「APIエラー: 429 Resource exhausted. Please try again later. Please refer to https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429」がでました。

下記をみると、予想では Tier1 のように支払いが少ないと制限がかなりキツそうだということがわかりました。

[Vertex AI の生成 AI の割り当てとシステム上限](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/quotas) 

そのため、10秒ごとに実施し、もし APIエラー 429 が出た場合には、60秒まってから再実行することに切り替えました。

## 📌 1. 必須設定：認証 (Credentials)

### 🛠️ Google Cloud 準備手順

本ツールは Google Cloud のエンタープライズ向け AI 基盤である **Vertex AI** を使用します。動作には **サービスアカウント JSON キー** が不可欠です。以下の手順に従って準備を行ってください。

##### 1. プロジェクトと API の有効化
* Google Cloud Console にログインし、使用するプロジェクトを選択します。
* **「API とサービス」** > **「ライブラリ」** を開き、**`Vertex AI API`** (`aiplatform.googleapis.com`) を検索して **「有効にする」** をクリックします。

##### 2. サービスアカウントの作成と権限付与
* **「IAM と管理」** > **「サービスアカウント」** に移動し、**「サービスアカウントを作成」** をクリックします。
* 任意の名前を入力して作成し、**「ロール」** の設定で以下の **2点のみ** を追加してください。
    * **`Vertex AI ユーザー`** (`roles/aiplatform.user`)：モデルへのリクエスト実行権限
    * **`Service Usage ユーザー`** (`roles/serviceusage.serviceUsageConsumer`)：プロジェクトのリソース使用権限

##### 3. JSON キーの生成と保存
* 作成したサービスアカウントを選択し、**「キー」** タブに移動します。
* **「鍵を追加」** > **「新しい鍵を作成」** を選択し、形式として **JSON** を指定してダウンロードします。
* ダウンロードしたファイルは、`rename_gemini.py` の `DEFAULT_CREDENTIALS_PATH` で指定したパスに保存してください。

> [!WARNING]
> 生成された JSON キーには強力なアクセス権が含まれます。公開リポジトリ（GitHub 等）にアップロードしたり、第三者に共有したりしないよう厳重に管理してください。

### 🛠️ Python へモジュール追加

下記のように、google-cloud-aiplatform　モジュールをインストールしてください。

`python3 -m pip install google-cloud-aiplatform`

なお、Pytyon3.10以降が望ましいです。
macOS をお使いの場合には、標準が 3.9.xです。
Homebrew などで 3.10以降をインストールした場合、

下記のように特定フォルダでのみ、下記のように 3.10以降のバージョンが使えるようにしてみてください。
```
mkdir project-a
cd project-a 
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
pip install google-cloud-aiplatform
export GOOGLE_APPLICATION_CREDENTIALS="service-account-key.json"
```

そうすれば、上記のときだけ、python コマンドで最新の pythonを使えます。
以下、python コマンドが使えると仮定して説明します。

### 🔑 設定方法
`rename_gemini.py` を開き、以下のグローバル変数に使用する JSON キーの絶対パスを指定してください。

```python
# [ rename_gemini.py 38行目付近 ]
DEFAULT_CREDENTIALS_PATH = "/Users/username/keys/your-service-account.json"
```

> [!IMPORTANT]
> 安全のため、APIキーの文字列を直接コードに書き込むことはせず、必ず外部 JSON ファイルを参照させてください。

---

## 🛠 2. 全オプション一覧 (CLI Options)

プログラム実行時に指定可能なすべてのオプションとその詳細です。

| オプション | 引数 | 説明 |
| :--- | :--- | :--- |
| `target` | (必須) | 解析対象となる画像ファイルへのパス。 (例: `./image.png`, `./*.jpg`) |
| `--lang` | `ja`, `en` | **UI表示言語**。操作ログやエラーメッセージの言語を指定します。 |
| `--output-lang` | (下記参照) | **生成されるファイル名の言語**。接頭辞をどの言語で作るか指定します。 |
| `--action` | `rename`, `copy` | **ファイル操作の動作**。直接リネームするか、コピーを作成するかを選択。 |
| `--model` | (下記参照) | 使用する **Gemini モデル ID**。 |
| `--thinking` | `high`, `medium`, `low`, `None` | **思考レベル**。Gemini 3.x系での推論の深さを調整します。 |
| `--keyfile` | `PATH` | 実行時に一時的にサービスアカウント JSON を変更する場合に指定。 |

---



## 🧬 3. モデルの選択と特性 (Models)

`--model` オプションで、目的（速度・コスト・精度）に合わせてモデルを切り替えられます。

> [!CAUTION]
> **⚠️ 注意事項：最新プレビュー版モデルの利用について**
> リスト下部の **3.1 プレビュー版モデル** は2026年2月〜3月にリリースされたばかりの最新版です。
> 現時点ではプロジェクトやリージョンによってデプロイが完了しておらず、実行時に **「404 (Not Found)」エラーが発生する可能性が高い** ためご注意ください。
>
> 実行に失敗する場合は、まず推奨の **安定版モデル（2.5系）** を使用し、最新の提供状況については以下の公式ドキュメントを確認してください。
> 🔗 [Google Cloud 公式：Gemini モデル バージョン情報](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions)

---

### 🚀 安定版モデル（2.5 シリーズ：現在利用可能・推奨）

| モデル ID | 推奨用途 / 特性 | 提供開始日 | 提供終了予定 |
| :--- | :--- | :--- | :--- |
| **`gemini-2.5-flash-image`** | **推奨。** 画像理解に特化した最適化モデル。整理タスクに最適。 | - | 2026/10/02 |
| **`gemini-2.5-pro`** | 高性能。複雑な図表や難解な文字が含まれる高度な解析用。 | 2025/06/17 | 2026/06/17 |
| **`gemini-2.5-flash`** | 標準モデル。速度と精度のバランスに優れています。 | 2025/06/17 | 2026/06/17 |
| **`gemini-2.5-flash-lite`** | 最速・最安価。大量の画像を低コストで処理したい場合に。 | 2025/07/22 | 2026/07/22 |
| **`gemini-live-2.5-flash-native-audio`** | 音声・ライブ分析対応。画像解析も可能ですが特殊用途向け。 | 2025/12/12 | 2026/12/13 |

---

### 🧪 プレビュー版モデル（段階的に提供開始）

| モデル ID | 特性 | 提供開始日 | 提供終了予定 |
| :--- | :--- | :--- | :--- |
| **`gemini-3.1-flash-lite-preview`** | 3/3リリース。思考（Thinking）機能に対応した最新軽量モデル。 | 2026/03/03 | 2026/06/01 |
| **`gemini-3.1-pro-preview`** | 2/19リリース。高度な推論能力を持つ最新の高性能モデル。 | 2026/02/19 | 2026/06/01 |

---

## 🧠 4. 思考レベルの設定 (Thinking Level)

Gemini 3.0/3.1 以降の対応モデルにおいて、AIが結論を出す前に「どれだけ深く考えるか」を指定します。

* **`high`** (8192 tokens): 複雑な文脈や曖昧な画像の深い推論（応答時間は長くなります）。
* **`medium`** (4096 tokens): 標準的な推論。バランス型（デフォルト）。
* **`low`** (1024 tokens): 単純な画像分類。高速レスポンス。
* **`None`**: 思考機能を無効化します。最も高速で低コストです。

---

## 🌏 5. ファイル名言語の設定 (Output Language)

`--output-lang` オプションにより、AIが生成する接頭辞の言語を切り替えます。以下の **19言語** に対応しています。

| コード | 言語 | 例 (プレフィックス) |
| :--- | :--- | :--- |
| `en` | 英語 (Default) | `receipt_image`, `landscape` |
| `ja` | 日本語 | `領収書`, `風景写真` |
| `vi` | ベトナム語 | `hóa_đơn`, `phong_cảnh` |
| `th` | タイ語 | `ใบเสร็จ`, `รูปภาพ` |
| `zh` | 中国語 | `发票`, `风景` |
| その他 | `ko`, `id`, `ms`, `hi`, `ar`, `fr`, `de`, `es`, `pt`, `it`, `ru`, `tr`, `nl`, `sv` | 各国の現地語 |

---

## ▶️ 6. 実行例 (Usage Examples)

### ① 日本語でファイル名を生成し、コピーを作成する
```bash
python rename_gemini.py ./aaa.JPG --output-lang ja --action copy
```

### ② 最新の3.1モデルを使い、深い推論でリネームする
```bash
python rename_gemini.py ./invoice.png --model gemini-3.1-flash-lite-preview --thinking high
```

### ③ フランス語の資料として整理する
```bash
python rename_gemini.py ./doc.jpg --output-lang fr
```

---

## 📁 7. ディレクトリ構造
```text
rename_image_files_with_gemini/
├── lang/
│   ├── en.json                 # UI：英語メッセージ
│   └── ja.json                 # UI：日本語メッセージ
├── modules/
│   ├── __init__.py
│   └── gemini_analyzer.py      # コアロジック (Vertex AIラッパー)
└── rename_gemini.py            # メイン実行スクリプト
```

---

## 👤 著者
**Kimiya Kitani**

## 📜 ライセンス
本ツールは **MITライセンス** の下で提供されます。

Copyright (c) 2026 Kimiya Kitani