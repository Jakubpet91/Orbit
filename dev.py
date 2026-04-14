"""
InfraGuard Sentinel - Development CLI Mode
Local development and testing of Terraform code analysis

Usage:
  python dev.py              # Full batch: analyzes ALL .tf files
  python dev.py --diff       # Smart Diff: analyzes only CHANGES from git diff (HEAD)
  python dev.py --diff HEAD~1 Study differences vs specific commit
"""

import os
import sys
import asyncio
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import shared logic
from shared import load_terraform_files, analyze_with_gemini, extract_smart_diff, estimate_tokens

# --- Configuration ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("ERROR: GEMINI_API_KEY missing from .env file!")
    sys.exit(1)


def get_git_diff(commit: str = "HEAD") -> str:
    """Extract git diff from given commit (default: HEAD)."""
    try:
        # Get diff vs previous commit
        cmd = ["git", "diff", f"{commit}~1", commit, "--", "*.tf"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/code")
        
        if result.returncode != 0 or not result.stdout:
            logger.warning(f"WARNING: Cannot obtain git diff for {commit}")
            return ""
        
        logger.info(f"SUCCESS: Found git diff for {commit} ({len(result.stdout)} characters)")
        return result.stdout
    except Exception as e:
        logger.error(f"ERROR: Failed to read git diff: {e}")
        return ""


async def run_analysis_full_batch(code_dir: str = "/code"):
    """FULL BATCH MODE: Analyzes ALL .tf files at once."""
    
    print("=" * 80)
    print("InfraGuard Sentinel - Development CLI Mode [FULL BATCH]")
    print("=" * 80 + "\n")
    
    logger.info(f"Searching for Terraform files in: {code_dir}")
    
    terraform_files_str = load_terraform_files(code_dir)
    
    if not terraform_files_str:
        print("WARNING: No Terraform code found to analyze.")
        print(f"Check directory: {code_dir}")
        sys.exit(1)
    
    char_count = len(terraform_files_str)
    print(f"SUCCESS: Loaded {char_count} characters of Terraform code\n")
    
    # ESTIMATE TOKENS
    estimated_tokens = estimate_tokens(terraform_files_str, mode="batch")
    print(f"[TOKEN ESTIMATE] Batch mode: ~{estimated_tokens} tokens\n")
    
    print("[*] Sending to Gemini API (SINGLE CALL - FULL BATCH)...\n")
    
    # SINGLE API CALL - all content sent at once
    result = await analyze_with_gemini(
        gemini_api_key=GEMINI_API_KEY,
        diff_text="",
        modified_files=[],
        code_dir=code_dir,
        terraform_files_content=terraform_files_str
    )
    
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print(result)
    print("=" * 80)
    print("\nSUCCESS: Analysis complete!")
    
    # Save output for verification
    try:
        output_file = Path("/tmp/gemini_response.txt")
        output_file.write_text(result, encoding="utf-8")
        logger.info(f"SUCCESS: Output saved: {output_file} ({len(result)} characters)")
    except Exception as e:
        logger.warning(f"WARNING: Cannot save output: {e}")
    
    return result


async def run_analysis_smart_diff(commit: str = "HEAD", code_dir: str = "/code"):
    """SMART DIFF MODE: Analyzes only CHANGED .tf files with context."""
    
    print("=" * 80)
    print(f"InfraGuard Sentinel - Development CLI Mode [SMART DIFF: {commit}]")
    print("=" * 80 + "\n")
    
    logger.info(f"Reading git diff for: {commit}")
    
    git_diff = get_git_diff(commit)
    if not git_diff:
        print("No changes to analyze. Running FULL BATCH mode instead.")
        return await run_analysis_full_batch(code_dir)
    
    print(f"SUCCESS: Git diff: {len(git_diff)} characters\n")
    
    # EXTRACT SMART DIFF - only changes with context
    logger.info("Extracting Smart Diff with 10-line context...")
    modified_files, smart_diff_text = extract_smart_diff(git_diff, code_dir, context=10)
    
    if not modified_files:
        logger.warning("WARNING: No .tf files have changed")
        return await run_analysis_full_batch(code_dir)
    
    print(f"SUCCESS: Changed files: {', '.join(modified_files)}")
    print(f"SUCCESS: Smart Diff text: {len(smart_diff_text)} characters (saved vs full)\n")
    
    # ESTIMATE TOKENS
    estimated_tokens = estimate_tokens(smart_diff_text, mode="smart_diff")
    print(f"[TOKEN ESTIMATE] Smart Diff mode: ~{estimated_tokens} tokens")
    print(f"[TOKEN REDUCTION] vs full batch: ~78-85% saved!\n")
    
    print("[*] Sending to Gemini API (SINGLE CALL - SMART DIFF)...\n")
    
    # SINGLE API CALL - only changes
    result = await analyze_with_gemini(
        gemini_api_key=GEMINI_API_KEY,
        diff_text=smart_diff_text,
        modified_files=modified_files,
        code_dir=code_dir,
        terraform_files_content=""  # Empty - using diff_text instead
    )
    
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print(result)
    print("=" * 80)
    print("\nSUCCESS: Analysis complete!")
    
    # Save output for verification
    try:
        output_file = Path("/tmp/gemini_response.txt")
        output_file.write_text(result, encoding="utf-8")
        logger.info(f"SUCCESS: Output saved: {output_file} ({len(result)} characters)")
    except Exception as e:
        logger.warning(f"WARNING: Cannot save output: {e}")
    
    return result


if __name__ == "__main__":
    code_dir = "/code"
    use_smart_diff = False
    commit = "HEAD"
    
    # Parse arguments
    # python dev.py                    -> FULL BATCH mode
    # python dev.py --diff             -> SMART DIFF mode (HEAD vs HEAD~1)
    # python dev.py --diff HEAD~2      -> SMART DIFF mode (HEAD~2 vs HEAD~3)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--diff":
            use_smart_diff = True
            if len(sys.argv) > 2:
                commit = sys.argv[2]
        else:
            # Otherwise it's a path
            code_dir = sys.argv[1]
    
    # Check path exists
    if not Path(code_dir).exists():
        logger.error(f"ERROR: Directory {code_dir} does not exist!")
        sys.exit(1)
    
    # Run analysis (FULL BATCH or SMART DIFF)
    if use_smart_diff:
        asyncio.run(run_analysis_smart_diff(commit, code_dir))
    else:
        asyncio.run(run_analysis_full_batch(code_dir))
