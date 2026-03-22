"""
Author: Kimiya Kitani
Description: A wrapper for Google Cloud Vertex AI (Gemini) to analyze images with multi-language output support.
License: MIT License
Version: 3.0
"""

import os
import json
import warnings
from google import genai
from PIL import Image

# ==========================================
# Global Settings
# ==========================================
DEFAULT_VERTEX_LOCATION = "us-central1"

# Expanded prompts focused on structured and specific identification (Optimized for 2.5 Flash/3.1 Flash)
PROMPTS = {
    "en": "Analyze this image and generate a highly specific and structured filename prefix. Identify the specific service, UI element, or report title shown. Use underscores (_) instead of spaces. Format example: ServiceName_Detail. Output ONLY the prefix.",
    "ja": "この画像を分析し、具体的かつ構造的なファイル名用接頭辞を生成してください。サービス名、画面項目、レポート名などを特定し、詳細がわかるようにしてください。スペースの代わりにアンダースコア（_）を使用してください。形式例：サービス名_詳細。接頭辞のみを出力してください。",
    "vi": "Hãy phân tích hình ảnh này và tạo một tiền tố tên tệp có cấu trúc và cụ thể. Xác định dịch vụ, thành phần giao diện hoặc tiêu đề báo cáo cụ thể. Sử dụng dấu gạch dưới (_) thay cho khoảng trắng. Định dạng: TenDichVu_ChiTiet. CHỈ xuất tiền tố.",
    "th": "วิเคราะห์ภาพนี้และสร้างคำนำหน้าชื่อไฟล์ที่มีโครงสร้างและเจาะจง ระบุชื่อบริการ องค์ประกอบ UI หรือชื่อรายงานที่เฉพาะเจาะจง ใช้เครื่องหมายขีดล่าง (_) แทนช่องว่าง รูปแบบ: ชื่อบริการ_รายละเอียด แสดงเฉพาะคำนำหน้าเท่านั้น",
    "id": "Analisis gambar ini dan buat awalan nama file yang sangat spesifik dan terstruktur. Identifikasi layanan, elemen UI, atau judul laporan tertentu. Gunakan garis bawah (_) sebagai pengganti spasi. Format: NamaLayanan_Detail. Hanya keluarkan awalan saja.",
    "ms": "Analisis imej ini dan hasilkan awalan nama fail yang sangat khusus dan berstruktur. Kenal pasti perkhidmatan, elemen UI, atau tajuk laporan yang khusus. Gunakan garis bawah (_) dan bukannya ruang. Format: NamaPerkhidmatan_Butiran. Hanya paparkan awalan sahaja.",
    "ko": "이 이미지를 분석하여 매우 구체적이고 구조화된 파일 이름 접두사를 생성하세요. 특정 서비스, UI 요소 또는 보고서 제목을 식별하세요. 공백 대신 밑줄(_)을 사용하세요. 형식: 서비스명_상세내용. 접두사만 출력하세요.",
    "zh": "分析此图像并生成一个高度具体且结构化的文件名前缀。识别具体的服务、UI 元素或报告标题。使用下划线 (_) 代替空格。格式示例：服务名_详情。只输出前缀。",
    "hi": "इस छवि का विश्लेषण करें और एक अत्यधिक विशिष्ट और संरचित फ़ाइल नाम उपसर्ग उत्पन्न करें। विशिष्ट सेवा, UI तत्व, या रिपोर्ट शीर्षक की पहचान करें। रिक्त स्थान के स्थान पर अंडरस्コア (_) का उपयोग करें। प्रारूप: ServiceName_Detail। केवल उपसर्ग आउटपुट करें।",
    "ar": "قم بتحليل هذه الصورة وإنشاء بادئة اسم ملف محددة ومنظمة للغاية. حدد الخدمة أو عنصر واجهة المستخدم أو عنوان التقرير المحدد. استخدم الشرطة السفلية (_) بدلاً من المسافات. التنسيق: اسم_الخدمة_التفاصيل. أخرج البادئة فقط.",
    "fr": "Analysez cette image et générez un préfixe de nom de fichier très spécifique et structuré. Identifiez le service, l'élément d'interface ou le titre du rapport spécifique. Utilisez des traits de soulignement (_) au lieu d'espaces. Format : NomDuService_Détail. Affichez UNIQUEMENT le préfixe.",
    "de": "Analysieren Sie dieses Bild und erstellen Sie ein spezifisches und strukturiertes Dateinamen-Präfix. Identifizieren Sie den Dienst, das UI-Element oder den Berichtstitel. Verwenden Sie Unterstriche (_) anstelle von Leerzeichen. Format: DienstName_Detail. Geben Sie NUR das Präfix aus.",
    "es": "Analice esta imagen y genere un prefijo de nombre de archivo muy específico y estructurado. Identifique el servicio, el elemento de la interfaz o el título del informe específico. Use guiones bajos (_) en lugar de espacios. Formato: NombreDelServicio_Detalle. Muestre SOLO el prefijo.",
    "pt": "Analise esta imagem e gere um prefixo de nome de arquivo altamente específico e estruturado. Identifique o serviço, elemento de interface ou título de relatório específico. Use sublinhados (_) em vez de espaços. Formato: NomeDoServiço_Detalhe. Forneça APENAS o prefixo.",
    "it": "Analizza questa immagine e genera un prefisso per il nome del file altamente specifico e strutturato. Identifica il servizio, l'elemento dell'interfaccia o il titolo del report specifico. Usa i trattini bassi (_) al posto degli spazi. Formato: NomeServizio_Dettaglio. Produci SOLO il prefisso.",
    "ru": "Проанализируйте это изображение и создайте конкретный и структурированный префикс имени файла. Укажите название сервиса, элемента интерфейса или заголовка отчета. Используйте подчеркивания (_) вместо пробелов. Формат: НазваниеСервиса_Детали. Выводите ТОЛЬКО префикс.",
    "tr": "Bu görüntüyü analiz edin ve son derece spesifik ve yapılandırılmış bir dosya adı öneki oluşturun. Belirli hizmeti, kullanıcı arayüzü öğesini veya rapor başlığını tanımlayın. Boşluk yerine alt çizgi (_) kullanın. Biçim: HizmetAdı_Detay. YALNIZCA öneki çıktı olarak verin.",
    "nl": "Analyseer deze afbeelding en genereer een zeer specifieke en gestructureerde bestandsnaam-prefix. Identificeer de specifieke service, het UI-element of de rapporttitel. Gebruik underscores (_) in plaats van spaties. Formaat: ServiceNaam_Detail. Voer ALLEEN de prefix uit.",
    "sv": "Analysera denna bild och generera ett mycket specifikt och strukturerat filnamnsprefix. Identifiera den specifika tjänsten, UI-elementet eller rapporttiteln. Använd understreck (_) istället för blanksteg. Format: Tjänstnamn_Detalj. Skapa ENDAST prefixet."
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
        self.client = self._configure_api(key_path)

    def _configure_api(self, key_path):
        """Initializes Vertex AI with a service account JSON file using google-genai SDK."""
        if not os.path.exists(key_path):
            raise FileNotFoundError(self.lang.get("MSG_ERR_KEY_FILE").format(path=key_path))
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project_id = data.get("project_id")
            if not project_id:
                raise ValueError("Project ID not found in JSON.")
            
            # Use the unified Client for Vertex AI
            return genai.Client(
                vertexai=True,
                project=project_id,
                location=DEFAULT_VERTEX_LOCATION,
                credentials=key_path # google-genai supports path to JSON or dict
            )
        except Exception as e:
            raise Exception(self.lang.get("MSG_ERR_KEY_FILE").format(path=str(e)))

    def generate_filename_prefix(self, image_path):
        """Analyzes the image and returns a prefix string."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(self.lang.get("MSG_ERR_FILE_NOT_FOUND").format(path=image_path))
        
        try:
            img = Image.open(image_path)
        except Exception as e:
            raise Exception(self.lang.get("MSG_ERR_IMAGE_PROCESS").format(error=str(e)))

        config = {}
        if self.thinking_level and ("3." in self.model_name or "thinking" in self.model_name):
            budget_map = {"high": 8192, "medium": 4096, "low": 1024}
            budget = budget_map.get(str(self.thinking_level).lower(), 4096)
            config["thinking_config"] = {"include_thoughts": True, "thinking_budget": budget}

        prompt = PROMPTS.get(self.output_lang, PROMPTS["en"])

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img],
                config=config
            )
            prefix = response.text.strip().replace("\n", "").replace(" ", "_")
            
            # Lowercase only for Latin-based languages to preserve casing for scripts like Vietnamese or Asian languages
            latin_langs = ["en", "fr", "de", "es", "pt", "it", "sv", "nl"]
            if self.output_lang in latin_langs:
                prefix = prefix.lower()
                
            return prefix
        except Exception as e:
            raise Exception(self.lang.get("MSG_ERR_API_RESPONSE").format(error=str(e)))