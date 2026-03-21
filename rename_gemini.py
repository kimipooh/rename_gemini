#!/usr/bin/env python3
"""
Author: Kimiya Kitani
License: MIT License
Version: 1.2
Description: Vertex AI (Gemini) image classification and auto-renaming tool.
             Supports multiple target files and wildcards.
"""

import sys
import os
import argparse
import shutil
import time  # Added for sleep processing

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

# Available Gemini Models (Availability and Characteristics)
# ----------------------------------------------------------------------
# [Best for Image Analysis and Classification]
# - "gemini-2.5-flash-image"      : Optimized for image understanding. Best for current image organization.
#
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
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-image"

DEFAULT_THINKING_LEVEL = "medium" 
DEFAULT_OUTPUT_LANG = "en"
DEFAULT_UI_LANG = "en"

# UI Messaging Definitions
MSG_INFO_ACTION_COPY   = "Action Mode: Copy (Original file is preserved)"
MSG_INFO_ACTION_RENAME = "Action Mode: Rename (Original file will be moved/overwritten)"
MSG_INFO_MODEL_CONFIG  = "Using Model: {model} | Output Lang: {out_lang} | Thinking: {thinking}"
MSG_INFO_PROCESSING    = "[{index}/{total}] Processing: {target}"
MSG_ERR_CRITICAL       = "Critical Error: {error}"
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Gemini Image Rename Tool")
    
    # Changed "target" to "targets" and added nargs="+" to support multiple files
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
        # Initialize Analyzer
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

        # Iterate through all target files
        total_files = len(args.targets)
        for i, target in enumerate(args.targets, 1):
            print(MSG_INFO_PROCESSING.format(index=i, total=total_files, target=target))
            
            # Retry loop for the current file to prevent skipping on 429 errors
            while True:
                try:
                    prefix = vision_tool.generate_filename_prefix(target)
                    
                    target_abs_path = os.path.abspath(target)
                    target_dir = os.path.dirname(target_abs_path)
                    target_basename = os.path.basename(target_abs_path)
                    filename_without_ext, ext = os.path.splitext(target_basename)
                    
                    # Update: Naming convention set to OriginalName_GeminiName.extension
                    new_filename = f"{filename_without_ext}_{prefix}{ext}"
                    new_filepath = os.path.join(target_dir, new_filename)
                    
                    if args.action == "copy":
                        shutil.copy2(target_abs_path, new_filepath)
                        print(ui_lang.get("MSG_STATUS_COPIED").format(new_path=new_filepath))
                    else:
                        os.rename(target_abs_path, new_filepath)
                        print(ui_lang.get("MSG_STATUS_RENAMED").format(new_path=new_filepath))
                    
                    # Success: Wait 7 seconds before the next file and break the retry loop
                    time.sleep(7)
                    break
                
                except Exception as e:
                    print(f"  Error processing {target}: {e}")
                    
                    # If 429 error occurs, wait for 60 seconds and retry the SAME file
                    if "429" in str(e):
                        print("  Rate limit reached (429). Waiting 60 seconds before retrying this file...")
                        time.sleep(60)
                    else:
                        # For other errors, wait 10 seconds and retry
                        print("  Unexpected error. Retrying in 10 seconds...")
                        time.sleep(10)

        print("-" * 40)
        print("Batch processing completed.")

    except Exception as e:
        print(MSG_ERR_CRITICAL.format(error=e))

if __name__ == "__main__":
    main()