// frontend/static/script.js

document.addEventListener("DOMContentLoaded", () => {
  // --- Sélecteurs du DOM ---
  const askBtn = document.getElementById("askBtn");
  const continueBtn = document.getElementById("continueBtn");
  const questionInput = document.getElementById("questionInput");
  const answerBox = document.getElementById("answerBox");
  const continueRow = document.getElementById("continueRow");

  // Section chat
  const chatSection = document.getElementById("chatSection");
  const chatWindow = document.getElementById("chatWindow");
  const chatInput = document.getElementById("chatInput");
  const sendChatBtn = document.getElementById("sendChatBtn");

  // Boutons microphone
  const micBtn = document.getElementById("micBtn");
  const micChatBtn = document.getElementById("micChatBtn");

  // Identifiant "fixe" de session
  const userId = "demo_user";

  // Indicateur : la conversation a-t-elle déjà commencé ?
  let conversationStarted = false;

  // Variables pour la reconnaissance vocale
  let recognition;
  let isListening = false;

  // Variables pour accumuler les transcriptions finales
  let accumulatedFinalTranscriptFirstQuestion = "";
  let accumulatedFinalTranscriptChat = "";

  // Écouteurs pour détecter les modifications manuelles de l'utilisateur
  questionInput.addEventListener('input', () => {
    accumulatedFinalTranscriptFirstQuestion = questionInput.value;
  });

  chatInput.addEventListener('input', () => {
    accumulatedFinalTranscriptChat = chatInput.value;
  });

  // Vérification de la compatibilité de l'API Web Speech
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = true; // Activer les résultats intermédiaires
    recognition.continuous = true; // Permettre une reconnaissance continue

    // Gestion des résultats de la reconnaissance
    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const result = event.results[i];
        const transcript = result[0].transcript;

        if (result.isFinal) {
          finalTranscript += transcript + ' ';
          if (!conversationStarted) {
            accumulatedFinalTranscriptFirstQuestion += transcript + ' ';
          } else {
            accumulatedFinalTranscriptChat += transcript + ' ';
          }
        } else {
          interimTranscript += transcript;
        }
      }

      if (!conversationStarted) {
        // Mettre à jour le champ de saisie avec le texte accumulé + interim
        questionInput.value = accumulatedFinalTranscriptFirstQuestion + interimTranscript;
      } else {
        // Mettre à jour le champ de saisie du chat avec le texte accumulé + interim
        chatInput.value = accumulatedFinalTranscriptChat + interimTranscript;
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      alert("Erreur de reconnaissance vocale : " + event.error);
      toggleMic(false, event.target === recognition);
    };

    recognition.onend = () => {
      if (isListening) {
        // Redémarrer la reconnaissance si elle s'arrête involontairement
        recognition.start();
      }
    };
  } else {
    // API non supportée
    micBtn.disabled = true;
    micChatBtn.disabled = true;
    alert("Votre navigateur ne supporte pas la reconnaissance vocale.");
  }

  // Fonction pour démarrer ou arrêter la reconnaissance vocale
  function toggleMic(active, isChat = false) {
    if (!recognition) return;

    if (active) {
      recognition.start();
      isListening = true;
      if (isChat) {
        micChatBtn.classList.add("active");
        micChatBtn.title = "Arrêter l'écoute";
      } else {
        micBtn.classList.add("active");
        micBtn.title = "Arrêter l'écoute";
      }
    } else {
      recognition.stop();
      isListening = false;
      if (isChat) {
        micChatBtn.classList.remove("active");
        micChatBtn.title = "Activer le micro";
      } else {
        micBtn.classList.remove("active");
        micBtn.title = "Activer le micro";
      }
    }
  }

  // --- 1) Première question (RAG) ---
  askBtn.addEventListener("click", async () => {
    const questionValue = questionInput.value.trim();
    if (!questionValue) {
      alert("Veuillez entrer une question.");
      return;
    }

    // On affiche un petit message de chargement
    answerBox.innerHTML = "<em>Réflexion...</em>";

    try {
      const resp = await fetch("/ask-rag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          question: questionValue
        })
      });

      const data = await resp.json();
      if (data.error) {
        answerBox.innerHTML = `<b>Erreur :</b> ${data.error}`;
      } else {
        // Afficher la réponse en Markdown => HTML
        const rendered = marked.parse(data.answer || "*Aucune réponse.*");
        answerBox.innerHTML = rendered;

        // On affiche le bouton "Continuer la conversation"
        continueRow.style.display = "block";
      }
    } catch (error) {
      console.error(error);
      answerBox.innerHTML = `<b>Erreur :</b> ${error.message}`;
    }
  });

  // --- 2) Bouton "Continuer la conversation" ---
  continueBtn.addEventListener("click", () => {
    conversationStarted = true;

    // Transférer le premier message de l'utilisateur dans le chatWindow
    const initialQuestion = questionInput.value.trim();
    if (initialQuestion) {
      addMessageBubble("user", initialQuestion);
    }

    // Transférer la réponse de l'IA dans le chatWindow
    const initialAnswer = answerBox.innerHTML;
    addMessageBubble("assistant", initialAnswer);

    // On masque la section de la première question
    firstQuestionSection.style.display = "none";
    // On affiche la zone de chat
    chatSection.style.display = "flex";
    // On vide la zone de réponse initiale
    answerBox.innerHTML = "";
    // On vide la zone de saisie initiale
    questionInput.value = "";
  });

  // --- 3) Gestion du Chat (sans RAG) ---
  // Envoi du message au clic sur "Envoyer"
  sendChatBtn.addEventListener("click", sendChatMessage);

  // Possibilité d'envoyer le message avec la touche Enter
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  // Gestion des clics sur les boutons microphone
  micBtn.addEventListener("click", () => {
    toggleMic(!isListening, false);
  });

  micChatBtn.addEventListener("click", () => {
    toggleMic(!isListening, true);
  });

  async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // 1) On affiche la "bulle user" dans la fenêtre de chat
    addMessageBubble("user", message);
    chatInput.value = "";

    // 2) On envoie au backend (route /chat-continue)
    try {
      const resp = await fetch("/chat-continue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          question: message
        })
      });

      const data = await resp.json();
      if (data.error) {
        // On affiche l'erreur comme si c'était une bulle "assistant"
        addMessageBubble("assistant", `**Erreur :** ${data.error}`);
      } else {
        addMessageBubble("assistant", data.answer || "Aucune réponse.");
      }
      // Ne pas forcer le scroll automatique ici
    } catch (err) {
      console.error(err);
      addMessageBubble("assistant", `**Erreur de connexion :** ${err.message}`);
      // Ne pas forcer le scroll automatique ici
    }
  }

  // Fonction utilitaire : ajout d'une bulle (user ou assistant)
  function addMessageBubble(role, text) {
    // On parse le Markdown
    const htmlContent = marked.parse(text);

    // Création de l'élément bulle
    const bubble = document.createElement("div");
    bubble.classList.add("message-bubble", role);
    bubble.innerHTML = htmlContent;

    // On l'ajoute au chatWindow
    chatWindow.appendChild(bubble);

    // Scroll automatique uniquement si c'est une réponse de l'assistant
    if (role === "assistant") {
      // Vérifie si l'utilisateur est déjà en bas
      const isAtBottom = chatWindow.scrollHeight - chatWindow.clientHeight <= chatWindow.scrollTop + 1;
      if (isAtBottom) {
        chatWindow.scrollTop = chatWindow.scrollHeight;
      }
    }
  }
});
