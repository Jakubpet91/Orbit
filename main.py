import os
from fastapi import FastAPI, Request
import uvicorn
from openai import OpenAI
from github import Github

app = FastAPI()

# KONFIGURACE - Render si je vytáhne z "Environment Variables"
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

client = OpenAI(api_key=OPENAI_KEY)
g = Github(GITHUB_TOKEN)

@app.get("/")
async def root():
    return {"message": "InfraGuard AI is running!"}

@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.json()
    
    if "pull_request" in payload and payload.get("action") in ["opened", "synchronize"]:
        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        
        print(f"🤖 Analyzuji PR #{pr_number} v {repo_name}...")
        
        try:
            repo = g.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            diff_text = ""
            files = pr.get_files()
            for file in files:
                diff_text += f"Soubor: {file.filename}\n{file.patch}\n\n"

            prompt = f"""Jsi expert na infrastrukturu a Terraform. 
            Zkontroluj následující změny v kódu. Zaměř se na:
            1. Bezpečnostní rizika (otevřené porty, chybějící šifrování).
            2. Nákladovou efektivitu (zbytečně drahé instance).
            3. Best practices.
            
            Změny v PR:
            {diff_text}
            
            Napiš krátký, věcný komentář pro vývojáře v češtině. Pokud je vše v pořádku, jen pochval."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            
            ai_review = response.choices[0].message.content
            pr.create_issue_comment(f"🤖 **InfraGuard AI Review:**\n\n{ai_review}")
            print("✅ Recenze odeslána!")
            
        except Exception as e:
            print(f"❌ Chyba při zpracování: {e}")

    return {"status": "ok"}

if __name__ == "__main__":
    # Render nastavuje port dynamicky přes proměnnou PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)