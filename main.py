import os
from fastapi import FastAPI, Request
import uvicorn
import google.generativeai as genai
from github import Github

app = FastAPI()

# KONFIGURACE
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Každý z těchto tří musí být na vlastním řádku:
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')
g = Github(GITHUB_TOKEN)

@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.json()
    
    if "pull_request" in payload and payload.get("action") in ["opened", "synchronize"]:
        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        diff_text = ""
        for file in pr.get_files():
            diff_text += f"Soubor: {file.filename}\n{file.patch}\n\n"

        prompt = f"Jsi expert na infrastrukturu. Zkontroluj tento kód (bezpečnost, cena, best practices) a napiš krátký český komentář pro vývojáře:\n\n{diff_text}"

        # Volání Gemini
        response = model.generate_content(prompt)
        ai_review = response.text

        pr.create_issue_comment(f"🤖 **InfraGuard Gemini Review:**\n\n{ai_review}")
        print(f"✅ Recenze pro {repo_name} PR #{pr_number} odeslána!")

    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)