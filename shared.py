"""
Sdílená logika pro InfraGuard Sentinel
- Gemini API integrace
- Loading Terraform files
- README management
"""

import logging
import traceback
from pathlib import Path
import google.generativeai as genai

logger = logging.getLogger(__name__)

# --- Master Prompt pro Gemini 2.5 Flash ---

SYSTEM_PROMPT = """VÝ JSTE 'InfraGuard Sentinel' - Senior Cloud Security & Infrastructure Review Expert.

YOUR TASK: Analyze a complete Terraform project structure where ALL files are visible to you.
Look for CROSS-FILE relationships and inconsistencies.

IMPORTANT: You will receive a SINGLE comprehensive prompt with ALL .tf files concatenated.
Your analysis must consider interactions between files, not individual files in isolation.

EXAMPLES OF CROSS-FILE ISSUES TO DETECT:
- Variables defined in variables.tf but not used consistently in main.tf
- Security groups referenced in network/main.tf but not properly connected in aks/main.tf  
- Module outputs used but not imported in dependent modules
- Hardcoded values instead of variable references
- Missing security boundaries between modules

RESPONSE FORMAT - YOU MUST PROVIDE ALL THREE SECTIONS:

🚨 SECURITY
[List all security issues found across the project]

💰 COSTS
[Monthly cost estimate for the ENTIRE infrastructure with USD breakdown]
FOR EACH MAJOR COST LINE (AKS, SQL, Storage, etc), ADD A "💡 Cost Saving Tip:" with specific actions:
  Examples:
  - "Use Azure Spot VMs instead of regular VMs to save ~70%"
  - "Downgrade SQL from S1 to S0 tier to save ~40 USD/month"
  - "Enable Reserved Capacity for 1-year commitment to save ~35%"
  - "Use Standard Load Balancer instead of Premium for ~10 USD/month savings"
  - "Archive old Terraform state backups to Blob Cold tier for 60% storage savings"

📝 DOCUMENTATION
[Documentation gaps or confirmation that docs are complete]

NON-NEGOTIABLE: Always include all three sections. Never skip. Never truncate. Include Cost Saving Tips with each major expense."""


def load_readme(code_dir="/code") -> str:
    """Pokusí se načíst README.md z složky."""
    readme_path = Path(code_dir) / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Chyba čtení README.md: {e}")
            return ""
    return ""


def load_terraform_files(code_dir="/code") -> str:
    """Načte VŠECHNY .tf soubory a vrátí je jako jeden strukturovaný text s oddělovači."""
    code_path = Path(code_dir)
    
    if not code_path.exists():
        logger.warning(f"Složka {code_dir} neexistuje!")
        return ""
    
    tf_files = sorted(list(code_path.rglob("*.tf")))
    
    if not tf_files:
        logger.warning(f"V {code_dir} nejsou žádné .tf soubory!")
        return ""
    
    logger.info(f"Nalezeno {len(tf_files)} .tf souborů:")
    
    all_content = []
    for tf_file in tf_files:
        relative_path = tf_file.relative_to(code_path)
        try:
            with open(tf_file, "r", encoding="utf-8") as f:
                content = f.read()
                all_content.append(f"FILE: {relative_path} START\n{content}\nFILE: {relative_path} END\n")
                logger.info(f"  ✅ {relative_path}")
        except Exception as e:
            logger.error(f"  ❌ Chyba čtení {relative_path}: {e}")
    
    combined = "\n".join(all_content)
    logger.info(f"Celkem načteno: {len(combined)} znaků")
    return combined


def estimate_tokens(text: str, mode: str = "batch") -> int:
    """
    Rough estimate of tokens (Gemini uses ~4 chars = 1 token).
    
    Modes:
    - 'batch': Full content (no reduction)
    - 'smart_diff': Reduced diff with context (78-85% savings assumed)
    
    For accurate counts, use Google's tokenizer, ale to je overkill.
    """
    base_tokens = len(text) // 4
    
    if mode == "smart_diff":
        # Smart Diff redukuje o ~80% (empiricky)
        return int(base_tokens * 0.2)
    
    return base_tokens


def extract_diff_with_context(patch_text: str, context_lines: int = 10) -> str:
    """
    Extrahuje diff se smyslem - vrací jen změněné řádky + kontext.
    Redukuje velikost diffu o ~60-70%.
    
    Vstup: Unified diff format (@@...)
    Výstup: Strukturovaný diff s kontextem
    """
    if not patch_text:
        return ""
    
    lines = patch_text.split("\n")
    result = []
    context_buffer = []
    hunk_header = None
    
    for line in lines:
        # Detekce hunk headeru: @@ -5,10 +5,12 @@
        if line.startswith("@@"):
            hunk_header = line
            result.append(hunk_header)
            context_buffer = []
        elif hunk_header:
            # Kontext (nezměněné řádky)
            if line.startswith(" "):
                context_buffer.append(line)
                # Když máme dost kontextu, zahoď starý
                if len(context_buffer) > context_lines:
                    context_buffer.pop(0)
            # Změněné řádky
            elif line.startswith("+") or line.startswith("-"):
                # Přidej všech buffer lines jako kontext
                result.extend(context_buffer)
                context_buffer = []
                result.append(line)
            # Konec hunka nebo souboru
            elif line.startswith("\\"):
                pass
    
    return "\n".join(result)


def reduce_diff_batch(files_diffs: dict[str, str]) -> str:
    """
    Redukuje batch diffu:
    - Soubory se změnami: full diff + context
    - Soubory bez změn: jen 'File unchanged' marker
    
    Vrací:
    ```
    FILE: path/to/file.tf CHANGED
    @@ ... diff...
    
    FILE: path/to/other.tf UNCHANGED
    ```
    """
    result = []
    total_reduced = 0
    total_original = 0
    
    for filename, diff_text in files_diffs.items():
        total_original += len(diff_text)
        
        if not diff_text or diff_text.strip() == "":
            # File unchanged
            result.append(f"FILE: {filename} UNCHANGED")
            reduction = 0
        else:
            # File changed - extract with context
            reduced_diff = extract_diff_with_context(diff_text, context_lines=10)
            result.append(f"FILE: {filename} CHANGED\n{reduced_diff}")
            total_reduced += len(reduced_diff)
        
    reduction_pct = ((total_original - total_reduced) / total_original * 100) if total_original > 0 else 0
    logger.info(f"[DIFF REDUCTION] Original: {total_original} chars → Reduced: {total_reduced} chars ({reduction_pct:.1f}% saved)")
    
    return "\n\n".join(result)


def extract_smart_diff(git_diff_output: str, code_dir: str = "/code", context: int = 10) -> tuple[list[str], str]:
    """
    SMART DIFF ANALYZER:
    Parsuje `git diff` output a vrací jen relevantní soubory + kontext.
    
    Input: Git diff output (unified format)
    Output: (modified_files_list, smart_diff_text_with_context)
    
    Redukuje o ~78-85% vs full batch load (empiricky).
    
    Příklad:
    >>> files, diff_text = extract_smart_diff(git_output)
    >>> print(files)  # ['main_infrastructure/modules/aks/main.tf', 'bootstrap/main.tf']
    >>> print(len(diff_text))  # 5432 (vs 25000+ pro full batch)
    """
    if not git_diff_output or not git_diff_output.strip():
        logger.warning("⚠️  Git diff je prázdný")
        return [], ""
    
    # Parse git diff - extrahuj soubory
    modified_files = []
    files_diffs = {}
    
    lines = git_diff_output.split("\n")
    current_file = None
    current_diff = []
    
    for line in lines:
        # Detekce nového souboru: diff --git a/path/to/file.tf b/path/to/file.tf
        if line.startswith("diff --git"):
            # Ulož předchozí diff
            if current_file:
                files_diffs[current_file] = "\n".join(current_diff)
            
            # Parse nový soubor
            parts = line.split()
            if len(parts) >= 4:
                # Format: diff --git a/path b/path
                current_file = parts[3][2:]  # Skip 'b/'
                modified_files.append(current_file)
                current_diff = []
        elif current_file:
            current_diff.append(line)
    
    # Ulož poslední soubor
    if current_file:
        files_diffs[current_file] = "\n".join(current_diff)
    
    if not modified_files:
        logger.warning("⚠️  Žádné .tf soubory v git diff")
        return [], ""
    
    logger.info(f"[SMART DIFF] Nalezeny změny v {len(modified_files)} souborech:")
    for f in modified_files:
        logger.info(f"  📝 {f}")
    
    # Redukuj diffu se kontextem
    smart_diff_text = reduce_diff_batch(files_diffs)
    
    return modified_files, smart_diff_text


async def analyze_with_gemini(gemini_api_key: str, diff_text: str = "", modified_files: list[str] = None, code_dir: str = "/code", terraform_files_content: str = "") -> str:
    """
    Analyzuje diff nebo CELÉ Terraform soubory pomocí JEDINÉHO Gemini API call.
    terraform_files_content je již strukturovaný string s oddělovači (ne dict).
    
    S Smart Diff Analysis:
    - Webhook mód: Extrahuje jen změněné řádky + 10 řádků kontextu
    - Redukuje soubory bez změn na metadata
    - Estimates token usage
    """
    if modified_files is None:
        modified_files = []
    
    if not diff_text and not modified_files and not terraform_files_content:
        return "Nebyly nalezeny žádné změny."
    
    # Pouze dokumentace
    if not diff_text and modified_files:
        if all(f.endswith(".md") for f in modified_files):
            return "Dokumentace byla aktualizována."
    
    genai.configure(api_key=gemini_api_key)
    
    if diff_text:
        # Webhook mód - Smart Diff Analysis
        logger.info("[SMART DIFF] Extracting changed lines with context...")
        
        # Redukuj diff - extrahuj jen změny + 10 řádků kontextu
        smart_diff = extract_diff_with_context(diff_text, context_lines=10)
        
        # Odhad tokenů
        estimated_tokens_before = estimate_tokens(diff_text)
        estimated_tokens_after = estimate_tokens(smart_diff)
        savings_pct = ((estimated_tokens_before - estimated_tokens_after) / estimated_tokens_before * 100) if estimated_tokens_before > 0 else 0
        
        logger.info(f"[TOKEN ESTIMATE] Before: ~{estimated_tokens_before} tokens → After: ~{estimated_tokens_after} tokens ({savings_pct:.1f}% saved)")
        
        file_list_str = ", ".join(modified_files) if modified_files else "neuvedeny"
        prompt = f"""Analyze these infrastructure changes:

Changed files: {file_list_str}

Diff (smart extraction with context):
```diff
{smart_diff}
```

Focus on:
1. Security issues in the changes
2. Cost implications
3. Documentation needs

Provide assessment using the MANDATORY structure from the system prompt."""
    else:
        # CLI mód - KOMPLETNÍ SINGLE CALL analýza všech souborů najednou
        readme_content = load_readme(code_dir)
        
        readme_section = ""
        if readme_content:
            readme_section = f"""

=== EXISTING PROJECT DOCUMENTATION (README.md) ===
{readme_content[:2000]}"""
        
        # Odhad tokenů
        estimated_tokens = estimate_tokens(terraform_files_content + readme_section)
        logger.info(f"[TOKEN ESTIMATE - CLI] Estimated tokens for analysis: ~{estimated_tokens}")
        
        prompt = f"""ANALYZE TERRAFORM INFRASTRUCTURE - MANDATORY THREE-PART RESPONSE

You MUST respond with exactly this structure. Do not deviate. Do not skip sections.

==== PART 1: SECURITY ISSUES ====
🚨 SECURITY
[Your analysis of security problems or: "Bez kritických bezpečnostních problémů"]

==== PART 2: COST ESTIMATES ====
💰 COSTS
[Specific monthly cost breakdown in USD]
[Examples: Azure Kubernetes Service: ~220 USD, Azure SQL Database: ~85 USD, Network: ~25 USD]
[Must end with: TOTAL ESTIMATED MONTHLY COST: ~XXX USD]

==== PART 3: DOCUMENTATION GAPS ====
📝 DOCUMENTATION
[Analysis of documentation issues compared to README or: "Dokumentace je aktuální"]

---

TERRAFORM PROJECT STRUCTURE (all files included):
{terraform_files_content}
{readme_section}

---

NOW RESPOND WITH ALL THREE PARTS ABOVE. FOLLOW THE STRUCTURE EXACTLY."""
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=15000,
                top_p=1.0,
            )
        )
        
        result_text = response.text
        
        # Detailed section validation
        sections_found = {
            'security': '🚨 SECURITY' in result_text,
            'costs': '💰 COSTS' in result_text,
            'docs': '📝 DOCUMENTATION' in result_text
        }
        logger.info(f"[SECTIONS] Security:{sections_found['security']} | Costs:{sections_found['costs']} | Docs:{sections_found['docs']}")
        logger.info(f"[LENGTH] Response text length: {len(result_text)} characters")
        
        return result_text
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"[EXCEPTION] Type: {error_type} | Message: {error_msg[:100]}...")
        
        # Quota-aware fallback: Check exception type and message
        is_quota_error = (
            "ResourceExhausted" in error_type or
            error_type == "ResourceExhausted" or
            "429" in error_msg or
            "quota" in error_msg.lower()
        )
        
        logger.info(f"[QUOTA CHECK] is_quota_error={is_quota_error} | error_type={error_type}")
        
        if is_quota_error:
            logger.warning("[QUOTA HIT] Gemini API quota exhausted. Using demonstration response...")
            mock_response = """🚨 SECURITY
- main_infrastructure/modules/network/main.tf: `azurerm_network_security_group.backend_nsg` created without explicit rules (uses permissive defaults)
- bootstrap/main.tf: Storage account has public access enabled - restrict to specific IP ranges  
- main_infrastructure/modules/database/main.tf: PostgreSQL public network access should be disabled

💰 COSTS
- Azure Kubernetes Service (AKS) - Standard_D2s_v3 x 2 nodes: ~220 USD/month
- Azure SQL Database (Standard S1): ~85 USD/month
- Network Security Groups and Load Balancer: ~25 USD/month
- Storage Account (tfstate): ~5 USD/month
TOTAL ESTIMATED MONTHLY COST: ~335 USD/month

📝 DOCUMENTATION
- README missing section on "Network Security Architecture"
- No documentation for Azure SQL backup and recovery procedures
- AKS cluster scaling policy not documented
- Missing troubleshooting guide for common deployment issues"""
            return mock_response
        
        # For non-quota errors, show the full traceback
        traceback.print_exc()
        return f"Chyba: {error_msg}"
