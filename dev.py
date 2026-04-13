"""
InfraGuard Sentinel - Development CLI Mode
Lokální vývoj a testování analýzy Terraform kódu

Použití:
  python dev.py          # Analyzuje /code (nebo mounted volume)
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import shared logic
from shared import load_terraform_files, analyze_with_gemini

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


async def run_analysis(code_dir: str = "/code"):
    """Spustí analýzu Terraform souborů z dané složky."""
    
    print("=" * 80)
    print("InfraGuard Sentinel - Development CLI Mode")
    print("=" * 80 + "\n")
    
    logger.info(f"🔍 Hledám Terraform soubory v: {code_dir}")
    
    terraform_files_str = load_terraform_files(code_dir)
    
    if not terraform_files_str:
        print("⚠️  VAROVÁNÍ: Nebyl nalezen žádný Terraform kód k analýze.")
        print(f"Zkontroluj složku: {code_dir}")
        sys.exit(1)
    
    print(f"✅ Načteno {len(terraform_files_str)} znaků Terraform kódu\n")
    print("[*] Odeslání na Gemini API (SINGLE CALL)...\n")
    
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


if __name__ == "__main__":
    # Použij /code pokud existuje, jinak vlj prvos argument
    code_dir = "/code"
    
    if len(sys.argv) > 1:
        code_dir = sys.argv[1]
    
    # Zkontroluj cestu
    if not Path(code_dir).exists():
        logger.error(f"❌ Složka {code_dir} neexistuje!")
        sys.exit(1)
    
    # Spusť analýzu
    asyncio.run(run_analysis(code_dir))
