// frontend/static/login.js

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const errorMsg = document.getElementById('errorMsg');
    const togglePasswordBtn = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    const eyeIcon = togglePasswordBtn.querySelector('.bi-eye');
    const eyeSlashIcon = togglePasswordBtn.querySelector('.bi-eye-slash');
  
    // Gestion de l'affichage du mot de passe
    togglePasswordBtn.addEventListener('click', () => {
      const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', type);
      
      // Toggle active class pour changer l'icône
      togglePasswordBtn.classList.toggle('active');
      
      // Changer l'icône
      if (passwordInput.getAttribute('type') === 'password') {
        eyeIcon.style.display = 'inline';
        eyeSlashIcon.style.display = 'none';
      } else {
        eyeIcon.style.display = 'none';
        eyeSlashIcon.style.display = 'inline';
      }
    });
  
    // Initialiser les icônes au chargement
    eyeSlashIcon.style.display = 'none';
  
    // Gestion de la soumission du formulaire avec affichage des erreurs
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault(); // Empêche la soumission classique du formulaire
  
      const formData = new FormData(loginForm);
      const password = formData.get('password');
  
      try {
        const response = await fetch('/login', {
          method: 'POST',
          body: formData,
        });
  
        if (response.ok) {
          // Si la connexion est réussie, redirige vers la page principale
          window.location.href = "/";
        } else {
          // Si la réponse n'est pas OK, affiche l'erreur
          const data = await response.json();
          errorMsg.textContent = data.detail || 'Erreur de connexion.';
          errorMsg.style.display = 'block';
        }
      } catch (error) {
        console.error('Erreur lors de la connexion :', error);
        errorMsg.textContent = 'Erreur de connexion.';
        errorMsg.style.display = 'block';
      }
    });
});
