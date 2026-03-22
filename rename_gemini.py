#!/usr/bin/env python3
"""
Author: Kimiya Kitani
License: MIT License
Version: 3.0
Description: Gemini image classification and auto-renaming tool.
             Supports both Google AI Studio (Default) and Vertex AI (Optional).
             Supports multiple target files and wildcards.
"""

import sys
import os
import argparse
import shutil
import time
import json
from google import genai

# --- Automatic adjustment of module search path ---
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from modules.gemini_analyzer import LanguageLoader
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
DEFAULT_PROJECT_ID = "YOUR_PROJECT_ID" # This will be overridden if keyfile is provided
DEFAULT_LOCATION = "us-central1"       # Required for Vertex AI

DEFAULT_THINKING_LEVEL = "medium" 
DEFAULT_OUTPUT_LANG = "en"
DEFAULT_UI_LANG = "en"

MSG_INFO_ACTION_COPY   = "Action Mode: Copy (Original file is preserved)"
MSG_INFO_ACTION_RENAME = "Action Mode: Rename (Original file will be moved/overwritten)"
MSG_INFO_MODEL_CONFIG  = "Using Model: {model} | Provider: {provider} | Output Lang: {out_lang}"
MSG_INFO_PROCESSING    = "[{index}/{total}] Processing: {target}"
MSG_ERR_CRITICAL       = "Critical Error: {error}"
# ==========================================

def get_gemini_prefix(client, model_name, target_path, output_lang):
    """Helper for both AI Studio and Vertex AI requests using the new SDK."""
    from PIL import Image
    img = Image.open(target_path)
    prompt = f"Describe this image in a very short name (max 10 characters) in {output_lang}. Output only the name."
    response = client.models.generate_content(
        model=model_name,
        contents=[prompt, img]
    )
    return response.text.strip()

def main():
    parser = argparse.ArgumentParser(description="Gemini Image Rename Tool v2.1")
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

    # Waiting Time Settings
    parser.add_argument("--sleep", type=float, default=None, help="Sleep time (seconds) between requests.")
    parser.add_argument("--retry-sleep", type=float, default=None, help="Sleep time (seconds) after a 429 error.")
    
    args = parser.parse_args()

    ui_lang_code = args.lang or ("ja" if os.path.exists(os.path.join(script_dir, "lang", "ja.json")) else DEFAULT_UI_LANG)
    ui_lang = LanguageLoader(ui_lang_code)

    try:
        provider = "Vertex AI" if args.use_vertex else "Google AI Studio"
        model_name = args.model or (DEFAULT_VERTEX_MODEL if args.use_vertex else DEFAULT_AI_STUDIO_MODEL)
        
        # Select the appropriate authentication key
        auth_key = args.keyfile or (DEFAULT_CREDENTIALS_PATH if args.use_vertex else DEFAULT_API_KEY)
        
        # Initialize the chosen provider using unified SDK
        vision_tool = None
        if args.use_vertex:
            # Resolve project_id from JSON file if available
            project_id = DEFAULT_PROJECT_ID
            if auth_key and os.path.exists(auth_key):
                try:
                    with open(auth_key, "r", encoding="utf-8") as f:
                        key_data = json.load(f)
                        project_id = key_data.get("project_id", DEFAULT_PROJECT_ID)
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = auth_key
                except Exception as e:
                    print(f"  Warning: Could not parse project_id from {auth_key}. {e}")
            
            vision_tool = genai.Client(
                vertexai=True,
                project=project_id,
                location=DEFAULT_LOCATION
            )
        else:
            vision_tool = genai.Client(api_key=auth_key)

        print(MSG_INFO_MODEL_CONFIG.format(model=model_name, provider=provider, out_lang=args.output_lang))
        print(MSG_INFO_ACTION_COPY if args.action == "copy" else MSG_INFO_ACTION_RENAME)
        print("-" * 40)

        total_files = len(args.targets)
        for i, target in enumerate(args.targets, 1):
            print(MSG_INFO_PROCESSING.format(index=i, total=total_files, target=target))
            
            while True:
                try:
                    # Generate prefix based on provider (Unified calling syntax)
                    prefix = get_gemini_prefix(vision_tool, model_name, target, args.output_lang)
                    
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
                    
                    # Distinct sleep time based on provider or custom argument
                    # Vertex AI (Tier 1) requires a much longer wait to avoid 429 errors.
                    # Google AI Studio usually allows much faster requests.
                    if args.sleep is not None:
                        time.sleep(args.sleep)
                    elif args.use_vertex:
                        time.sleep(25)
                    else:
                        time.sleep(0.3)
                    break
                
                except Exception as e:
                    print(f"  Error processing {target}: {e}")
                    if "429" in str(e):
                        # Recovery time also differs by provider or custom argument
                        if args.retry_sleep is not None:
                            wait_time = args.retry_sleep
                        else:
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