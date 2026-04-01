from dotenv import load_dotenv
load_dotenv()

import os
import httpx
from fastapi import FastAPI, Request, HTTPException
import logging
import traceback

# --- Konfigurace a Inicializace ---

# Nastavení logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Načtení tokenů z proměnných prostředí
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")

# Kontrola existence tokenů
if not GEMINI_API_KEY:
    raise ValueError("Chybí povinná proměnná prostředí: GEMINI_API_KEY")
if not GITHUB_TOKEN:
    logger.warning("Chybí GITHUB_TOKEN, GitHub integrace bude omezena.")
if not GITLAB_TOKEN:
    logger.warning("Chybí GITLAB_TOKEN, GitLab integrace bude omezena.")

app = FastAPI()

# --- Systémový Prompt pro Gemini v2.5 ---

SYSTEM_PROMPT = """
Jste InfraGuard Agent v2.5, Senior SRE a bezpečnostní architekt. Jste zodpovědný za produkční stabilitu a bezpečnost.
Vaším úkolem je analyzovat diffy a seznam změněných souborů.

Pravidla pro analýzu:
1.  **Struktura odpovědi:** Používejte VÝHRADNĚ tuto strukturu. Nezačínejte ničím jiným.
    ```
    🚨 KRITICKÉ:
    - (Vyjmenuj kritická rizika)

    ⚠️ VAROVÁNÍ:
    - (Vyjmenuj varování)

    ✅ INFO:
    - (Vyjmenuj informativní body)
    ```
2.  **Kategorizace rizik:**
    - `🚨 KRITICKÉ:` Jakékoliv heslo, API klíč, token, tajný klíč, nebo otevřený port (0.0.0.0). Piš jen: `Nalezeny přihlašovací údaje nebo nebezpečně vystavený port.`
    - `⚠️ VAROVÁNÍ:`
        - Změny v infrastruktuře (.tf, .hcl, k8s manifesty) bez odpovídající aktualizace v `.md` souboru. Piš: `Detekovány změny v infrastruktuře, které nejsou zaneseny v dokumentaci.`
        - Použití drahých/velkých instancí, neefektivní konfigurace, špatné SRE praktiky.
    - `✅ INFO:`
        - Pokud se mění POUZE dokumentace (např. `README.md`), napiš: `Dokumentace: Aktualizována.`
        - Pokud je vše v pořádku a nejsou žádná kritická rizika ani varování, napiš: `Vše v pořádku.`
3.  **Styl:** Buďte extrémně stručný, v odrážkách, bez omáčky.

Příklad kontextu, který dostanete:
- Seznam změněných souborů: main.tf, README.md, variables.tf
- Diff: [obsah diffu]

Vaším úkolem je na základě těchto vstupů vygenerovat strukturovanou odpověď.
"""

# --- Sdílená Logika (Gemini AI) ---

async def analyze_with_gemini(diff_text: str, modified_files: list[str]) -> str:
    """
    Odešle diff a seznam souborů k analýze do Gemini 1.5 Flash API.
    """
    if not diff_text and not modified_files:
        return "Nebyly nalezeny žádné změny."
    
    if not diff_text and modified_files:
        if all(f.endswith(".md") for f in modified_files):
             return "✅ INFO:\n- Dokumentace: Aktualizována."
        else:
            diff_text = "Pouze změna názvu souborů nebo jiné metadata."


    url = f"https://generativelaanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    file_list_str = ", ".join(modified_files)
    prompt_context = f"Kontext této změny:\n- Seznam změněných souborů: {file_list_str}\n\nAnalyzuj tento diff:\n\n```diff\n{diff_text}\n```"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt_context}"}]}],
        "generationConfig": {"temperature": 0.1, "topP": 1.0, "topK": 1, "maxOutputTokens": 2048}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=90)
            response.raise_for_status()
            
            result = response.json()
            if "candidates" in result and result["candidates"]:
                content_part = result["candidates"][0]["content"]["parts"][0]
                return content_part["text"]
            else:
                logger.error(f"Gemini API nevrátilo validní kandidáty. Odpověď: {result}")
                return "Chyba: Gemini API nevrátilo obsah."

        except Exception:
            logger.error(f"Chyba při volání Gemini API. Payload: {payload}")
            # Vypíše kompletní traceback do logu pro detailní debugging
            traceback.print_exc()
            return "Chyba: Nepodařilo se zpracovat požadavek na Gemini API. Více detailů v logu serveru."

# --- Webhooky ---

@app.post("/webhook/github")
async def webhook_github(request: Request):
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN není nastaven.")

    payload = await request.json()
    action = payload.get("action")
    if payload.get("pull_request") is None or action not in ["opened", "synchronize"]:
        return {"status": "ignored"}

    pr_data = payload["pull_request"]
    pr_url = pr_data["url"]
    comments_url = pr_data["comments_url"]
    repo_url = pr_data["head"]["repo"]["url"]
    files_url = f"{pr_url}/files"

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        
        # Získání diffu
        diff_headers = {**headers, "Accept": "application/vnd.github.v3.diff"}
        diff_response = await client.get(pr_url, headers=diff_headers)
        
        # Získání seznamu souborů
        files_response = await client.get(files_url, headers=headers)
        
        if diff_response.status_code != 200 or files_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Nepodařilo se získat data z GitHubu.")
            
        diff_text = diff_response.text
        modified_files = [f["filename"] for f in files_response.json()]

    # Analýza a odeslání komentáře
    analysis_result = await analyze_with_gemini(diff_text, modified_files)
    comment_payload = {"body": analysis_result}
    
    async with httpx.AsyncClient() as client:
        await client.post(comments_url, json=comment_payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})

    return {"status": "success"}

@app.post("/webhook/gitlab")
async def webhook_gitlab(request: Request):
    if not GITLAB_TOKEN:
        raise HTTPException(status_code=500, detail="GITLAB_TOKEN není nastaven.")

    payload = await request.json()
    attrs = payload.get("object_attributes", {})
    if payload.get("object_kind") != "merge_request" or attrs.get("action") not in ["open", "reopen", "update"]:
        return {"status": "ignored"}

    project_id = payload["project"]["id"]
    mr_iid = attrs["iid"]
    
    changes_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
    
    async with httpx.AsyncClient() as client:
        headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
        response = await client.get(changes_url, headers=headers)
        response.raise_for_status()
        
        changes_data = response.json()
        diff_text = "\n".join([c.get("diff", "") for c in changes_data.get("changes", [])])
        modified_files = [c.get("new_path") for c in changes_data.get("changes", [])]

    # Analýza a odeslání komentáře
    analysis_result = await analyze_with_gemini(diff_text, modified_files)
    notes_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    
    async with httpx.AsyncClient() as client:
        await client.post(notes_url, json={"body": analysis_result}, headers={"PRIVATE-TOKEN": GITLAB_TOKEN})

    return {"status": "success"}

@app.get("/")
def read_root():
    return {"message": "InfraGuard Agent v2.5 je online."}
