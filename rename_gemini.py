#!/usr/bin/env python3
"""
Author: Kimiya Kitani
License: MIT License
Version: 2.0
Description: Gemini image classification and auto-renaming tool.
             Supports both Google AI Studio (Default) and Vertex AI (Optional).
             Supports multiple target files and wildcards.
"""

import sys
import os
import argparse
import shutil
import time
import google.generativeai as genai

# --- Automatic adjustment of module search path ---
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from modules.gemini_analyzer import GeminiAnalyzer, LanguageLoader
except ImportError as e:
    print(f"Critical Error: Required modules not found in {script_dir}. {e}")
    sys.exit(1)

# ==========================================
# Global Settings
# ==========================================
# Available Gemini Models (Availability and Characteristics)
# ----------------------------------------------------------------------
# [General Purpose & High Speed]
# - "gemini-2.5-flash"            : Standard high-speed model.
# - "gemini-2.5-flash-lite"       : Most affordable and fastest.
# - "gemini-2.0-flash-001"        : Stable version of the 2.0 series.
#
# [Latest & Preview Models]
# NOTE: These may NOT be available in your project yet (returns 404).
# Check the link below and enable if necessary before use:
# https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
# - "gemini-3.1-flash-lite-preview": Released 3/3. Supports Thinking feature.
# - "gemini-3.1-pro-preview"       : Released 2/19. For advanced reasoning.
# ----------------------------------------------------------------------

# For Google AI Studio (Default)
DEFAULT_API_KEY = "YOUR_AI_STUDIO_API_KEY"
DEFAULT_AI_STUDIO_MODEL = "gemini-2.5-flash"

# For Vertex AI (Sub/Optional)
DEFAULT_CREDENTIALS_PATH = "/Users/username/keys/your-service-account.json"
DEFAULT_VERTEX_MODEL = "gemini-2.5-flash"

DEFAULT_THINKING_LEVEL = "medium" 
DEFAULT_OUTPUT_LANG = "en"
DEFAULT_UI_LANG = "en"

MSG_INFO_ACTION_COPY   = "Action Mode: Copy (Original file is preserved)"
MSG_INFO_ACTION_RENAME = "Action Mode: Rename (Original file will be moved/overwritten)"
MSG_INFO_MODEL_CONFIG  = "Using Model: {model} | Provider: {provider} | Output Lang: {out_lang}"
MSG_INFO_PROCESSING    = "[{index}/{total}] Processing: {target}"
MSG_ERR_CRITICAL       = "Critical Error: {error}"
# ==========================================

def get_ai_studio_prefix(model, target_path, output_lang):
    """Helper for Google AI Studio (Gemini API) requests."""
    from PIL import Image
    img = Image.open(target_path)
    prompt = f"Describe this image in a very short name (max 10 characters) in {output_lang}. Output only the name."
    response = model.generate_content([prompt, img])
    return response.text.strip()

def main():
    parser = argparse.ArgumentParser(description="Gemini Image Rename Tool v2.0")
    parser.add_argument("targets", nargs="+", help="Target image path(s) or wildcard (e.g., *.png)")
    
    # Provider Settings
    parser.add_argument("--use-vertex", action="store_true", help="Use Vertex AI instead of Google AI Studio")
    
    # Common Settings
    parser.add_argument("--lang", type=str, default=None, help="UI language (ja, en)")
    parser.add_argument("--output-lang", type=str, default=DEFAULT_OUTPUT_LANG, 
                        choices=["en", "ja", "vi", "th", "id", "ms", "ko", "zh", "hi", "ar", "fr", "de", "es", "pt", "it", "ru", "tr", "nl", "sv"],
                        help="Language for the generated prefix.")
    
    # Combined Key Management: API Key (AI Studio) or JSON Path (Vertex AI)
    parser.add_argument("--keyfile", type=str, default=None, help="API Key (AI Studio) or JSON path (Vertex AI)")
    
    parser.add_argument("--model", type=str, default=None, help="Override default model name")
    parser.add_argument("--thinking", type=str, default=DEFAULT_THINKING_LEVEL)
    parser.add_argument("--action", type=str, choices=["rename", "copy"], default="rename")
    args = parser.parse_args()

    ui_lang_code = args.lang or ("ja" if os.path.exists(os.path.join(script_dir, "lang", "ja.json")) else DEFAULT_UI_LANG)
    ui_lang = LanguageLoader(ui_lang_code)

    try:
        provider = "Vertex AI" if args.use_vertex else "Google AI Studio"
        model_name = args.model or (DEFAULT_VERTEX_MODEL if args.use_vertex else DEFAULT_AI_STUDIO_MODEL)
        
        # Select the appropriate authentication key
        auth_key = args.keyfile or (DEFAULT_CREDENTIALS_PATH if args.use_vertex else DEFAULT_API_KEY)
        
        # Initialize the chosen provider
        vision_tool = None
        if args.use_vertex:
            vision_tool = GeminiAnalyzer(
                key_path=auth_key, 
                model_name=model_name, 
                thinking_level=args.thinking if args.thinking != "None" else None, 
                lang_code=ui_lang_code,
                output_lang=args.output_lang
            )
        else:
            genai.configure(api_key=auth_key)
            vision_tool = genai.GenerativeModel(model_name)

        print(MSG_INFO_MODEL_CONFIG.format(model=model_name, provider=provider, out_lang=args.output_lang))
        print(MSG_INFO_ACTION_COPY if args.action == "copy" else MSG_INFO_ACTION_RENAME)
        print("-" * 40)

        total_files = len(args.targets)
        for i, target in enumerate(args.targets, 1):
            print(MSG_INFO_PROCESSING.format(index=i, total=total_files, target=target))
            
            while True:
                try:
                    # Generate prefix based on provider
                    if args.use_vertex:
                        prefix = vision_tool.generate_filename_prefix(target)
                    else:
                        prefix = get_ai_studio_prefix(vision_tool, target, args.output_lang)
                    
                    # Sanitize prefix
                    prefix = prefix.replace("/", "-").replace("\\", "-").replace(":", "-").strip()
                    
                    target_abs_path = os.path.abspath(target)
                    target_dir = os.path.dirname(target_abs_path)
                    target_basename = os.path.basename(target_abs_path)
                    filename_without_ext, ext = os.path.splitext(target_basename)
                    
                    new_filename = f"{filename_without_ext}_{prefix}{ext}"
                    new_filepath = os.path.join(target_dir, new_filename)
                    
                    if args.action == "copy":
                        shutil.copy2(target_abs_path, new_filepath)
                        print(ui_lang.get("MSG_STATUS_COPIED").format(new_path=new_filepath))
                    else:
                        os.rename(target_abs_path, new_filepath)
                        print(ui_lang.get("MSG_STATUS_RENAMED").format(new_path=new_filepath))
                    
                    # Distinct sleep time based on provider
                    # Vertex AI (Tier 1) requires a much longer wait to avoid 429 errors.
                    # Google AI Studio usually allows much faster requests.
                    if args.use_vertex:
                        time.sleep(25)
                    else:
                        time.sleep(2)
                    break
                
                except Exception as e:
                    print(f"  Error processing {target}: {e}")
                    if "429" in str(e):
                        # Recovery time also differs by provider
                        wait_time = 90 if args.use_vertex else 30
                        print(f"  Rate limit reached (429). Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        time.sleep(10)

        print("-" * 40)
        print("Batch processing completed.")

    except Exception as e:
        print(MSG_ERR_CRITICAL.format(error=e))

if __name__ == "__main__":
    main()