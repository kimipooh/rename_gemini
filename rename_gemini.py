#!/usr/bin/env python3
"""
Author: Kimiya Kitani
License: MIT License
Version: 1.3
Description: Vertex AI (Gemini) image classification and auto-renaming tool.
             Supports multiple target files and wildcards.
"""

import sys
import os
import argparse
import shutil
import time

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
DEFAULT_CREDENTIALS_PATH = "/Users/username/keys/your-service-account.json"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-image"

DEFAULT_THINKING_LEVEL = "medium" 
DEFAULT_OUTPUT_LANG = "en"
DEFAULT_UI_LANG = "en"

MSG_INFO_ACTION_COPY   = "Action Mode: Copy (Original file is preserved)"
MSG_INFO_ACTION_RENAME = "Action Mode: Rename (Original file will be moved/overwritten)"
MSG_INFO_MODEL_CONFIG  = "Using Model: {model} | Output Lang: {out_lang} | Thinking: {thinking}"
MSG_INFO_PROCESSING    = "[{index}/{total}] Processing: {target}"
MSG_ERR_CRITICAL       = "Critical Error: {error}"
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Gemini Image Rename Tool")
    parser.add_argument("targets", nargs="+", help="Target image path(s) or wildcard (e.g., *.png)")
    parser.add_argument("--lang", type=str, default=None, help="UI language (ja, en)")
    parser.add_argument("--output-lang", type=str, default=DEFAULT_OUTPUT_LANG, 
                        choices=["en", "ja", "vi", "th", "id", "ms", "ko", "zh", "hi", "ar", "fr", "de", "es", "pt", "it", "ru", "tr", "nl", "sv"],
                        help="Language for the generated prefix.")
    parser.add_argument("--keyfile", type=str, default=DEFAULT_CREDENTIALS_PATH)
    parser.add_argument("--model", type=str, default=DEFAULT_GEMINI_MODEL)
    parser.add_argument("--thinking", type=str, default=DEFAULT_THINKING_LEVEL)
    parser.add_argument("--action", type=str, choices=["rename", "copy"], default="rename")
    args = parser.parse_args()

    thinking_level = None if args.thinking in ["None", "none", "", None] else args.thinking
    ui_lang_code = args.lang or ("ja" if os.path.exists(os.path.join(script_dir, "lang", "ja.json")) else DEFAULT_UI_LANG)
    ui_lang = LanguageLoader(ui_lang_code)

    try:
        vision_tool = GeminiAnalyzer(
            key_path=args.keyfile, 
            model_name=args.model, 
            thinking_level=thinking_level, 
            lang_code=ui_lang_code,
            output_lang=args.output_lang
        )
        
        print(MSG_INFO_MODEL_CONFIG.format(model=args.model, out_lang=args.output_lang, thinking=thinking_level or "Disabled"))
        if args.action == "copy":
            print(MSG_INFO_ACTION_COPY)
        else:
            print(MSG_INFO_ACTION_RENAME)
        
        print("-" * 40)

        total_files = len(args.targets)
        for i, target in enumerate(args.targets, 1):
            print(MSG_INFO_PROCESSING.format(index=i, total=total_files, target=target))
            
            # Retry loop for the current file to prevent skipping
            while True:
                try:
                    prefix = vision_tool.generate_filename_prefix(target)
                    
                    # --- CRITICAL FIX: Sanitize prefix to prevent [Errno 2] ---
                    # Replace characters that are invalid for filenames, especially slashes
                    prefix = prefix.replace("/", "-").replace("\\", "-").replace(":", "-").strip()
                    
                    target_abs_path = os.path.abspath(target)
                    target_dir = os.path.dirname(target_abs_path)
                    target_basename = os.path.basename(target_abs_path)
                    filename_without_ext, ext = os.path.splitext(target_basename)
                    
                    # Naming convention: OriginalName_prefix.extension
                    new_filename = f"{filename_without_ext}_{prefix}{ext}"
                    new_filepath = os.path.join(target_dir, new_filename)
                    
                    if args.action == "copy":
                        shutil.copy2(target_abs_path, new_filepath)
                        print(ui_lang.get("MSG_STATUS_COPIED").format(new_path=new_filepath))
                    else:
                        os.rename(target_abs_path, new_filepath)
                        print(ui_lang.get("MSG_STATUS_RENAMED").format(new_path=new_filepath))
                    
                    # Wait 10 seconds to avoid triggering the 429 lockout as much as possible
                    time.sleep(10)
                    break
                
                except Exception as e:
                    print(f"  Error processing {target}: {e}")
                    
                    if "429" in str(e):
                        print("  Rate limit reached (429). Waiting 60 seconds before retrying this file...")
                        time.sleep(60)
                    else:
                        # For other errors (like Errno 2 caused by slash before sanitize), wait and retry
                        print("  Unexpected error. Retrying in 10 seconds...")
                        time.sleep(10)

        print("-" * 40)
        print("Batch processing completed.")

    except Exception as e:
        print(MSG_ERR_CRITICAL.format(error=e))

if __name__ == "__main__":
    main()