# Widget Grist - Synchronisation Démarches Simplifiées

Interface web pour synchroniser automatiquement des données depuis Grist vers Démarches Simplifiées (champs répétables).

## 🎨 Design

Interface noir et blanc flat design avec :

- Header avec logo + titre
- 4 cartes statistiques (Total, À synchroniser, Succès, Échec)
- Bouton d'action "Lancer le traitement"
- Barre de progression en temps réel

## 🏗️ Architecture

```
Horsing_Around/
├── api/                    # Endpoints Vercel serverless
│   ├── process.py         # Endpoint POST traitement
│   ├── stats.py           # Endpoint GET statistiques
│   └── requirements.txt   # Dépendances API
├── core/                   # Logique métier partagée
│   ├── __init__.py
│   ├── ds.py              # Fonctions Démarches Simplifiées
│   ├── grist.py           # Fonctions Grist
│   ├── processor.py       # Logique de traitement
│   └── stats.py           # Calcul statistiques
├── index.html             # Interface utilisateur
├── style.css              # Styles (flat design noir & blanc)
├── script.js              # Logique frontend + appels API
├── app.py                 # Serveur Flask local (dev)
├── requirements.txt       # Dépendances Flask
└── vercel.json            # Configuration Vercel
```

## 🚀 Déploiement sur Vercel

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

# Ou pour déployer en production directement
vercel --prod
```

### 3. Configuration des variables d'environnement

Dans le dashboard Vercel (Settings > Environment Variables), ajouter :

```
GRIST_SERVER=https://grist.numerique.gouv.fr
GRIST_DOC_ID=...
GRIST_TABLE_ID=Demarche_134359_repetable_informations_enfant
GRIST_API_TOKEN=...
DS_API_TOKEN=...
DS_INSTRUCTEUR_ID=...
DS_CHAMP_REPETABLE_ID=...
```

**Note :** Ces variables peuvent être passées depuis le widget Grist directement.

## 📝 Configuration dans Grist

### 1. Créer un Custom Widget

Dans Grist, aller dans :

1. Menu (3 points) > Widget
2. Custom Widget
3. URL : `https://ton-projet.vercel.app`

### 2. Accès aux données

Le widget a besoin de l'accès en lecture/écriture à la table :

- ✅ Read table
- ✅ Full document access (pour les mises à jour)

### 3. Colonnes requises dans la table

- `dossier_number` (Entier) : Numéro du dossier DS
- `Donnees_DN` (Texte) : Données à injecter (format libre)
- `Envoi_DN` (Texte) : Statut ("Succès" ou "Échec: ...")
- `Date_envoi_DN` (DateTime) : Date de succès
- `block_row_id_annotations` (Texte) : ID de la row DS créée
- `Avis_commission` (Texte) : Avis saisi (pour stats)

## 📊 Fonctionnement

### 1. Chargement : Le widget charge les stats depuis Grist

**Affichage :**
- Total : nombre total de lignes
- À synchroniser : `Envoi_DN` vide OU commence par "Échec"
- Succès : `Envoi_DN` = "Succès"
- Échec : `Envoi_DN` commence par "Échec"
- Avis saisis : `Avis_commission` non vide

### 2. Traitement : Clic sur "Lancer le traitement"

**Appel API serverless** `/api/process` qui :
- Récupère les lignes à synchroniser
- Traite toutes les lignes en attente
- Met à jour les statuts dans Grist

### 3. Affichage : Les stats se rechargent toutes les 5 secondes

**Auto-refresh** : Les stats se rechargent automatiquement en arrière-plan

## ✨ Logique de synchronisation

**Détection des doublons :**
DS crée une ligne vide par défaut dans le champ répétable. Le script détecte et remplit au lieu d'en créer une nouvelle.

**Réutilisation des lignes vides :**
Si une ligne vide existe déjà dans DS, elle est remplie. Sinon, une nouvelle ligne est ajoutée.

**Retry automatique :**
En cas d'échec :
- 3 tentatives avec 5 secondes de pause
- Si échec après 3 tentatives → marque "Échec" dans Grist

## 🔧 Debug

### En local

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur Flask
python app.py
```

Ouvrir http://localhost:3000

### Logs Vercel

```bash
vercel logs
```

## ⚠️ Limitations Vercel (version gratuite)

- **Timeout** : 10 secondes max par requête
- **Invocations** : 1000/jour
- **Build time** : 45 minutes/mois

⚠️ Si tu as beaucoup de lignes à traiter (>100), il faudra peut-être passer au plan Pro ou découper le traitement en plusieurs appels.

## 🔬 TODO / Améliorations possibles

- [ ] Ajouter ton logo
- [ ] Personnaliser les icônes
- [ ] Ajouter un historique des exécutions
- [ ] Notifications en temps réel (websockets)
- [ ] Filtres par statut
- [ ] Export logs

## 📚 Références

- [Documentation Vercel Serverless Functions](https://vercel.com/docs/functions)
- [Documentation Grist Custom Widgets](https://support.getgrist.com/widget-custom/)
- [Documentation DS GraphQL](https://demarche.numerique.gouv.fr/graphql)

## 🆘 Support

Pour toute question ou problème :

1. Vérifier les logs Vercel : `vercel logs`
2. Vérifier la console navigateur (F12)
3. Vérifier les variables d'environnement Vercel
