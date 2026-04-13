"""
InfraGuard Sentinel - Production FastAPI Server
Automatické code review pro GitHub PR a GitLab MR
Analýza změn při otevření/aktualizaci PR/MR

Použití:
  uvicorn main:app --host 0.0.0.0 --port 8000

Webhooks:
  POST /webhook          -> GitHub PR webhook
  POST /webhook/gitlab   -> GitLab MR webhook
  GET /health            -> Health check endpoint
"""

import os
import logging
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from github import Github
import httpx

# Load environment
load_dotenv()

# Import shared logic
from shared import analyze_with_gemini

# --- Konfigurace ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")

if not GEMINI_API_KEY:
    raise ValueError("❌ Chybí povinná proměnná prostředí: GEMINI_API_KEY")

if not GITHUB_TOKEN:
    logger.warning("⚠️  Chybí GITHUB_TOKEN, GitHub integrace bude omezena.")
if not GITLAB_TOKEN:
    logger.warning("⚠️  Chybí GITLAB_TOKEN, GitLab integrace bude omezena.")

app = FastAPI()


# --- GitHub Webhook ---

@app.post("/webhook")
async def github_webhook(request: Request):
    """GitHub webhook - analyzuje PR a posílá review."""
    try:
        if not GITHUB_TOKEN:
            raise HTTPException(status_code=500, detail="GITHUB_TOKEN není nastaven.")

        payload = await request.json()
        logger.info("📥 Přijat GitHub webhook...")

        if "pull_request" not in payload or payload.get("action") not in ["opened", "synchronize"]:
            logger.info("⏭️  Ignoruji webhook (není PR nebo action)")
            return {"status": "ignored"}

        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        
        logger.info(f"🤖 Analyzuji {repo_name} PR #{pr_number}")
        
        # PyGithub - extrahuj diff z PR
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        diff_text = ""
        modified_files = []
        
        for file in pr.get_files():
            modified_files.append(file.filename)
            patch = file.patch if file.patch else "Změna obsahu není k dispozici."
            diff_text += f"Soubor: {file.filename}\n{patch}\n\n"

        if not diff_text:
            logger.warning("⚠️  Žádný text k analýze.")
            return {"status": "ok"}

        logger.info(f"📊 Odesílám na Gemini ({len(diff_text)} znaků)...")
        
        # Analyze with Gemini
        analysis_result = await analyze_with_gemini(
            gemini_api_key=GEMINI_API_KEY,
            diff_text=diff_text,
            modified_files=modified_files,
            code_dir="/code",
            terraform_files_content=""
        )
        
        # Odeslání komentáře na GitHub
        comment = f"""🤖 **InfraGuard Sentinel - Code Review**

{analysis_result}"""
        
        pr.create_issue_comment(comment)
        logger.info(f"✅ Recenze odeslána na GitHub PR #{pr_number}!")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ KRITICKÁ CHYBA v GitHub webhook: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "reason": str(e)}


# --- GitLab Webhook ---

@app.post("/webhook/gitlab")
async def webhook_gitlab(request: Request):
    """GitLab webhook pro MR analýzu."""
    try:
        if not GITLAB_TOKEN:
            raise HTTPException(status_code=500, detail="GITLAB_TOKEN není nastaven.")

        payload = await request.json()
        attrs = payload.get("object_attributes", {})
        
        if payload.get("object_kind") != "merge_request" or attrs.get("action") not in ["open", "reopen", "update"]:
            logger.info("⏭️  Ignoruji GitLab webhook (není MR nebo action)")
            return {"status": "ignored"}

        project_id = payload["project"]["id"]
        mr_iid = attrs["iid"]
        project_name = payload["project"]["path_with_namespace"]
        
        logger.info(f"🤖 Analyzuji {project_name} MR #{mr_iid}")
        
        changes_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        
        async with httpx.AsyncClient() as client:
            headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
            response = await client.get(changes_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            
            changes_data = response.json()
            diff_text = "\n".join([c.get("diff", "") for c in changes_data.get("changes", [])])
            modified_files = [c.get("new_path") for c in changes_data.get("changes", [])]

        if not diff_text:
            logger.warning("⚠️  Žádný text k analýze v GitLab MR")
            return {"status": "ok"}

        logger.info(f"📊 Odesílám na Gemini ({len(diff_text)} znaků)...")
        
        # Analýza
        analysis_result = await analyze_with_gemini(
            gemini_api_key=GEMINI_API_KEY,
            diff_text=diff_text,
            modified_files=modified_files,
            code_dir="/code",
            terraform_files_content=""
        )
        
        # Komentář
        comment = f"""🤖 **InfraGuard Sentinel - Code Review**

{analysis_result}"""
        
        notes_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
        async with httpx.AsyncClient() as client:
            await client.post(
                notes_url,
                json={"body": comment},
                headers={"PRIVATE-TOKEN": GITLAB_TOKEN},
                timeout=30.0
            )

        logger.info(f"✅ Recenze odeslána na GitLab MR #{mr_iid}!")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ KRITICKÁ CHYBA v GitLab webhook: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "reason": str(e)}


# --- Health Check Endpoints ---

@app.get("/")
def read_root():
    return {
        "service": "InfraGuard Sentinel",
        "version": "2.0",
        "mode": "production",
        "webhooks": [
            {"path": "/webhook", "type": "GitHub PR"},
            {"path": "/webhook/gitlab", "type": "GitLab MR"}
        ]
    }


@app.get("/health")
def health_check():
    """Health check pro Render/monitoring."""
    return {
        "status": "healthy",
        "service": "InfraGuard Sentinel",
        "version": "2.0"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Spouštím InfraGuard Sentinel na portu {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
