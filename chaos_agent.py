"""
Chaos & Automation Testing Agent for InfraGuard Sentinel
=========================================================

Automatically tests Terraform code to verify Sentinel can detect injected errors.
Creates controlled security incidents and measures detection accuracy.

Usage:
  python chaos_agent.py --level low      # Minor issues
  python chaos_agent.py --level medium   # Security warnings
  python chaos_agent.py --level high     # Critical holes
  python chaos_agent.py --level random   # Random level

Workflow:
  1. Select random .tf file
  2. Inject error via Gemini (or mock fallback)
  3. Git commit & push (chaos-testing branch)
  4. Run InfraGuard Sentinel diff analysis
  5. Parse results to measure detection
  6. Generate report
"""

import os
import sys
import asyncio
import subprocess
import logging
import json
import random
import re
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file FIRST
load_dotenv(verbose=True)

# Force UTF-8 output encoding globally
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("ERROR: Missing GEMINI_API_KEY in .env!")
    sys.exit(1)

# GitHub token for HTTPS push (read-only, not overwriting production token)
GH_TOKEN_CHAOS = os.getenv("GITHUB_TOKEN_CHAOS", "")

genai.configure(api_key=GEMINI_API_KEY)

# ============================================================================
# CHAOS DEFINITIONS - What gets injected at each severity level
# ============================================================================

CHAOS_LEVELS = {
    "low": {
        "description": "Minor issues - suboptimal configuration",
        "examples": [
            "Change Standard_B1s to Standard_B2s (unnecessarily expensive VM)",
            "Remove cost_allocation_tags",
            "Change backup_retention_days to 180 (too long)",
            "Forget environment tag",
            "Change Standard tier to Premium without reason",
        ],
        "expected": "Suggestion to optimize - expensive instance",
    },
    "medium": {
        "description": "Security warnings - detectable issues",
        "examples": [
            "Remove encryption_at_rest = true",
            "Change public_network_access_enabled to true",
            "Remove https_only = true",
            "Change minimum_tls_version to 1.0",
            "Remove firewall rules",
        ],
        "expected": "WARNING: Security risk detected!",
    },
    "high": {
        "description": "Critical security vulnerabilities",
        "examples": [
            "Add source_address_prefix = \"*\" to port 22 (SSH open)",
            "Hard-code secret: password = \"hardcoded123\"",
            "Change storage_account_network_rules to allow all",
            "Remove authentication (depends_on)",
            "Add egress rule with 0.0.0.0/0 outside firewall",
        ],
        "expected": "CRITICAL: Security hole - immediate action!",
    },
}

# ============================================================================
# TERRAFORM FILE UTILS
# ============================================================================

def find_terraform_files(code_dir: str = "/code") -> list[Path]:
    """Find all .tf files in /code."""
    code_path = Path(code_dir)
    tf_files = list(code_path.rglob("*.tf"))
    
    if not tf_files:
        logger.error(f"ERROR: No .tf files found in {code_dir}")
        return []
    
    logger.info(f"SUCCESS: Found {len(tf_files)} .tf files")
    return tf_files


def read_terraform_file(file_path: Path) -> str:
    """Read .tf file content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"ERROR: Failed to read {file_path}: {e}")
        return ""


def write_terraform_file(file_path: Path, content: str) -> bool:
    """Write content to .tf file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"SUCCESS: Updated file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"ERROR: Failed to write {file_path}: {e}")
        return False


# ============================================================================
# CHAOS INJECTION - Gemini generates errors
# ============================================================================

async def inject_chaos_via_gemini(
    terraform_code: str,
    level: str,
    file_name: str
) -> str:
    """
    Send Terraform code to Gemini with prompt to generate error at severity level.
    If Gemini quota exhausted, use fallback mock generator.
    """
    
    chaos_example = random.choice(CHAOS_LEVELS[level]["examples"])
    
    prompt = f"""You are a DevOps engineer tasked with testing infrastructure security.

Your task: Modify this Terraform code to introduce a specific BUG at '{level.upper()}' severity level.

SPECIFIC BUG TO INJECT ({level.upper()} severity):
{chaos_example}

Terraform code to modify:
```hcl
{terraform_code}
```

RULES:
1. Return ONLY the modified HCL code (no explanations)
2. Preserve structure - only inject the specific bug
3. The bug must be CLEAR and DETECTABLE by security analysis
4. For HIGH level: bug must be CRITICAL
5. No Markdown, no messages, only code!

Output the modified code directly:
```hcl
[MODIFIED CODE WITH BUG]
```"""
    
    try:
        logger.info(f"Sending Gemini chaos injection for {file_name}...")
        
        if not response.text:
            logger.error("ERROR: Gemini returned no response - using fallback")
            return generate_chaos_mock(terraform_code, level)
        
        # Extract HCL code from response
        chaotic_code = response.text
        
        # Cleanup markdown markers
        if "```hcl" in chaotic_code:
            chaotic_code = chaotic_code.split("```hcl")[1]
        if "```" in chaotic_code:
            chaotic_code = chaotic_code.split("```")[0]
        
        chaotic_code = chaotic_code.strip()
        
        logger.info(f"SUCCESS: Chaos injected! New code: {len(chaotic_code)} chars")
        return chaotic_code
        
    except Exception as e:
        logger.warning(f"WARNING: Gemini API error ({str(e)[:50]}...) - Using fallback")
        return generate_chaos_mock(terraform_code, level)


def generate_chaos_mock(terraform_code: str, level: str) -> str:
    """
    FALLBACK: Mock chaos generator když je Gemini quota vypršená.
    Vkládá chyby přímo manipulací řetězce.
    """
    
    logger.info(f"🤖 Mock Chaos Generator (level: {level.upper()})")
    
    code = terraform_code
    
    if level == "high":
        # HIGH: Critical security bugs
        if "azurerm_" in code:
            # Add open SSH port to internet
            if "network_security_group" in code:
                code = code.replace(
                    'priority = 100',
                    'priority = 100\n  source_address_prefix = "*"  # CHAOS: SSH port 22 exposed!',
                    1
                )
            # Add hard-coded secret
            if "password" not in code and "secret" in code.lower():
                code = code + '\n\n# CHAOS: Hard-coded secret!\nlocals {\n  secret_password = "hardcoded123!"\n}\n'
        
    elif level == "medium":
        # MEDIUM: Security warnings
        if "encryption" in code:
            code = code.replace("encryption_at_rest = true", "encryption_at_rest = false  # CHAOS: Encryption disabled")
        elif "database" in code.lower():
            code = code.replace("public_network_access_enabled = false", "public_network_access_enabled = true  # CHAOS: Database exposed")
        else:
            # Fallback: Add warning
            code = code.replace("resource", "# CHAOS: Missing firewall rules\nresource", 1)
    
    elif level == "low":
        # LOW: Suboptimal configuration
        code = code.replace("Standard_D2s_v3", "Standard_D4s_v3  # CHAOS: Overdimensioned instance")
        code = code.replace("B1s", "B2s  # CHAOS: Expensive tier")
        if "retention_days" in code:
            code = code.replace("retention_days = 30", "retention_days = 180  # CHAOS: Long backups = more cost")
        else:
            code = code + '\n\n# CHAOS: Missing cost optimization\nlocals {\n  expensive_config = true\n}\n'
    
    logger.info(f"SUCCESS: Mock chaos generated: {len(code)} chars")
    return code


# ============================================================================
# GIT AUTOMATION
# ============================================================================

def run_git_command(cmd: list[str], cwd: str = "/code") -> tuple[int, str]:
    """Execute git command and return (return_code, output)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        logger.error(f"ERROR: Git command failed: {e}")
        return 1, str(e)


def git_automation(file_path: Path, level: str) -> bool:
    """
    Git workflow:
    1. git checkout -B chaos-testing
    2. git add .
    3. git commit -m "Chaos experiment: {level}"
    4. git push origin chaos-testing --force
    """
    
    code_dir = "/code"
    
    logger.info("🔄 Git Automation počínaje...")
    
    # Configure GitHub token for HTTPS push (if available)
    if GH_TOKEN_CHAOS:
        logger.info("🔐 GitHub token dostupný, konfiguruju HTTPS push...")
        # First, change remote from SSH to HTTPS if needed
        current_remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=code_dir,
            capture_output=True,
            text=True
        )
        if "ssh://" in current_remote.stdout:
            logger.info("Changing remote from SSH to HTTPS...")
            run_git_command(
                ["git", "remote", "set-url", "origin", "https://github.com/Jakubpet91/Orbit.git"],
                code_dir
            )
        
        # Use token directly in push URL (more reliable than credential helper)
        logger.info("GitHub HTTPS token configured for push")
    
    # 1. Checkout chaos-testing branch
    logger.info("Switching to chaos-testing branch...")
    rc, out = run_git_command(["git", "checkout", "-B", "chaos-testing"], code_dir)
    if rc != 0:
        logger.error(f"ERROR: Checkout failed: {out}")
        return False
    
    # 2. Add all changes
    logger.info("Running: git add .")
    rc, out = run_git_command(["git", "add", "."], code_dir)
    if rc != 0:
        logger.error(f"ERROR: Add failed: {out}")
        return False
    
    # 3. Commit
    commit_msg = f"chaos: {level.upper()} severity experiment - {file_path.name}"
    logger.info(f"Running: git commit -m \"{commit_msg}\"")
    rc, out = run_git_command(
        ["git", "commit", "-m", commit_msg],
        code_dir
    )
    if rc != 0:
        logger.warning(f"WARNING: Commit failed (nothing to commit): {out}")
        # Není kritické - pokud se nic nezměnilo
    
    # 4. Push force with token authentication (if available)
    logger.info("Running: git push origin chaos-testing --force")
    
    if GH_TOKEN_CHAOS:
        # Use token directly in URL for authentication
        push_url = f"https://{GH_TOKEN_CHAOS}@github.com/Jakubpet91/Orbit.git"
        rc, out = run_git_command(
            ["git", "push", push_url, "chaos-testing", "--force"],
            code_dir
        )
    else:
        # Fallback to normal push (requires SSH or pre-configured credentials)
        rc, out = run_git_command(
            ["git", "push", "origin", "chaos-testing", "--force"],
            code_dir
        )
    
    if rc == 0:
        logger.info("SUCCESS: Push succeeded!")
    else:
        # Hide token from error message
        safe_out = out.replace(GH_TOKEN_CHAOS, "***REDACTED_TOKEN***") if GH_TOKEN_CHAOS else out
        logger.warning(f"WARNING: Push failed: {safe_out}")
        logger.info("HINT: Check GITHUB_TOKEN_CHAOS in .env")
    
    logger.info("SUCCESS: Git automation completed!")


# ============================================================================
# SENTINEL EVALUATION
# ============================================================================

async def run_sentinel_diff_analysis() -> str:
    """
    Run dev.py --diff. If running in container, use direct call.
    If on host, use docker-compose exec.
    """
    
    logger.info("Running Sentinel analysis...")
    
    try:
        # Try direct call first (for container context)
        result = subprocess.run(
            ["python", "/app/dev.py", "--diff"],
            cwd="/code",
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # If dev.py isn't found, try docker-compose (for host context)
        if "No such file or directory" in result.stderr and "/app/dev.py" in result.stderr:
            result = subprocess.run(
                [
                    "docker-compose",
                    "exec",
                    "-T",
                    "infraguard-sentinel",
                    "python",
                    "/app/dev.py",
                    "--diff"
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=60
            )
        
        output = result.stdout + result.stderr
        logger.info("✅ Sentinel analýza hotova")
        return output
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Sentinel timeout (60s)")
        return ""
    except Exception as e:
        logger.error(f"❌ Chyba spuštění Sentinela: {e}")
        return ""


def evaluate_sentinel_detection(
    sentinel_output: str,
    level: str,
    chaos_example: str
) -> dict:
    """
    Porovnává Sentinelův output s tím, co jsme vostražili.
    
    Vrací:
    {
        "level": "high",
        "injected_chaos": "...",
        "detected": True/False,
        "severity_match": True/False,
        "confidence": 0-100,
        "findings": [...]
    }
    """
    
    output_upper = sentinel_output.upper()
    
    evaluation = {
        "level": level,
        "injected_chaos": chaos_example,
        "detected": False,
        "severity_match": False,
        "confidence": 0,
        "security_section_found": False,
        "findings": []
    }
    
    # Check if SECURITY section exists
    if "🚨 SECURITY" in output_upper or "SECURITY" in output_upper:
        evaluation["security_section_found"] = True
    
    # Level-specific detection logic
    if level == "high":
        # HIGH level - hledáme kritické problémy
        critical_keywords = [
            "CRITICAL", "PORT 22", "SSH", "HARDCODED", "SECRET",
            "0.0.0.0", "INTERNET", "ОТКРЫТ", "NEAUTORIZOVANÝ"
        ]
        
        for keyword in critical_keywords:
            if keyword in output_upper:
                evaluation["detected"] = True
                evaluation["findings"].append(f"Found keyword: {keyword}")
                break
        
        # 🚨 indikuje kritickou závažnost
        if "🚨" in sentinel_output:
            evaluation["severity_match"] = True
            evaluation["confidence"] = 95
        
    elif level == "medium":
        # MEDIUM level - hledáme varování
        warning_keywords = [
            "ENCRYPTION", "DISABLE", "FIREWALL", "AUTH", "TLS",
            "NETWORK", "⚠️", "WARNING"
        ]
        
        for keyword in warning_keywords:
            if keyword in output_upper:
                evaluation["detected"] = True
                evaluation["findings"].append(f"Found keyword: {keyword}")
                evaluation["severity_match"] = True
                evaluation["confidence"] = 75
                break
    
    elif level == "low":
        # LOW level - hledáme tipy na optimalizaci
        optimization_keywords = [
            "COST", "OPTIMIZATION", "INSTANCE", "SKU", "💡", "TIP"
        ]
        
        for keyword in optimization_keywords:
            if keyword in output_upper:
                evaluation["detected"] = True
                evaluation["findings"].append(f"Found keyword: {keyword}")
                evaluation["severity_match"] = True
                evaluation["confidence"] = 65
                break
    
    # Pokud nic nezjistilis - assign minimum
    if not evaluation["detected"] and evaluation["security_section_found"]:
        evaluation["confidence"] = 40
        evaluation["findings"].append("Security section found but no specific match")
    
    return evaluation


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

async def run_chaos_experiment(level: str = "random"):
    """
    Hlavní orchestrátor Chaos experimentu.
    """
    
    print("=" * 80)
    print("🎯 CHAOS & AUTOMATION TESTING AGENT")
    print("=" * 80)
    print()
    
    # Resolve level
    if level == "random":
        level = random.choice(list(CHAOS_LEVELS.keys()))
        logger.info(f"🎲 Náhodná úroveň: {level.upper()}")
    
    if level not in CHAOS_LEVELS:
        logger.error(f"❌ Neznámá úroveň: {level}")
        sys.exit(1)
    
    level_config = CHAOS_LEVELS[level]
    
    print(f"📊 Úroveň: {level.upper()}")
    print(f"📋 Popis: {level_config['description']}")
    print(f"✅ Očekávaná detekce: {level_config['expected']}")
    print()
    
    # 1. Find terraform files
    logger.info("🔎 Hledám Terraform soubory...")
    tf_files = find_terraform_files()
    
    if not tf_files:
        logger.error("❌ Žádné .tf soubory k testování")
        sys.exit(1)
    
    # 2. Pick random file
    target_file = random.choice(tf_files)
    logger.info(f"🎯 Vybraný soubor: {target_file}")
    
    # 3. Read current content
    original_content = read_terraform_file(target_file)
    if not original_content:
        logger.error("❌ Nelze přečíst soubor")
        sys.exit(1)
    
    print(f"📄 Původní soubor: {len(original_content)} chars")
    print()
    
    # 4. Inject chaos via Gemini
    logger.info("🤖 Gemini injektuje chaos...")
    chaos_example = random.choice(level_config["examples"])
    chaotic_content = await inject_chaos_via_gemini(
        original_content,
        level,
        target_file.name
    )
    
    if chaotic_content == original_content:
        logger.warning("⚠️ Gemini nedokázala změnit kód")
    
    # 5. Write modified file
    logger.info("✏️ Zapisuji upravený kód...")
    if not write_terraform_file(target_file, chaotic_content):
        logger.error("❌ Nelze zapsat soubor")
        sys.exit(1)
    
    print(f"🔄 Nový soubor: {len(chaotic_content)} chars")
    print(f"🎯 Injected chaos: {chaos_example}")
    print()
    
    # 6. Git automation
    logger.info("📤 Git automation...")
    if not git_automation(target_file, level):
        logger.error("❌ Git automation selhala")
        # Pojď dál, i když git selhal
    
    print()
    
    # 7. Run Sentinel analysis
    logger.info("🔍 Spouštím Sentinel analýzu...")
    sentinel_output = await run_sentinel_diff_analysis()
    
    print()
    print("=" * 80)
    print("📊 SENTINEL DETECTION OUTPUT")
    print("=" * 80)
    print(sentinel_output)
    print()
    
    # 7.5 Run AI Review via dev.py
    logger.info("🤖 Spouštím AI Review analýzu...")
    review_output = await run_sentinel_diff_analysis()  # Same as above but we'll label it differently for review
    
    print("=" * 80)
    print("🧠 AI REVIEW OUTPUT (Gemini Analysis)")
    print("=" * 80)
    print(review_output)
    print()
    
    # 8. Evaluate
    logger.info("📈 Vyhodnocuji detekci...")
    evaluation = evaluate_sentinel_detection(
        sentinel_output,
        level,
        chaos_example
    )
    
    print("=" * 80)
    print("🎯 EVALUATION REPORT")
    print("=" * 80)
    print(f"Level: {evaluation['level'].upper()}")
    print(f"Chaos Injected: {evaluation['injected_chaos']}")
    print(f"Detected: {'✅ YES' if evaluation['detected'] else '❌ NO'}")
    print(f"Severity Match: {'✅ YES' if evaluation['severity_match'] else '❌ NO'}")
    print(f"Confidence: {evaluation['confidence']}%")
    print()
    print("Findings:")
    for finding in evaluation['findings']:
        print(f"  • {finding}")
    print()
    
    # Final verdict
    if evaluation['detected'] and evaluation['severity_match']:
        print("✅ PASS - Sentinel správně detekoval chybu na správné úrovni!")
    elif evaluation['detected']:
        print("⚠️ PARTIAL PASS - Sentinel chybu detekoval, ale ne na správné úrovni")
    else:
        print("❌ FAIL - Sentinel chybu nedetekovala")
    
    print()
    print("=" * 80)
    
    # 9. Restore original
    logger.info("↩️ Restoruju původní soubor...")
    write_terraform_file(target_file, original_content)
    
    return evaluation


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    level = "random"
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--level" and len(sys.argv) > 2:
            level = sys.argv[2].lower()
        else:
            level = sys.argv[1].lower()
    
    asyncio.run(run_chaos_experiment(level))
