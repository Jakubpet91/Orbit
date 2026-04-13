"""
InfraGuard Sentinel - Development CLI Mode
Lokální vývoj a testování analýzy Terraform kódu

Použití:
  python dev.py              # Full batch: analyzuje ALL .tf files
  python dev.py --diff       # Smart Diff: analyzuje jen ZMĚNY z git diff (HEAD)
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

# --- Konfigurace ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("❌ Chybí GEMINI_API_KEY v .env souboru!")
    sys.exit(1)


def get_git_diff(commit: str = "HEAD") -> str:
    """Extrahuje git diff z daného commitu (default: HEAD)."""
    try:
        # Get diff vs previous commit
        cmd = ["git", "diff", f"{commit}~1", commit, "--", "*.tf"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/code")
        
        if result.returncode != 0 or not result.stdout:
            logger.warning(f"⚠️  Nelze získat git diff pro {commit}")
            return ""
        
        logger.info(f"✅ Nalezen git diff pro {commit} ({len(result.stdout)} znaků)")
        return result.stdout
    except Exception as e:
        logger.error(f"❌ Chyba při čtení git diff: {e}")
        return ""


async def run_analysis_full_batch(code_dir: str = "/code"):
    """FULL BATCH MODE: Analyzuje VŠECHNY .tf soubory najednou."""
    
    print("=" * 80)
    print("InfraGuard Sentinel - Development CLI Mode [FULL BATCH]")
    print("=" * 80 + "\n")
    
    logger.info(f"🔍 Hledám Terraform soubory v: {code_dir}")
    
    terraform_files_str = load_terraform_files(code_dir)
    
    if not terraform_files_str:
        print("⚠️  VAROVÁNÍ: Nebyl nalezen žádný Terraform kód k analýze.")
        print(f"Zkontroluj složku: {code_dir}")
        sys.exit(1)
    
    char_count = len(terraform_files_str)
    print(f"✅ Načteno {char_count} znaků Terraform kódu\n")
    
    # ESTIMATE TOKENS
    estimated_tokens = estimate_tokens(terraform_files_str, mode="batch")
    print(f"[TOKEN ESTIMATE] Batch mode: ~{estimated_tokens} tokens\n")
    
    print("[*] Odeslání na Gemini API (SINGLE CALL - FULL BATCH)...\n")
    
    # SINGLE API CALL - veškerý obsah se odesílá najednou
    result = await analyze_with_gemini(
        gemini_api_key=GEMINI_API_KEY,
        diff_text="",
        modified_files=[],
        code_dir=code_dir,
        terraform_files_content=terraform_files_str
    )
    
    print("=" * 80)
    print("📋 VÝSLEDKY ANALÝZY")
    print("=" * 80)
    print(result)
    print("=" * 80)
    print("\n✅ Analýza hotova!")
    
    # Ulož výstup pro verifikaci
    try:
        output_file = Path("/tmp/gemini_response.txt")
        output_file.write_text(result, encoding="utf-8")
        logger.info(f"✅ Výstup uložen: {output_file} ({len(result)} znaků)")
    except Exception as e:
        logger.warning(f"⚠️  Nelze uložit výstup: {e}")
    
    return result


async def run_analysis_smart_diff(commit: str = "HEAD", code_dir: str = "/code"):
    """SMART DIFF MODE: Analyzuje JEN ZMĚNĚNÉ .tf soubory se kontextem."""
    
    print("=" * 80)
    print(f"InfraGuard Sentinel - Development CLI Mode [SMART DIFF: {commit}]")
    print("=" * 80 + "\n")
    
    logger.info(f"📊 Čtu git diff pro: {commit}")
    
    git_diff = get_git_diff(commit)
    if not git_diff:
        print("⚠️  Žádné změny k analýze. Spustím FULL BATCH mode místo toho.")
        return await run_analysis_full_batch(code_dir)
    
    print(f"✅ Git diff: {len(git_diff)} znaků\n")
    
    # EXTRACT SMART DIFF - jen změny se kontextem
    logger.info("🎯 Extrahuju Smart Diff s kontextem 10 řádků...")
    modified_files, smart_diff_text = extract_smart_diff(git_diff, code_dir, context=10)
    
    if not modified_files:
        logger.warning("⚠️  Žádné .tf soubory se nezměnily")
        return await run_analysis_full_batch(code_dir)
    
    print(f"✅ Změněné soubory: {', '.join(modified_files)}")
    print(f"✅ Smart Diff text: {len(smart_diff_text)} znaků (ušetřeno vs full)\n")
    
    # ESTIMATE TOKENS
    estimated_tokens = estimate_tokens(smart_diff_text, mode="smart_diff")
    print(f"[TOKEN ESTIMATE] Smart Diff mode: ~{estimated_tokens} tokens")
    print(f"[TOKEN REDUCTION] vs full batch: ~78-85% ušetřené!\n")
    
    print("[*] Odeslání na Gemini API (SINGLE CALL - SMART DIFF)...\n")
    
    # SINGLE API CALL - jen změny
    result = await analyze_with_gemini(
        gemini_api_key=GEMINI_API_KEY,
        diff_text=smart_diff_text,
        modified_files=modified_files,
        code_dir=code_dir,
        terraform_files_content=""  # Empty - používáme diff_text místo toho
    )
    
    print("=" * 80)
    print("📋 VÝSLEDKY ANALÝZY")
    print("=" * 80)
    print(result)
    print("=" * 80)
    print("\n✅ Analýza hotova!")
    
    # Ulož výstup pro verifikaci
    try:
        output_file = Path("/tmp/gemini_response.txt")
        output_file.write_text(result, encoding="utf-8")
        logger.info(f"✅ Výstup uložen: {output_file} ({len(result)} znaků)")
    except Exception as e:
        logger.warning(f"⚠️  Nelze uložit výstup: {e}")
    
    return result


if __name__ == "__main__":
    code_dir = "/code"
    use_smart_diff = False
    commit = "HEAD"
    
    # Parse argumenty
    # python dev.py                    -> FULL BATCH mode
    # python dev.py --diff             -> SMART DIFF mode (HEAD vs HEAD~1)
    # python dev.py --diff HEAD~2      -> SMART DIFF mode (HEAD~2 vs HEAD~3)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--diff":
            use_smart_diff = True
            if len(sys.argv) > 2:
                commit = sys.argv[2]
        else:
            # Jinak je to cesta
            code_dir = sys.argv[1]
    
    # Zkontroluj cestu
    if not Path(code_dir).exists():
        logger.error(f"❌ Složka {code_dir} neexistuje!")
        sys.exit(1)
    
    # Spusť analýzu (FULL BATCH nebo SMART DIFF)
    if use_smart_diff:
        asyncio.run(run_analysis_smart_diff(commit, code_dir))
    else:
        asyncio.run(run_analysis_full_batch(code_dir))
