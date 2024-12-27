# backend/main.py

import os
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from .services.rag_service import ask_with_rag
from .services.chat_service import init_conversation, continue_conversation

# =========================
# Chargement des variables d'environnement
# =========================
load_dotenv()  # Charge les variables depuis le fichier .env

# On récupère nos secrets
VALID_PASSWORD = os.getenv("VALID_PASSWORD", "demo1234")
SECRET_KEY = os.getenv("SECRET_KEY", "SECRET_KEY_DEMO")

# =========================
# Configuration et app
# =========================

app = FastAPI(title="RAG + Chat", version="1.0.0")

# -- Définition des chemins absolus dynamiques --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Chemin vers /backend
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")    # Chemin vers /frontend
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")        # Chemin vers /frontend/static

# Vérifiez que les dossiers existent
if not os.path.exists(FRONTEND_DIR):
    raise RuntimeError(f"Le dossier frontend '{FRONTEND_DIR}' n'existe pas.")
if not os.path.exists(STATIC_DIR):
    raise RuntimeError(f"Le dossier statique '{STATIC_DIR}' n'existe pas.")

# -- Montage des fichiers statiques (CSS, JS, etc.) --
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# -- Middleware de session --
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="session_rag")

# =========================
# Routes login / logout
# =========================

@app.get("/login", response_class=HTMLResponse)
def get_login_page():
    """
    Retourne la page de login (login.html).
    """
    file_path = os.path.join(FRONTEND_DIR, "login.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Page login introuvable")
    return FileResponse(file_path)

@app.post("/login")
def do_login(request: Request, password: str = Form(...)):
    """
    Vérifie le mot de passe envoyé par l'utilisateur.
    Si correct, on stocke l'info dans la session ; sinon, 401.
    """
    if password == VALID_PASSWORD:
        request.session["logged_in"] = True
        # Retour JSON si le front-end veut gérer l'affichage
        # ou redirection si on préfère la méthode classique
        return JSONResponse({"success": True}, status_code=200)
    else:
        return JSONResponse({"detail": "Mot de passe incorrect."}, status_code=401)

@app.get("/logout")
def logout(request: Request):
    """
    Déconnecte l'utilisateur (supprime la session).
    """
    request.session.clear()
    return RedirectResponse(url="/login")

# =========================
# Route principale (index)
# =========================

@app.get("/", response_class=HTMLResponse)
def serve_index(request: Request):
    """
    Retourne index.html UNIQUEMENT si l'utilisateur est connecté.
    """
    if not request.session.get("logged_in"):
        return RedirectResponse(url="/login")

    file_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Fichier index.html introuvable.")

# =========================
# Routes RAG
# =========================

@app.post("/ask-rag")
async def ask_rag_endpoint(request: Request):
    """
    Première question : exécute la recherche RAG (Azure Search + GPT),
    puis initialise la conversation pour l'utilisateur.
    """
    if not request.session.get("logged_in"):
        return JSONResponse({"error": "Non authentifié"}, status_code=401)

    data = await request.json()
    question = data.get("question", "")
    user_id = data.get("user_id", "demo_user")

    if not question:
        return JSONResponse({"error": "Aucune question fournie."}, status_code=400)

    documents, answer = ask_with_rag(question)

    if not documents and "Erreur" in answer:
        return JSONResponse({"error": answer}, status_code=500)

    init_conversation(user_id, question, answer)
    return JSONResponse({"answer": answer})

@app.post("/chat-continue")
async def chat_continue_endpoint(request: Request):
    """
    Questions suivantes : ne refait pas de RAG, 
    mais continue la conversation en tenant compte de l'historique.
    """
    if not request.session.get("logged_in"):
        return JSONResponse({"error": "Non authentifié"}, status_code=401)

    data = await request.json()
    user_id = data.get("user_id", "demo_user")
    question = data.get("question", "")

    if not question:
        return JSONResponse({"error": "Aucune question fournie."}, status_code=400)

    new_answer = continue_conversation(user_id, question)
    if new_answer.startswith("Aucun historique"):
        return JSONResponse({"error": new_answer}, status_code=400)

    return JSONResponse({"answer": new_answer})

# =========================
# Lancement serveur
# =========================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

