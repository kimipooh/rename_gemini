"""
Author: Kimiya Kitani
Description: A wrapper for Google Cloud Vertex AI (Gemini) to analyze images with multi-language output support.
License: MIT License
Version: 2.6
"""

import os
import json
import warnings
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.oauth2 import service_account

# ==========================================
# Global Settings
# ==========================================
DEFAULT_VERTEX_LOCATION = "us-central1"

# Expanded prompts based on Google Gemini supported languages
PROMPTS = {
    "en": "Analyze this image and provide a short, descriptive prefix (1 to 3 words) for its filename. Use ONLY lowercase alphanumeric characters and underscores. Do not output any other text.",
    "ja": "この画像を分析し、ファイル名の接頭辞としてふさわしい内容を簡潔に表す言葉（1〜3単語程度）を出力してください。日本語を使用してください。スペースが必要な場合はアンダースコア（_）で繋いでください。他の解説は一切出力しないでください。",
    "vi": "Hãy phân tích hình ảnh này và cung cấp một tiền tố mô tả ngắn gọn (1 đến 3 từ) cho tên tệp bằng tiếng Việt. Nếu có dấu cách, hãy thay bằng dấu gạch dưới (_). Không xuất thêm bất kỳ văn bản giải thích nào khác.",
    "th": "วิเคราะห์ภาพนี้และให้คำนำหน้าชื่อไฟล์ที่อธิบายเนื้อหาอย่างย่อ (1 ถึง 3 คำ) เป็นภาษาไทย หากมีช่องว่างให้ใช้เครื่องหมายขีดล่าง (_) แทน ห้ามแสดงข้อความอธิบายอื่นใด",
    "id": "Analisis gambar ini dan berikan awalan deskriptif pendek (1 hingga 3 kata) untuk nama filenya dalam Bahasa Indonesia. Gunakan garis bawah (_) untuk spasi. Jangan berikan teks penjelasan lainnya.",
    "ms": "Analisis imej ini dan berikan awalan deskriptif pendek (1 hingga 3 patah perkataan) untuk nama failnya dalam Bahasa Melayu. Gunakan garis bawah (_) untuk ruang. Jangan berikan teks penjelasan lain.",
    "ko": "이 이미지를 분석하고 파일 이름에 대한 짧고 설명적인 접두사(1~3단어)를 한국어로 제공하세요. 공백 대신 밑줄(_)을 사용하세요. 다른 설명 텍스트는 출력하지 마세요.",
    "zh": "分析此图像，并为其文件名提供一个简短的描述性前缀（1至3个词）。请使用中文。如果需要空格，请使用下划线（_）连接。不要输出任何其他解释性文本。",
    "hi": "इस छवि का विश्लेषण करें और इसके फ़ाइल नाम के लिए हिंदी में एक छोटा, वर्णनात्मक उपसर्ग (1 से 3 शब्द) प्रदान करें। रिक्त स्थान के लिए अंडरस्कोर (_) का उपयोग करें। कोई अन्य व्याख्यात्मक पाठ आउटपुट न करें।",
    "ar": "قم بتحليل هذه الصورة وتقديم بادئة وصفية قصيرة (من 1 إلى 3 كلمات) لاسم الملف الخاص بها باللغة العربية. استخدم الشرطة السفلية (_) للفواصل. لا تخرج أي نص توضيحي آخر.",
    "fr": "Analysez cette image et fournissez un préfixe descriptif court (1 à 3 mots) pour son nom de fichier en français. Utilisez des tirets bas (_) pour les espaces. Ne générez aucun autre texte.",
    "de": "Analysieren Sie dieses Bild und geben Sie ein kurzes, beschreibendes Präfix (1 bis 3 Wörter) für den Dateinamen auf Deutsch an. Verwenden Sie Unterstriche (_) für Leerzeichen. Geben Sie keinen weiteren Text aus.",
    "es": "Analice esta imagen y proporcione un prefijo descriptivo corto (1 a 3 palabras) para su nombre de archivo en español. Use guiones bajos (_) para los espacios. No genere ningún otro texto.",
    "pt": "Analise esta imagem e forneça um prefixo descritivo curto (1 a 3 palavras) para o nome do arquivo em português. Use sublinhados (_) para espaços. Não gere nenhum outro texto.",
    "it": "Analizza questa immagine e fornisci un prefisso descrittivo breve (da 1 a 3 parole) per il nome del file in italiano. Usa i trattini bassi (_) per gli spazi. Non generare altro testo.",
    "ru": "Проанализируйте это изображение и укажите короткий описательный префикс (от 1 до 3 слов) для его имени файла на русском языке. Используйте подчеркивания (_) вместо пробелов. Не выводите никакой другой текст.",
    "tr": "Bu görüntüyü analiz edin ve dosya adı için Türkçe kısa, açıklayıcı bir önek (1 ila 3 kelime) sağlayın. Boşluklar için alt çizgi (_) kullanın. Başka bir açıklama metni oluşturmayın.",
    "nl": "Analyseer deze afbeelding en geef een kort, beschrijvend voorvoegsel (1 tot 3 woorden) voor de bestandsnaam in het Nederlands. Gebruikt underscores (_) voor spaties. Genereer geen andere tekst.",
    "sv": "Analysera denna bild och ange ett kort, beskrivande prefix (1 till 3 ord) för filnamnet på svenska. Använd understreck (_) för blanksteg. Skapa ingen annan text."
}

EMERGENCY_MESSAGES = {
    "MSG_ERR_API_RESPONSE": "API Error: {error}", 
    "MSG_ERR_FILE_NOT_FOUND": "File not found: {path}",
    "MSG_ERR_KEY_FILE": "Service Account JSON file not found or invalid: {path}",
    "MSG_ERR_IMAGE_PROCESS": "Image processing error: {error}",
    "MSG_STATUS_START": "Starting image analysis for: {target}",
    "MSG_STATUS_RENAMED": "File renamed to: {new_path}",
    "MSG_STATUS_COPIED": "File copied to: {new_path}"
}

warnings.filterwarnings("ignore")
# ==========================================

class LanguageLoader:
    """Helper to load localized UI messages."""
    def __init__(self, lang_code="en"):
        self.lang_code = lang_code
        self.messages = {}
        self._load_messages()

    def _load_messages(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(current_dir)
        lang_file = os.path.join(base_dir, "lang", f"{self.lang_code}.json")
        if not os.path.exists(lang_file):
            lang_file = os.path.join(base_dir, "lang", "en.json")
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except Exception:
            self.messages = EMERGENCY_MESSAGES

    def get(self, key):
        return self.messages.get(key, key)

class GeminiAnalyzer:
    """Core logic for interacting with Vertex AI Gemini models."""
    def __init__(self, key_path, model_name, thinking_level=None, lang_code="en", output_lang="en"):
        self.lang = LanguageLoader(lang_code)
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.output_lang = output_lang if output_lang in PROMPTS else "en"
        self._configure_api(key_path)
        self.model = GenerativeModel(self.model_name)

    def _configure_api(self, key_path):
        """Initializes Vertex AI with a service account JSON file."""
        if not os.path.exists(key_path):
            raise FileNotFoundError(self.lang.get("MSG_ERR_KEY_FILE").format(path=key_path))
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project_id = data.get("project_id")
            if not project_id:
                raise ValueError("Project ID not found in JSON.")
            credentials = service_account.Credentials.from_service_account_file(key_path)
            vertexai.init(project=project_id, location=DEFAULT_VERTEX_LOCATION, credentials=credentials)
        except Exception as e:
            raise Exception(self.lang.get("MSG_ERR_KEY_FILE").format(path=str(e)))

    def generate_filename_prefix(self, image_path):
        """Analyzes the image and returns a prefix string."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(self.lang.get("MSG_ERR_FILE_NOT_FOUND").format(path=image_path))
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/png" if ext == ".png" else "image/jpeg"
            image_part = Part.from_data(data=image_bytes, mime_type=mime_type)
        except Exception as e:
            raise Exception(self.lang.get("MSG_ERR_IMAGE_PROCESS").format(error=str(e)))

        request_kwargs = {}
        if self.thinking_level and ("3." in self.model_name or "thinking" in self.model_name):
            budget_map = {"high": 8192, "medium": 4096, "low": 1024}
            budget = budget_map.get(str(self.thinking_level).lower(), 4096)
            request_kwargs["generation_config"] = {
                "thinking_config": {"include_thoughts": True, "thinking_budget": budget}
            }

        prompt = PROMPTS.get(self.output_lang, PROMPTS["en"])

        try:
            response = self.model.generate_content([prompt, image_part], **request_kwargs)
            prefix = response.text.strip().replace("\n", "").replace(" ", "_")
            
            # Lowercase only for Latin-based languages to preserve casing for scripts like Vietnamese or Asian languages
            latin_langs = ["en", "fr", "de", "es", "pt", "it", "sv", "nl"]
            if self.output_lang in latin_langs:
                prefix = prefix.lower()
                
            return prefix
        except Exception as e:
            raise Exception(self.lang.get("MSG_ERR_API_RESPONSE").format(error=str(e)))