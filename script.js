$; // Configuration - À adapter selon ton environnement Grist
const CONFIG = {
  // Ces valeurs seront récupérées depuis le Custom Widget Grist
  gristDocId: null,
  gristTableId: "Demarche_134359_repetable_informations_enfant",
  gristAccessToken: null,
  gristServer: "https://grist.numerique.gouv.fr",

  // Polling interval (ms)
  refreshInterval: 5000,

  // API endpoints (Vercel serverless functions)
  apiEndpoints: {
    process: "/api/process",
    status: "/api/status",
  },
};

// État global
let isProcessing = false;
let refreshTimer = null;

// Initialize Grist Custom Widget
async function initGristWidget() {
  try {
    // Attendre que Grist soit prêt
    await grist.ready();

    // Récupérer l'access token et doc ID depuis Grist
    const table = await grist.selectedTable.getTableId();
    const accessToken = await grist.docApi.getAccessToken();

    CONFIG.gristTableId = table;
    CONFIG.gristAccessToken = accessToken;

    // Récupérer le doc ID depuis l'URL
    const urlParams = new URLSearchParams(window.location.search);
    CONFIG.gristDocId = urlParams.get("docId") || getDocIdFromUrl();

    console.log("✅ Grist widget initialized");

    // Charger les stats initiales
    await loadStats();

    // Démarrer le refresh automatique
    startAutoRefresh();
  } catch (error) {
    console.error("❌ Erreur initialisation Grist:", error);
    // Fallback si pas dans Grist (développement local)
    console.log("⚠️ Mode développement - utilisation config par défaut");
  }
}

// Récupérer le doc ID depuis l'URL
function getDocIdFromUrl() {
  const url = window.location.href;
  const match = url.match(/\/doc\/([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

// Charger les statistiques depuis l'API
async function loadStats() {
  try {
    showStatus("Chargement des statistiques...", "info");

    // Appeler l'API stats
    const url = new URL("/api/stats", window.location.origin);

    // Ajouter les paramètres si disponibles
    if (CONFIG.gristDocId)
      url.searchParams.append("gristDocId", CONFIG.gristDocId);
    if (CONFIG.gristTableId)
      url.searchParams.append("gristTableId", CONFIG.gristTableId);
    if (CONFIG.gristAccessToken)
      url.searchParams.append("gristAccessToken", CONFIG.gristAccessToken);
    if (CONFIG.gristServer)
      url.searchParams.append("gristServer", CONFIG.gristServer);

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Erreur inconnue");
    }

    // Mettre à jour l'interface
    updateStatsDisplay(data.stats);

    hideStatus();
  } catch (error) {
    console.error("❌ Erreur chargement stats:", error);
    showStatus("Erreur lors du chargement des statistiques", "error");
  }
}

// Mettre à jour l'affichage des stats
function updateStatsDisplay(stats) {
  document.getElementById("total-value").textContent = stats.total;
  document.getElementById("pending-value").textContent = stats.pending;
  document.getElementById("success-value").textContent = stats.success;
  document.getElementById("error-value").textContent = stats.error;
}

// Lancer le traitement
async function launchProcess() {
  if (isProcessing) {
    console.log("⚠️ Traitement déjà en cours");
    return;
  }

  try {
    isProcessing = true;
    updateProcessingState(true);

    showStatus("Démarrage du traitement...", "info");
    showProgress(0, "Initialisation...");

    // Appeler l'API Vercel serverless function
    const response = await fetch(CONFIG.apiEndpoints.process, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        gristDocId: CONFIG.gristDocId,
        gristTableId: CONFIG.gristTableId,
        gristAccessToken: CONFIG.gristAccessToken,
        gristServer: CONFIG.gristServer,
      }),
    });

    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }

    const result = await response.json();

    // Afficher le résultat
    if (result.success) {
      showStatus(
        `✅ Traitement terminé ! ${result.processed} ligne(s) traitée(s)`,
        "success",
      );
      showProgress(100, "Terminé");
    } else {
      throw new Error(result.error || "Erreur inconnue");
    }

    // Recharger les stats
    await loadStats();

    // Masquer la progress bar après 3 secondes
    setTimeout(() => {
      hideProgress();
    }, 3000);
  } catch (error) {
    console.error("❌ Erreur traitement:", error);
    showStatus(`❌ Erreur: ${error.message}`, "error");
    hideProgress();
  } finally {
    isProcessing = false;
    updateProcessingState(false);
  }
}

// Mettre à jour l'état du bouton pendant le traitement
function updateProcessingState(processing) {
  const btn = document.getElementById("launch-btn");
  btn.disabled = processing;
  btn.textContent = processing
    ? "Traitement en cours..."
    : "Lancer le traitement";
}

// Afficher un message de statut
function showStatus(message, type = "info") {
  const statusEl = document.getElementById("status-message");
  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;
  statusEl.classList.remove("hidden");
}

// Masquer le message de statut
function hideStatus() {
  const statusEl = document.getElementById("status-message");
  statusEl.classList.add("hidden");
}

// Afficher la barre de progression
function showProgress(percent, text) {
  const container = document.getElementById("progress-container");
  const fill = document.getElementById("progress-fill");
  const textEl = document.getElementById("progress-text");

  container.classList.remove("hidden");
  fill.style.width = `${percent}%`;
  textEl.textContent = text;
}

// Masquer la barre de progression
function hideProgress() {
  const container = document.getElementById("progress-container");
  container.classList.add("hidden");
}

// Démarrer le refresh automatique
function startAutoRefresh() {
  // Nettoyer l'ancien timer si existe
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }

  // Créer un nouveau timer
  refreshTimer = setInterval(async () => {
    if (!isProcessing) {
      await loadStats();
    }
  }, CONFIG.refreshInterval);
}

// Arrêter le refresh automatique
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
  // Bouton lancer traitement
  document
    .getElementById("launch-btn")
    .addEventListener("click", launchProcess);

  // Initialiser le widget Grist
  if (typeof grist !== "undefined") {
    initGristWidget();
  } else {
    console.log("⚠️ Grist API non disponible - mode développement");
    // En dev, afficher des valeurs par défaut
    updateStatsDisplay({ total: 0, pending: 0, success: 0, error: 0 });
  }
});

// Cleanup au déchargement de la page
window.addEventListener("beforeunload", () => {
  stopAutoRefresh();
});
