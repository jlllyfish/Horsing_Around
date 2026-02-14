// Configuration
const CONFIG = {
  gristDocId: null,
  gristTableIdEnvoi: "Demarche_134359_repetable_informations_enfant", // Onglet Envoi
  gristTableIdSaisie: "Demarche_138030_repetable_enfant", // Onglet Saisie
  gristAccessToken: null,
  gristServer: "https://grist.numerique.gouv.fr",
  refreshInterval: 30000, // 30 secondes
  apiEndpoints: {
    process: "/api/process",
    stats: "/api/stats",
    saveAvis: "/api/save-avis",
  },
};

// État global
let isProcessing = false;
let refreshTimer = null;
let currentTab = "saisie";
let allRecordsSaisie = []; // Tous les records de la table Saisie
let filteredRecords = []; // Records filtrés (pour navigation)
let currentIndex = 0; // Index actuel dans la navigation
let selectedRecord = null; // Record sélectionné pour la saisie

// ========== UTILITAIRES ==========

/**
 * Convertit un timestamp Unix en date lisible
 * @param {number} timestamp - Timestamp Unix (peut être en secondes ou millisecondes)
 * @returns {string} - Date formatée "JJ/MM/AAAA"
 */
function formatDate(timestamp) {
  if (!timestamp) return "-";

  // Grist peut retourner des timestamps en secondes ou millisecondes
  // Si le nombre est < 10000000000, c'est probablement en secondes
  const ts = timestamp < 10000000000 ? timestamp * 1000 : timestamp;

  const date = new Date(ts);

  // Vérifier si la date est valide
  if (isNaN(date.getTime())) return "-";

  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();

  return `${day}/${month}/${year}`;
}

// ========== GESTION DES ONGLETS ==========

function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");

      // Retirer active de tous les boutons et contenus
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabContents.forEach((c) => c.classList.remove("active"));

      // Ajouter active au bouton et contenu sélectionnés
      btn.classList.add("active");
      document.getElementById(`tab-${tabId}`).classList.add("active");

      currentTab = tabId;

      // Charger les données selon l'onglet
      if (tabId === "saisie") {
        loadRecordsSaisie();
      } else if (tabId === "envoi") {
        loadStats(true);
      }
    });
  });
}

// ========== ONGLET 1: SAISIE DES AVIS ==========

async function loadRecordsSaisie() {
  try {
    showStatusSaisie("Chargement des enfants...", "info");

    const response = await fetch(
      `/api/get-enfants?tableId=${CONFIG.gristTableIdSaisie}`,
    );

    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Erreur inconnue");
    }

    allRecordsSaisie = data.records;

    // Trier par ordre alphabétique (nom)
    allRecordsSaisie.sort((a, b) => {
      const nomA = (a.fields.nom || "").toLowerCase();
      const nomB = (b.fields.nom || "").toLowerCase();
      return nomA.localeCompare(nomB);
    });

    console.log(`✅ ${allRecordsSaisie.length} records chargés et triés`);

    // Initialiser la liste filtrée et afficher le premier
    updateFilteredRecords();

    if (filteredRecords.length > 0) {
      currentIndex = 0;
      displayRecordAtIndex(currentIndex);
    }

    // Afficher le compteur initial
    updateCounter();

    hideStatusSaisie();
  } catch (error) {
    console.error("❌ Erreur chargement records:", error);
    showStatusSaisie("Erreur lors du chargement des données", "error");
  }
}

/**
 * Met à jour la liste des records filtrés selon la checkbox
 */
function updateFilteredRecords() {
  const filterCheckbox = document.getElementById("filter-non-saisis");
  const isFiltered = filterCheckbox ? filterCheckbox.checked : false;

  if (isFiltered) {
    filteredRecords = allRecordsSaisie.filter(
      (r) =>
        !r.fields.Avis_commission || r.fields.Avis_commission.trim() === "",
    );
  } else {
    filteredRecords = [...allRecordsSaisie];
  }

  // Trier par nom
  filteredRecords.sort((a, b) => {
    const nomA = (a.fields.nom || "").toLowerCase();
    const nomB = (b.fields.nom || "").toLowerCase();
    return nomA.localeCompare(nomB);
  });
}

/**
 * Affiche le record à l'index donné
 */
function displayRecordAtIndex(index) {
  if (index < 0 || index >= filteredRecords.length) {
    return;
  }

  currentIndex = index;
  selectedRecord = filteredRecords[currentIndex];

  // Remplir les champs d'info
  const nom = selectedRecord.fields.nom || "Sans nom";
  const prenom = selectedRecord.fields.prenom_s || "";
  const fullName = prenom ? `${prenom} ${nom}` : nom;

  document.getElementById("selected-name").textContent = fullName;
  document.getElementById("selected-prenom").textContent = prenom || "-";
  document.getElementById("selected-naissance").textContent = formatDate(
    selectedRecord.fields.ne_e_le,
  );
  document.getElementById("selected-dossier").textContent =
    selectedRecord.fields.dossier_number || "?";
  document.getElementById("selected-record-id").textContent = selectedRecord.id;

  // Pré-remplir le textarea si un avis existe déjà
  const avisText = document.getElementById("avis-text");
  avisText.value = selectedRecord.fields.Avis_commission || "";
  avisText.disabled = false;

  // Activer les boutons
  document.getElementById("valider-btn").disabled = false;
  document.getElementById("clear-btn").disabled = false;

  // Mettre à jour le compteur de navigation
  updateNavigationButtons();
}

/**
 * Met à jour l'état des boutons de navigation
 */
function updateNavigationButtons() {
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const navCounter = document.getElementById("nav-counter");

  if (filteredRecords.length === 0) {
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    navCounter.textContent = "0 / 0";
    return;
  }

  prevBtn.disabled = currentIndex === 0;
  nextBtn.disabled = currentIndex === filteredRecords.length - 1;
  navCounter.textContent = `${currentIndex + 1} / ${filteredRecords.length}`;
}

/**
 * Navigation vers le record précédent
 */
function navigatePrevious() {
  if (currentIndex > 0) {
    displayRecordAtIndex(currentIndex - 1);
  }
}

/**
 * Navigation vers le record suivant
 */
function navigateNext() {
  if (currentIndex < filteredRecords.length - 1) {
    displayRecordAtIndex(currentIndex + 1);
  }
}

/**
 * Met à jour l'affichage du compteur selon le contexte
 */
function updateCounter() {
  const filterCheckbox = document.getElementById("filter-non-saisis");
  const searchInput = document.getElementById("search-nom");
  const counter = document.getElementById("search-counter");
  const counterText = document.getElementById("counter-text");

  if (!filterCheckbox || !searchInput || !counter || !counterText) return;

  const searchText = searchInput.value.trim();
  const isFiltered = filterCheckbox.checked;

  // Calculer les stats
  const result = filterRecordsSaisie(searchText, isFiltered);

  // Afficher le compteur si :
  // - Il y a une recherche active OU
  // - Le filtre est activé
  if (searchText !== "" || isFiltered) {
    if (isFiltered) {
      counterText.textContent = `${result.stats.nonSaisis} avis non saisi(s) / ${result.stats.total} total`;
    } else {
      counterText.textContent = `${result.stats.filtered} résultat(s) sur ${result.stats.total} total`;
    }
    counter.classList.remove("hidden");
  } else {
    counter.classList.add("hidden");
  }
}

function filterRecordsSaisie(searchText, nonSaisisOnly) {
  let filtered = allRecordsSaisie;
  const totalRecords = allRecordsSaisie.length;

  // Filtrer par case à cocher "Avis non saisis"
  if (nonSaisisOnly) {
    filtered = filtered.filter(
      (r) =>
        !r.fields.Avis_commission || r.fields.Avis_commission.trim() === "",
    );
  }

  // Filtrer par texte de recherche
  if (searchText.trim() !== "") {
    const search = searchText.toLowerCase();
    filtered = filtered.filter((r) => {
      const nom = (r.fields.nom || "").toLowerCase();
      const prenom = (r.fields.prenom || "").toLowerCase();
      return nom.includes(search) || prenom.includes(search);
    });
  }

  return {
    records: filtered,
    stats: {
      total: totalRecords,
      filtered: filtered.length,
      nonSaisis: allRecordsSaisie.filter(
        (r) =>
          !r.fields.Avis_commission || r.fields.Avis_commission.trim() === "",
      ).length,
    },
  };
}

function showAutocomplete(result) {
  const list = document.getElementById("autocomplete-list");
  const counter = document.getElementById("search-counter");
  const counterText = document.getElementById("counter-text");

  list.innerHTML = "";

  // Afficher le compteur
  const filterCheckbox = document.getElementById("filter-non-saisis");
  if (filterCheckbox.checked) {
    counterText.textContent = `${result.stats.filtered} avis non saisi(s) / ${result.stats.total} total`;
  } else {
    counterText.textContent = `${result.stats.filtered} résultat(s) sur ${result.stats.total} total`;
  }
  counter.classList.remove("hidden");

  if (result.records.length === 0) {
    list.classList.add("hidden");
    return;
  }

  result.records.slice(0, 10).forEach((record) => {
    const item = document.createElement("div");
    item.className = "autocomplete-item";

    const nom = record.fields.nom || "Sans nom";
    const prenom = record.fields.prenom || "";
    const fullName = prenom ? `${prenom} ${nom}` : nom;
    const dossier = record.fields.dossier_number || "?";
    const avisStatus = record.fields.Avis_commission
      ? "✓ Avis saisi"
      : "○ Non saisi";

    item.innerHTML = `
      <strong>${fullName}</strong>
      <small>Dossier ${dossier} - ${avisStatus}</small>
    `;

    item.addEventListener("click", () => {
      selectRecord(record);
      list.classList.add("hidden");
    });

    list.appendChild(item);
  });

  list.classList.remove("hidden");
}

function selectRecord(record) {
  // Trouver l'index de ce record dans filteredRecords
  const index = filteredRecords.findIndex((r) => r.id === record.id);

  if (index !== -1) {
    displayRecordAtIndex(index);
  }

  // Fermer l'autocomplete
  document.getElementById("autocomplete-list").classList.add("hidden");
}

function clearSelection() {
  // Retourner au premier enfant
  if (filteredRecords.length > 0) {
    currentIndex = 0;
    displayRecordAtIndex(currentIndex);
  }

  // Vider le champ de recherche et la zone d'avis
  document.getElementById("search-nom").value = "";
  document.getElementById("avis-text").value =
    selectedRecord?.fields.Avis_commission || "";
  document.getElementById("autocomplete-list").classList.add("hidden");
  document.getElementById("search-counter").classList.add("hidden");
}

async function saveAvis() {
  if (!selectedRecord) {
    showStatusSaisie("Aucun enfant sélectionné", "error");
    return;
  }

  const avisText = document.getElementById("avis-text").value.trim();

  if (!avisText) {
    showStatusSaisie("Veuillez saisir un avis", "error");
    return;
  }

  try {
    showStatusSaisie("Enregistrement de l'avis...", "info");

    const response = await fetch(CONFIG.apiEndpoints.saveAvis, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        recordId: selectedRecord.id,
        avis: avisText,
        tableId: CONFIG.gristTableIdSaisie,
      }),
    });

    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || "Erreur inconnue");
    }

    showStatusSaisie("✅ Avis enregistré avec succès !", "success");

    // Recharger les records
    await loadRecordsSaisie();

    // Clear selection après 2 secondes
    setTimeout(() => {
      clearSelection();
      hideStatusSaisie();
    }, 2000);
  } catch (error) {
    console.error("❌ Erreur sauvegarde avis:", error);
    showStatusSaisie(`❌ Erreur: ${error.message}`, "error");
  }
}

// Event listeners pour l'onglet Saisie
function initSaisieTab() {
  const searchInput = document.getElementById("search-nom");
  const filterCheckbox = document.getElementById("filter-non-saisis");
  const validerBtn = document.getElementById("valider-btn");
  const clearBtn = document.getElementById("clear-btn");

  // Recherche avec autocomplete
  searchInput.addEventListener("input", (e) => {
    const searchText = e.target.value;
    const nonSaisisOnly = filterCheckbox.checked;

    if (searchText.trim() === "") {
      document.getElementById("autocomplete-list").classList.add("hidden");
      document.getElementById("search-counter").classList.add("hidden");
      return;
    }

    const result = filterRecordsSaisie(searchText, nonSaisisOnly);
    showAutocomplete(result);
  });

  // Checkbox filtre
  filterCheckbox.addEventListener("change", (e) => {
    // Mettre à jour la liste filtrée
    updateFilteredRecords();

    // Afficher le premier de la nouvelle liste
    if (filteredRecords.length > 0) {
      currentIndex = 0;
      displayRecordAtIndex(currentIndex);
    }

    // Mettre à jour le compteur
    updateCounter();

    // Si il y a une recherche active, mettre à jour l'autocomplete
    const searchText = searchInput.value;
    if (searchText.trim() !== "") {
      const result = filterRecordsSaisie(searchText, e.target.checked);
      showAutocomplete(result);
    }
  });

  // Fermer autocomplete si clic ailleurs
  document.addEventListener("click", (e) => {
    if (
      !searchInput.contains(e.target) &&
      !document.getElementById("autocomplete-list").contains(e.target)
    ) {
      document.getElementById("autocomplete-list").classList.add("hidden");
    }
  });

  // Bouton valider
  validerBtn.addEventListener("click", saveAvis);

  // Bouton annuler
  clearBtn.addEventListener("click", clearSelection);

  // Boutons de navigation
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");

  prevBtn.addEventListener("click", navigatePrevious);
  nextBtn.addEventListener("click", navigateNext);

  // Navigation au clavier (flèches gauche/droite)
  document.addEventListener("keydown", (e) => {
    // Ne pas naviguer si on est en train de taper dans un champ
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
      return;
    }

    if (currentTab === "saisie") {
      if (e.key === "ArrowLeft") {
        navigatePrevious();
      } else if (e.key === "ArrowRight") {
        navigateNext();
      }
    }
  });
}

function showStatusSaisie(message, type = "info") {
  const statusEl = document.getElementById("status-message-saisie");
  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;
  statusEl.classList.remove("hidden");
}

function hideStatusSaisie() {
  const statusEl = document.getElementById("status-message-saisie");
  statusEl.classList.add("hidden");
}

// ========== ONGLET 2: ENVOI DES AVIS (dashboard original) ==========

async function loadStats(showMessage = false) {
  try {
    if (showMessage) {
      showStatus("Chargement des statistiques...", "info");
    }

    const response = await fetch("/api/stats");

    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Erreur inconnue");
    }

    updateStatsDisplay(data.stats);

    if (showMessage) {
      hideStatus();
    }
  } catch (error) {
    console.error("❌ Erreur chargement stats:", error);
    if (showMessage) {
      showStatus("Erreur lors du chargement des statistiques", "error");
    }
  }
}

function updateStatsDisplay(stats) {
  document.getElementById("total-value").textContent = stats.total;
  document.getElementById("pending-value").textContent = stats.pending;
  document.getElementById("success-value").textContent = stats.success;
  document.getElementById("error-value").textContent = stats.error;
  document.getElementById("avis-value").textContent =
    `${stats.avisCompleted} / ${stats.total}`;
}

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

    const response = await fetch(CONFIG.apiEndpoints.process, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        gristDocId: CONFIG.gristDocId,
        gristTableId: CONFIG.gristTableIdEnvoi,
        gristServer: CONFIG.gristServer,
      }),
    });

    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }

    const result = await response.json();

    if (result.success) {
      showStatus(
        `✅ Traitement terminé ! ${result.processed} ligne(s) traitée(s)`,
        "success",
      );
      showProgress(100, "Terminé");
    } else {
      throw new Error(result.error || "Erreur inconnue");
    }

    await loadStats(true);

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

function updateProcessingState(processing) {
  const btn = document.getElementById("launch-btn");
  btn.disabled = processing;
  btn.textContent = processing
    ? "Traitement en cours..."
    : "Lancer le traitement";
}

function showStatus(message, type = "info") {
  const statusEl = document.getElementById("status-message");
  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;
  statusEl.classList.remove("hidden");
}

function hideStatus() {
  const statusEl = document.getElementById("status-message");
  statusEl.classList.add("hidden");
}

function showProgress(percent, text) {
  const container = document.getElementById("progress-container");
  const fill = document.getElementById("progress-fill");
  const textEl = document.getElementById("progress-text");

  container.classList.remove("hidden");
  fill.style.width = `${percent}%`;
  textEl.textContent = text;
}

function hideProgress() {
  const container = document.getElementById("progress-container");
  container.classList.add("hidden");
}

function startAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }

  refreshTimer = setInterval(async () => {
    if (!isProcessing && currentTab === "envoi") {
      await loadStats(false);
    }
  }, CONFIG.refreshInterval);
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

// ========== INITIALISATION ==========

async function initGristWidget() {
  try {
    if (typeof grist !== "undefined") {
      await grist.ready();
      console.log("✅ Grist ready");
    }

    // Initialiser les onglets
    initTabs();

    // Initialiser l'onglet Saisie
    initSaisieTab();

    // Charger les données de l'onglet actif
    if (currentTab === "saisie") {
      await loadRecordsSaisie();
    } else {
      await loadStats(true);
    }

    // Démarrer le refresh automatique
    startAutoRefresh();
  } catch (error) {
    console.error("❌ Erreur initialisation:", error);
    await loadRecordsSaisie();
    startAutoRefresh();
  }
}

// Event listeners globaux
document.addEventListener("DOMContentLoaded", () => {
  // Boutons onglet Envoi
  document
    .getElementById("launch-btn")
    .addEventListener("click", launchProcess);

  document
    .getElementById("refresh-btn")
    .addEventListener("click", () => loadStats(true));

  // Initialiser le widget Grist
  if (typeof grist !== "undefined") {
    initGristWidget();
  } else {
    console.log("⚠️ Grist API non disponible - mode développement");
    initTabs();
    initSaisieTab();
  }
});

window.addEventListener("beforeunload", () => {
  stopAutoRefresh();
});
