# 🤖 Gemini Image Analyzer & Renamer (v2.0)

> **Version 1.0 (2026-03-06)**  
> **Version 1.1 (2026-03-06) 複数ファイルに対応**  
> **Version 1.2 (2026-03-21) 複数ファイル利用時のAPI制限の対策を追加**  
> **Version 1.3 (2026-03-21) 無害化（サニタイズ）: スラッシュ等をハイフンに置換する処理を追加**  
> **Version 2.0 (2026-03-21) Vertex AIの制限回避のため Google AI Studio をデフォルトに、Vertex AI をサブに変更。**  

> Gemini API (Google AI Studio / Google Cloud Vertex AI) を利用して画像の内容を解析し、その内容にふさわしい接頭辞（プレフィックス）を生成して自動的にファイル名を変更・整理するツールです。

---
## ⚠️ 重要：API制限と接続先の変更について
複数ファイルを一括処理する場合、Vertex AI（特に初期の Tier 1 プロジェクト）では RPM制限（1分間に15回程度）が非常に厳格です。1,000枚規模の処理では頻繁に「429 Resource exhausted」エラーが発生します。

この制限を回避し、高速に処理を完了させるため、Version 2.0 より **Google AI Studio (Gemini API)** を標準の接続先として採用しました。

- **Google AI Studio (Default)**: 制限が緩く、1,000枚以上の連続処理に最適です。
- **Vertex AI (Optional)**: `--use-vertex` フラグを指定することで、従来通り使用可能です。

## 📌 1. 必須設定：認証 (Credentials)

### 🛠️ A. Google AI Studio 準備（推奨・デフォルト）
1. [Google AI Studio](https://aistudio.google.com/) で APIキーを取得します。
2. 実行時に `--keyfile` 引数でキーを渡すか、スクリプト内の `DEFAULT_API_KEY` に記述してください。

### 🛠️ B. Vertex AI 準備（サブ・オプション）
1. Google Cloud Console で **Vertex AI API** を有効にします。
2. サービスアカウントを作成し、「Vertex AI ユーザー」「Service Usage ユーザー」の権限を付与します。
3. JSON キーを生成し、実行時に `--keyfile` でパスを指定するか、`DEFAULT_CREDENTIALS_PATH` に記述してください。

### 📦 Python モジュールのインストール
Version 2.0 では以下のモジュールが必要です。

`python3 -m pip install google-cloud-aiplatform google-generativeai Pillow`

※ Python 3.10 以降を推奨します。macOS 標準の 3.9.x をお使いの場合は venv 等で最新環境を構築してください。

---

## 🛠 2. 全オプション一覧 (CLI Options)

| オプション | 引数 | 説明 |
| :--- | :--- | :--- |
| `target` | (必須) | 解析対象の画像パス (例: `./*.png`) |
| `--use-vertex` | (なし) | **Vertex AI** を使用する場合に指定（デフォルトは AI Studio）。 |
| `--keyfile` | `KEY/PATH` | **AI Studio の APIキー** または **Vertex AI の JSON パス** を指定。 |
| `--output-lang` | `ja`, `en`等 | **生成されるファイル名の言語** (19言語対応)。 |
| `--action` | `rename`, `copy`| 直接リネームするか、コピーを作成するかを選択。 |
| `--model` | `ID` | 使用する **Gemini モデル ID**。 |
| `--thinking` | `high`~`None` | **思考レベル**。推論の深さを調整（3.x系対応）。 |

---

## 🧬 3. モデルの選択 (Models)

`--model` 未指定時のデフォルト：  
- AI Studio: `gemini-2.5-flash`   
- Vertex AI: `gemini-2.5-flash`

### 🚀 推奨モデル
| モデル ID | 特性 |
| :--- | :--- |
| **`gemini-2.5-flash`** | **推奨** 安定版。標準的な画像解析に。 |
| **`gemini-2.5-flash-lite`** | **推奨** 高速・安価版。大量処理でもやすい。ただし大雑把になりやすい。 |
| **`gemini-3.1-flash-lite-preview`** | 思考機能対応。ただし思考レベルを指定しない（None）ざと大雑把になりやすい）|

---

## 🧠 4. 実行時の挙動とスリープ設定

プロバイダーの制限に合わせて待機時間を自動的に切り替えます。

- **Google AI Studio**: 制限が緩いため、1回ごとに **2秒** 待機します。429エラー時は 30秒待機します。
- **Vertex AI**: 制限が厳しいため、1回ごとに **25秒** 待機します。429エラー時は 90秒待機します。

---

## ▶️ 5. 実行例 (Usage Examples)

### ① Google AI Studio で日本語ファイル名を生成（最速・推奨）
```bash
python rename_gemini.py ./*.png --keyfile "YOUR_API_KEY" --output-lang ja
```

### ② Vertex AI を使い、最新モデルと深い推論でリネームする
```bash
python rename_gemini.py ./invoice.png --use-vertex --model gemini-3.1-flash-lite-preview --thinking high
```

---

## 👤 著者
**Kimiya Kitani**

## 📜 ライセンス
本ツールは **MITライセンス** の下で提供されます。
Copyright (c) 2026 Kimiya Kitani
