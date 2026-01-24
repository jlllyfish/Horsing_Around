# Widget Grist - Synchronisation Démarches Simplifiées

Interface web pour synchroniser automatiquement des données depuis Grist vers Démarches Simplifiées (champs répétables).

## 🎨 Design

Interface noir et blanc flat design inspirée de "One Trick Pony Club" avec :

- Header avec logo + titre
- 4 cartes statistiques (Total, À synchroniser, Succès, Échec)
- Bouton d'action "Lancer le traitement"
- Barre de progression en temps réel

## 🏗️ Architecture

```
/
├── index.html              # Interface utilisateur
├── style.css              # Styles (flat design noir & blanc)
├── script.js              # Logique frontend + Grist API
├── api/
│   ├── process.py         # Serverless function - traitement
│   └── requirements.txt   # Dépendances Python
├── vercel.json            # Configuration Vercel
└── README.md              # Ce fichier
```

## 📦 Déploiement sur Vercel

### 1. Installation Vercel CLI

```bash
npm install -g vercel
```

### 2. Déploiement

```bash
# Se placer dans le dossier du projet
cd /chemin/vers/le/projet

# Déployer (première fois)
vercel

# Ou pour deployer en production directement
vercel --prod
```

### 3. Configuration des variables d'environnement

Dans le dashboard Vercel (Settings > Environment Variables), ajouter :

```
GRIST_SERVER=https://grist.numerique.gouv.fr
GRIST_DOC_ID=ton_doc_id
GRIST_TABLE_ID=Demarche_134359_repetable_informations_enfant
GRIST_API_TOKEN=ton_token_grist
DS_API_TOKEN=ton_token_ds
DS_INSTRUCTEUR_ID=SW5zdHJ1Y3RldXItMTQ5MTM=
DS_CHAMP_REPETABLE_ID=Q2hhbXAtNjA0ODQyNg==
```

**Note :** Ces variables peuvent aussi être passées depuis le widget Grist directement.

## 🔧 Configuration dans Grist

### 1. Créer un Custom Widget

Dans Grist, aller dans :

1. Menu (3 points) > Widget
2. Custom Widget
3. URL : `https://ton-projet.vercel.app`

### 2. Accès aux données

Le widget a besoin de l'accès en lecture/écriture à la table :

- ✅ Read table
- ✅ Full document access (pour écrire les statuts)

### 3. Colonnes requises dans la table

- `dossier_number` (Integer) : Numéro du dossier DS
- `Donnees_DN` (Text) : Données à insérer
- `Envoi_DN` (Text) : Statut (vide = à traiter)
- `Date_envoi_DN` (DateTime) : Date de succès

## 🎯 Personnalisation

### Logo

Remplacer dans `index.html` :

```html
<!-- # LOGO ICI : Remplacer le div.logo-placeholder par ton logo SVG ou image -->
<div class="logo-placeholder">WIP</div>
```

Par :

```html
<img src="ton-logo.svg" alt="Logo" />
<!-- ou -->
<svg>...</svg>
```

### Icônes des cartes stats

Remplacer les SVG dans `index.html` aux emplacements marqués :

```html
<!-- # ICON ICI : Icône graphique/chart pour TOTAL -->
<svg>...</svg>
```

### Couleurs

Modifier dans `style.css` :

```css
/* Pour changer la couleur d'accent (actuellement noir) */
.stat-card-accent {
  background-color: #000; /* Changer ici */
}
```

## 📊 Fonctionnement

1. **Chargement** : Le widget charge les stats depuis Grist
2. **Affichage** :
   - Total = toutes les lignes
   - À synchroniser = `Envoi_DN` vide ou commence par "Échec"
   - Succès = `Envoi_DN` = "Succès"
   - Échec = `Envoi_DN` commence par "Échec"
3. **Traitement** :
   - Clic sur "Lancer le traitement"
   - Appel API serverless `/api/process`
   - Traite toutes les lignes en attente
   - Met à jour les statuts dans Grist
4. **Auto-refresh** : Les stats se rechargent toutes les 5 secondes

## 🔄 Logique de synchronisation

### Détection des doublons

Avant d'ajouter une ligne, vérifie si la donnée existe déjà dans DS.

### Réutilisation des lignes vides

DS crée une ligne vide par défaut dans les champs répétables. Le script la détecte et la remplit au lieu d'en créer une nouvelle.

### Retry automatique

En cas d'échec :

- 3 tentatives avec 5 secondes de pause
- Si échec après 3 tentatives → marque "Échec" dans Grist
- Au prochain lancement → retente automatiquement les échecs

## 🚨 Limitations Vercel (version gratuite)

- **Timeout** : 10 secondes max par requête
- **Invocations** : 1000/jour
- **Build time** : 45 minutes/mois

⚠️ Si tu as beaucoup de lignes à traiter (>100), il faudra peut-être passer au plan Pro ou découper le traitement en plusieurs appels.

## 🐛 Debug

### En local

```bash
# Installer les dépendances
pip install -r api/requirements.txt

# Lancer un serveur local
python -m http.server 8000

# Ouvrir http://localhost:8000
```

### Logs Vercel

```bash
vercel logs
```

## 📝 TODO / Améliorations possibles

- [ ] Ajouter ton logo
- [ ] Personnaliser les icônes
- [ ] Ajouter un historique des exécutions
- [ ] Notifications en temps réel (websockets)
- [ ] Filtres par statut
- [ ] Export des logs

## 📚 Références

- [Documentation Vercel Serverless Functions](https://vercel.com/docs/functions)
- [Documentation Grist Custom Widgets](https://support.getgrist.com/widget-custom/)
- [Documentation DS GraphQL](https://demarche.numerique.gouv.fr/graphql)

## 🤝 Support

Pour toute question ou problème :

1. Vérifier les logs Vercel : `vercel logs`
2. Vérifier la console navigateur (F12)
3. Vérifier les variables d'environnement Vercel
