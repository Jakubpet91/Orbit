"""
InfraGuard Sentinel - Production FastAPI Server
Automatic code review for GitHub PR and GitLab MR
Analyze changes when opening/updating PR/MR

Usage:
  uvicorn main:app --host 0.0.0.0 --port 8000

Webhooks:
  POST /webhook           -> GitHub PR webhook
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
from shared import analyze_with_gemini, extract_diff_with_context, estimate_tokens

# --- Configuration ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")

# Dynamic target branch filter (configurable in Render: e.g. "main" or "test")
TARGET_BRANCH_FILTER = os.getenv("TARGET_BRANCH_FILTER", "main")

if not GITHUB_TOKEN:
    raise ValueError("ERROR: Missing required environment variable: GEMINI_API_KEY")

if not GITHUB_TOKEN:
    logger.warning("WARNING: GITHUB_TOKEN missing, GitHub integration will be limited.")
if not GITLAB_TOKEN:
    logger.warning("WARNING: GITLAB_TOKEN missing, GitLab integration will be limited.")

app = FastAPI()


# --- GitHub Webhook ---

@app.post("/webhook")
async def github_webhook(request: Request):
    """GitHub webhook - analyzes PR and sends review."""
    try:
        if not GITHUB_TOKEN:
            raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not set.")

        payload = await request.json()
        logger.info("GitHub webhook received...")

        if "pull_request" not in payload or payload.get("action") not in ["opened", "synchronize"]:
            logger.info("Skipping webhook (not PR or action)")
            return {"status": "ignored"}

        # --- BRANCH FILTER ---
        target_branch = payload["pull_request"]["base"]["ref"]
        if target_branch != TARGET_BRANCH_FILTER:
            logger.info(f"Skipping PR: Target is {target_branch}, but filter is set to {TARGET_BRANCH_FILTER}")
            return {"status": "ignored", "reason": f"Target branch is not {TARGET_BRANCH_FILTER}"}

        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        
        logger.info(f"Analyzing {repo_name} PR #{pr_number} (Target: {target_branch})")
        
        # PyGithub - extrahuj diff z PR
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        diff_text = ""
        modified_files = []
        
        logger.info("[SMART DIFF] GitHub: Extracting PR files with smart diff...")
        for file in pr.get_files():
            modified_files.append(file.filename)
            patch = file.patch if file.patch else ""
            
            if patch:
                # Smart extraction: context + changes
                smart_patch = extract_diff_with_context(patch, context_lines=10)
                diff_text += f"--- {file.filename}\n{smart_patch}\n\n"
            else:
                # No patch = file only added/deleted symbolically
                diff_text += f"--- {file.filename} [No content change detected]\n\n"

        if not diff_text:
            logger.warning("WARNING: No text to analyze.")
            return {"status": "ok"}

        # Token estimate
        estimated_tokens = estimate_tokens(diff_text)
        logger.info(f"[TOKEN ESTIMATE] GitHub PR: ~{estimated_tokens} tokens to be used in Gemini call")
        
        # Analyze with Gemini
        analysis_result = await analyze_with_gemini(
            gemini_api_key=GEMINI_API_KEY,
            diff_text=diff_text,
            modified_files=modified_files,
            code_dir="/code",
            terraform_files_content=""
        )
        
        # Send comment to GitHub
        comment = f"""🤖 **InfraGuard Sentinel - Code Review**

{analysis_result}"""
        
        pr.create_issue_comment(comment)
        logger.info(f"SUCCESS: Review sent to GitHub PR #{pr_number}!")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"ERROR: Critical error in GitHub webhook: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "reason": str(e)}


# --- GitLab Webhook ---

@app.post("/webhook/gitlab")
async def webhook_gitlab(request: Request):
    """GitLab webhook for MR analysis."""
    try:
        if not GITLAB_TOKEN:
            raise HTTPException(status_code=500, detail="GITLAB_TOKEN is not set.")

        payload = await request.json()
        attrs = payload.get("object_attributes", {})
        
        if payload.get("object_kind") != "merge_request" or attrs.get("action") not in ["open", "reopen", "update"]:
            logger.info("Skipping GitLab webhook (not MR or action)")
            return {"status": "ignored"}

        # --- BRANCH FILTER ---
        target_branch = attrs.get("target_branch", "")
        if target_branch != TARGET_BRANCH_FILTER:
            logger.info(f"Skipping MR: Target is {target_branch}, but filter is set to {TARGET_BRANCH_FILTER}")
            return {"status": "ignored", "reason": f"Target branch is not {TARGET_BRANCH_FILTER}"}

        project_id = payload["project"]["id"]
        mr_iid = attrs["iid"]
        project_name = payload["project"]["path_with_namespace"]
        
        logger.info(f"Analyzing {project_name} MR #{mr_iid} (Target: {target_branch})")
        
        changes_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        
        async with httpx.AsyncClient() as client:
            headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
            response = await client.get(changes_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            
            changes_data = response.json()
            modified_files = []
            diff_text = ""
            
            logger.info("[SMART DIFF] GitLab: Extracting MR files with smart diff...")
            for change in changes_data.get("changes", []):
                new_path = change.get("new_path", "unknown")
                modified_files.append(new_path)
                
                patch = change.get("diff", "")
                if patch:
                    # Smart extraction: context + changes
                    smart_patch = extract_diff_with_context(patch, context_lines=10)
                    diff_text += f"--- {new_path}\n{smart_patch}\n\n"
                else:
                    diff_text += f"--- {new_path} [No content change detected]\n\n"

        if not diff_text:
            logger.warning("WARNING: No text to analyze in GitLab MR")
            return {"status": "ok"}

        # Token estimate
        estimated_tokens = estimate_tokens(diff_text)
        logger.info(f"[TOKEN ESTIMATE] GitLab MR: ~{estimated_tokens} tokens to be used in Gemini call")
        
        # Analysis
        analysis_result = await analyze_with_gemini(
            gemini_api_key=GEMINI_API_KEY,
            diff_text=diff_text,
            modified_files=modified_files,
            code_dir="/code",
            terraform_files_content=""
        )
        
        # Comment
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

        logger.info(f"SUCCESS: Review sent to GitLab MR #{mr_iid}!")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"ERROR: Critical error in GitLab webhook: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "reason": str(e)}


# --- Health Check Endpoints ---

@app.get("/")
def read_root():
    return {
        "service": "InfraGuard Sentinel",
        "version": "2.0",
        "mode": "production",
        "filter_active_on": TARGET_BRANCH_FILTER,
        "webhooks": [
            {"path": "/webhook", "type": "GitHub PR"},
            {"path": "/webhook/gitlab", "type": "GitLab MR"}
        ]
    }


@app.get("/health")
def health_check():
    """Health check for Render/monitoring."""
    return {
        "status": "healthy",
        "service": "InfraGuard Sentinel",
        "version": "2.0",
        "target_filter": TARGET_BRANCH_FILTER
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting InfraGuard Sentinel on port {port}...")
    logger.info(f"Active filter for target branch: {TARGET_BRANCH_FILTER}")
    uvicorn.run(app, host="0.0.0.0", port=port)