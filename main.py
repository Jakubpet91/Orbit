import os
from fastapi import FastAPI, Request
import uvicorn
import google.generativeai as genai
from github import Github
import httpx

app = FastAPI()

# KONFIGURACE
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Jednoduchá konfigurace
genai.configure(api_key=GEMINI_KEY)

# Použijeme model Flash - v roce 2026 je to nejstabilnější volba
model = genai.GenerativeModel('gemini-1.5-flash')
g = Github(GITHUB_TOKEN)

@app.get("/")
async def root():
    return {"status": "running"}

@app.post("/webhook")
async def github_webhook(request: Request):
    try:
        payload = await request.json()
        print("📥 Přijat webhook...")

        if "pull_request" in payload and payload.get("action") in ["opened", "synchronize"]:
            repo_name = payload["repository"]["full_name"]
            pr_number = payload["pull_request"]["number"]
            
            print(f"🤖 Analyzuji {repo_name} PR #{pr_number}")
            
            repo = g.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            diff_text = ""
            for file in pr.get_files():
                # Někdy je patch None (u velkých nebo binárních souborů)
                patch = file.patch if file.patch else "Změna obsahu není k dispozici."
                diff_text += f"Soubor: {file.filename}\n{patch}\n\n"

            if not diff_text:
                print("⚠️ Žádný text k analýze.")
                return {"status": "ok"}

            # PŘÍMÉ VOLÁNÍ GEMINI 2.5 (Vynutíme v1)
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{
                    "parts": [{"text": f"Jsi expert na IT infrastrukturu. Udělej krátkou a věcnou českou recenzi tohoto kódu z hlediska bezpečnosti a efektivity:\n\n{diff_text}"}]
                }]
            }

            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=data, headers=headers, timeout=30.0)
                result = res.json()
                
                if res.status_code != 200:
                    print(f"❌ Detail chyby od Googlu: {result}")
                    raise Exception(f"Google API Error {res.status_code}")
                
                # Bezpečné vytažení textu z odpovědi
                try:
                    ai_review = result['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    print(f"❌ Divná odpověď od Googlu: {result}")
                    raise Exception("Nepodařilo se přečíst odpověď od AI.")

            # Odeslání na GitHub
            pr.create_issue_comment(f"🤖 **InfraGuard (Gemini 2.5 Flash) Review:**\n\n{ai_review}")
            print(f"✅ Recenze odeslána na GitHub!")
            
    except Exception as e:
        print(f"❌ KRITICKÁ CHYBA: {str(e)}")
        import traceback
        traceback.print_exc() # Tohle nám do logu vypíše přesně, kde to ruplo
        return {"status": "error", "reason": str(e)}

    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
