# backend/services/chat_service.py
import requests
from dotenv import load_dotenv
import os
load_dotenv()


# --- CONFIGURATION AZURE OPENAI ---
AZURE_OPENAI_URL = os.getenv("AZURE_OPENAI_URL")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

# Mémoire des conversations : { user_id: [ {"role": "...", "content": "..."} , ... ] }
CONVERSATIONS = {}

def init_conversation(user_id: str, question: str, answer: str) -> None:
    """
    Initialise l'historique de conversation pour un utilisateur
    après la première question RAG.
    """
    conversation_history = [
        {
            "role": "system",
            "content": (
                "Vous êtes un assistant fiscal expert en fiscalité française. "
                "Dans cette conversation, vous avez déjà utilisé des documents externes "
                "pour fournir une première réponse. Pour les questions suivantes, "
                "vous n'accéderez plus aux documents, mais vous garderez en mémoire "
                "le contexte de la discussion. Répondez de manière claire et concise, "
                "en conservant toutes les informations précédemment discutées."
            )
        },
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    CONVERSATIONS[user_id] = conversation_history

def continue_conversation(user_id: str, question: str) -> str:
    """
    Continue la conversation sans refaire de RAG.
    Renvoie la nouvelle réponse.
    """
    # On récupère l'historique pour cet utilisateur
    conversation_history = CONVERSATIONS.get(user_id, [])
    if not conversation_history:
        return f"Aucun historique trouvé pour l'utilisateur {user_id}."

    # On ajoute la nouvelle question de l'utilisateur
    conversation_history.append({"role": "user", "content": question})

    # Appel Azure OpenAI
    try:
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_KEY
        }

        data = {
            "messages": conversation_history,
            "temperature": 0.8,
            "max_tokens": 2000,
            "top_p": 0.95,
            "n": 1
        }

        response = requests.post(AZURE_OPENAI_URL, headers=headers, json=data, timeout=60)
        if response.status_code != 200:
            return f"Erreur OpenAI : {response.status_code} - {response.text}"

        json_resp = response.json()
        new_answer = json_resp["choices"][0]["message"]["content"]

        # On ajoute la réponse de l’assistant à l’historique
        conversation_history.append({"role": "assistant", "content": new_answer})

        # Mise à jour de la conversation
        CONVERSATIONS[user_id] = conversation_history

        return new_answer

    except Exception as e:
        return f"Erreur lors de l'appel Azure OpenAI : {e}"
