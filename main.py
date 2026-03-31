import os
from fastapi import FastAPI, Request
import uvicorn
import google.generativeai as genai
from github import Github

app = FastAPI()

# KONFIGURACE
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

genai.configure(api_key=GEMINI_KEY, transport='rest') 

# Použijeme tento specifický název, který v1 API miluje
model = genai.GenerativeModel('gemini-1.5-flash') 
g = Github(GITHUB_TOKEN)

@app.get("/")
async def root():
    return {"status": "running"}

@app.post("/webhook")
async def github_webhook(request: Request):
    try:
        payload = await request.json()
        
        # Logování pro nás, abychom věděli, že data dorazila
        print("📥 Přijat webhook z GitHubu...")

        if "pull_request" in payload and payload.get("action") in ["opened", "synchronize"]:
            repo_name = payload["repository"]["full_name"]
            pr_number = payload["pull_request"]["number"]
            
            print(f"🤖 Analyzuji {repo_name} PR #{pr_number}")
            
            repo = g.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            diff_text = ""
            for file in pr.get_files():
                diff_text += f"Soubor: {file.filename}\n{file.patch}\n\n"

            prompt = f"Jsi expert na infrastrukturu. Zkontroluj kód a napiš krátký český komentář:\n\n{diff_text}"

            response = model.generate_content(prompt)
            ai_review = response.text

            pr.create_issue_comment(f"🤖 **InfraGuard Gemini Review:**\n\n{ai_review}")
            print(f"✅ Recenze úspěšně odeslána na GitHub!")
            
    except Exception as e:
        # TOHLE JE KLÍČOVÉ - vypíše to chybu do Render logu!
        print(f"❌ CHYBA: {str(e)}")
        return {"status": "error", "reason": str(e)}

    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
