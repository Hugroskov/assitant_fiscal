# backend/services/rag_service.py
import requests
from typing import Tuple, List
import os
from dotenv import load_dotenv

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

AZURE_OPENAI_URL = os.getenv("AZURE_OPENAI_URL")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
MAX_CHARS_PER_DOC = 1200
TOP_DOCUMENTS = 3

def ask_with_rag(question: str) -> Tuple[List[str], str]:
    """
    1) Effectue une recherche sur Azure Cognitive Search
    2) Appelle Azure OpenAI (modèle GPT-4) en injectant les documents trouvés en contexte
    3) Retourne la liste des documents + la réponse
       ou ([], <message d'erreur>) si problème.
    """
    # --- Étape 1 : Recherche Azure ---
    search_headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_SEARCH_API_KEY
    }
    search_query = {
        "search": question,
        "top": TOP_DOCUMENTS
    }
    search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{AZURE_SEARCH_INDEX}/docs/search?api-version=2021-04-30-Preview"

    try:
        search_response = requests.post(search_url, json=search_query, headers=search_headers, timeout=30)
        if search_response.status_code != 200:
            return [], f"Erreur Search : {search_response.status_code} - {search_response.text}"
        search_results = search_response.json()
    except Exception as e:
        return [], f"Exception lors de l'appel à Azure Search : {e}"

    # Extraction/tronquage des documents
    raw_documents = []
    for doc in search_results.get("value", []):
        doc_text = f"{doc.get('title', '')} : {doc.get('content', '') or doc.get('text', '')}"
        if len(doc_text) > MAX_CHARS_PER_DOC:
            doc_text = doc_text[:MAX_CHARS_PER_DOC] + "..."
        raw_documents.append(doc_text)

    # Si aucun document
    if not raw_documents:
        raw_documents = ["Aucun document pertinent trouvé."]
    context = "\n".join(raw_documents)

    # --- Étape 2 : Appel Azure OpenAI ---
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Vous êtes un assistant fiscal expert en fiscalité française. "
                    "tu es une IA qui sert d'aasistant aux conseillers en patrimoine, experts comptables, avocats fiscaux"
                    "Votre rôle est de fournir des réponses claires, précises et personnalisées "
                    "en matière d'optimisation fiscale, en tenant compte des lois en vigueur "
                    "(Code Général des Impôts, BOFiP, etc.). "
                    "Répondez de manière concise et pratique, en priorisant les solutions applicables."
                )
            },
            {
                "role": "user",
                "content": f"Voici le contexte :\n{context}\n\nQuestion : {question}"
            }
        ]

        data = {
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500,
            "top_p": 0.95,
            "n": 1
        }
        openai_headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_KEY
        }

        response = requests.post(AZURE_OPENAI_URL, headers=openai_headers, json=data, timeout=60)
        if response.status_code == 200:
            json_resp = response.json()
            answer = json_resp["choices"][0]["message"]["content"]
            return raw_documents, answer
        else:
            return raw_documents, f"Erreur OpenAI : {response.status_code} - {response.text}"

    except Exception as e:
        return raw_documents, f"Erreur lors de l'appel Azure OpenAI : {e}"
