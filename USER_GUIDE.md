# Guide Utilisateur PANELia

**Version**: 2.5
**Date**: 2025-12-08
**Pour**: Utilisateurs finaux

---

## Table des Matières

1. [Présentation](#présentation)
2. [Installation](#installation)
3. [Premier Lancement](#premier-lancement)
4. [Guide d'Utilisation](#guide-dutilisation)
5. [Sites Supportés](#sites-supportés)
6. [Paramètres Avancés](#paramètres-avancés)
7. [Résolution de Problèmes](#résolution-de-problèmes)
8. [FAQ](#faq)

---

## Présentation

**PANELia** est une application web moderne pour télécharger et découper automatiquement des chapitres de manhwa/manga en planches individuelles.

### Fonctionnalités

✅ **Téléchargement Automatique**
- Détection automatique des chapitres
- Téléchargement parallèle ultra-rapide
- Retry automatique en cas d'échec

✅ **Traitement Intelligent**
- Découpage automatique en planches
- Filtrage par largeur minimale
- Compression JPEG optimisée

✅ **Interface Moderne**
- Interface Streamlit intuitive
- Progression en temps réel
- Export ZIP un clic

✅ **Robustesse**
- Validation des entrées
- Gestion d'erreurs avancée
- Métriques de performance

---

## Installation

### Prérequis

- **Python 3.11+** installé
- **Google Chrome** installé et à jour
- **Connexion internet** stable

### Étapes

#### 1. Cloner le Projet

```bash
git clone https://github.com/nzambipoatyxn-spec/manhwa-panel-pro.git
cd manhwa-panel-pro
```

#### 2. Créer l'Environnement Virtuel

**Windows**:
```powershell
python -m venv my_venv
my_venv\Scripts\activate
```

**Linux/macOS**:
```bash
python3 -m venv my_venv
source my_venv/bin/activate
```

#### 3. Installer les Dépendances

```bash
pip install -r requirements.txt
```

#### 4. Vérifier l'Installation

```bash
python check_environment.py
```

**Résultat attendu**:
```
✅ Python 3.11+ : OK
✅ Chrome installé : OK
✅ Dépendances : OK
✅ Répertoire output : OK
```

---

## Premier Lancement

### Démarrer l'Application

```bash
streamlit run app.py
```

**Résultat**: Votre navigateur s'ouvre sur `http://localhost:8501`

### Interface Principale

L'interface se compose de :

1. **Barre latérale** : Paramètres et statistiques
2. **Zone principale** : Workflow en 3 étapes
   - Étape 1 : URL de la série
   - Étape 2 : Sélection plage de chapitres
   - Étape 3 : Téléchargement et traitement

---

## Guide d'Utilisation

### Workflow Complet

#### Étape 1 : Entrer l'URL

1. Allez sur le site du manhwa
2. Copiez l'URL de la **page principale de la série**
   ```
   Exemple MangaDex : https://mangadex.org/title/abc123/series-name
   Exemple Madara   : https://example.com/manga/series-name/
   ```
3. Collez l'URL dans PANELia
4. Cliquez sur **"Lancer la Découverte"**

**Validation Automatique**:
- ✅ URL vérifiée (http/https uniquement)
- ✅ Domaine supporté (ou fallback)
- ✅ Longueur max 2048 caractères

#### Étape 2 : Sélectionner les Chapitres

1. **Liste découverte** : PANELia affiche tous les chapitres trouvés
2. **Sélection plage** :
   - Début : Premier chapitre à télécharger
   - Fin : Dernier chapitre à télécharger
3. **Validation** :
   - Plage vérifiée automatiquement
   - Avertissement si > 100 chapitres
4. Cliquez sur **"Lancer le Traitement du Lot"**

#### Étape 3 : Traitement

1. **Téléchargement** : Barre de progression en temps réel
2. **Découpage** : Traitement automatique
3. **Statistiques** :
   - Chapitres traités
   - Images trouvées/téléchargées
   - Planches sauvegardées
4. **Export** : Bouton "Télécharger le ZIP" à la fin

### Structure de Sortie

```
output/
└── Nom-du-Manhwa/
    ├── Chapitre-01/
    │   ├── page_001.jpg
    │   ├── page_002.jpg
    │   └── ...
    ├── Chapitre-02/
    └── ...
```

---

## Sites Supportés

### Sites Principaux

| Site | Type | CAPTCHA | Notes |
|------|------|---------|-------|
| **MangaDex** | API | Non | Optimal, très rapide |
| **FlameComics** | Selenium | Non | Stable |
| **AsuraComic** | Selenium | Non | Très stable |
| **Raijin Scans** | Selenium | Oui | Mode interactif requis |

### Mode Fallback

Si votre site n'est pas listé :
1. PANELia tente automatiquement plusieurs stratégies
2. Thèmes détectés : Madara, AsuraComic
3. Succès variable selon la structure du site

---

## Paramètres Avancés

### Barre Latérale

#### Qualité JPEG (70-100%)

```
Recommandé : 92%
- 70-80% : Compression élevée, petits fichiers
- 85-92% : Équilibre qualité/taille
- 95-100% : Qualité maximale, gros fichiers
```

**Impact** : 1 Mo à 92% → 2 Mo à 100%

#### Largeur Minimale (200-800px)

```
Recommandé : 400px
- 200px : Garde toutes les images
- 400px : Filtre les miniatures
- 600px+ : Très sélectif
```

**Usage** : Filtrer les petites images (avatars, icônes)

#### Timeout (10-60s)

```
Recommandé : 30s
- 10-20s : Connexion rapide
- 30s : Standard
- 40-60s : Connexion lente
```

**Impact** : Temps max pour télécharger 1 image

---

## Résolution de Problèmes

### Problème : Chrome non trouvé

**Erreur** :
```
❌ Erreur navigateur. Redémarrage en cours...
💡 Vérifiez que Chrome est installé et à jour.
```

**Solution** :
1. Installer Chrome : [chrome.com](https://www.google.com/chrome/)
2. Redémarrer PANELia
3. Si erreur persiste :
   ```bash
   pip install --force-reinstall undetected-chromedriver webdriver-manager
   ```

---

### Problème : Aucun chapitre trouvé

**Erreur** :
```
❌ Aucun chapitre n'a pu être découvert.
```

**Causes** :
- URL incorrecte (page chapitre au lieu de série)
- Site a changé de structure
- CAPTCHA non résolu

**Solutions** :
1. Vérifier que l'URL est celle de la **série** (liste des chapitres)
2. Essayer un autre chapitre ou site
3. Si site nécessite CAPTCHA, résoudre manuellement

---

### Problème : Erreurs de téléchargement

**Erreur** :
```
[DL][CHAP 1] ÉCHEC FINAL pour ...
```

**Causes** :
- Connexion internet instable
- Serveur down temporairement
- Images supprimées

**Solutions** :
1. Vérifier connexion internet
2. Réessayer plus tard
3. Augmenter timeout (barre latérale)
4. Vérifier que le chapitre existe toujours

---

### Problème : Circuit Breaker ouvert

**Message logs** :
```
Circuit breaker OUVERT (3 échecs, timeout 30s)
```

**Signification** : Trop d'échecs consécutifs, PANELia bloque temporairement

**Solution** :
1. Attendre 30-60 secondes
2. Circuit se rouvre automatiquement
3. Si persiste, redémarrer l'application

---

### Problème : Espace disque insuffisant

**Erreur** :
```
❌ Espace disque insuffisant.
```

**Solution** :
1. Vérifier espace disque : `df -h` (Linux/macOS) ou Propriétés du disque (Windows)
2. Libérer de l'espace (supprimer dossier `output/` si nécessaire)
3. Redémarrer le traitement

---

### Problème : Validation échouée

**Erreur** :
```
❌ URL invalide : ...
```

**Causes** :
- URL malformée
- Schéma incorrect (ftp://, file://)
- URL trop longue (> 2048 caractères)

**Solution** :
1. Copier-coller l'URL depuis le navigateur
2. S'assurer qu'elle commence par `http://` ou `https://`
3. Pas de caractères spéciaux

---

## FAQ

### Q1 : Combien de chapitres puis-je télécharger en une fois ?

**R** : Pas de limite technique, mais recommandé **< 100 chapitres** pour :
- Stabilité du processus
- Gestion mémoire optimale
- Meilleur retry en cas d'erreur

**Astuce** : Pour 200 chapitres, faire 2 lots de 100.

---

### Q2 : Puis-je mettre en pause et reprendre ?

**R** : Non actuellement. Le traitement est en un bloc.

**Alternative** :
1. Noter les chapitres déjà traités
2. Relancer avec une nouvelle plage
3. Les chapitres déjà présents dans `output/` ne sont pas écrasés

---

### Q3 : Comment améliorer la vitesse ?

**Optimisations** :
1. **Connexion rapide** : Fibre > ADSL
2. **Timeout optimal** : 20s au lieu de 30s si connexion rapide
3. **Qualité réduite** : 85% au lieu de 92% (gain taille, pas vitesse)
4. **Un seul lot** : Éviter de lancer plusieurs instances PANELia

**Performance actuelle** : ~15-30s par chapitre (10-20 images)

---

### Q4 : PANELia fonctionne sur quel OS ?

**R** : Multiplateforme :
- ✅ **Windows 10/11**
- ✅ **Linux** (Ubuntu, Debian, Arch)
- ✅ **macOS** (10.15+)

**Prérequis** : Python 3.11+ et Chrome installés

---

### Q5 : Logs sont sauvegardés où ?

**R** : `app.log` à la racine du projet

**Rotation automatique** :
- Taille max : 10 MB
- Rétention : 7 jours
- Ancien fichier → `app.log.2025-12-08`

**Consulter** :
```bash
tail -f app.log  # Temps réel (Linux/macOS)
Get-Content app.log -Tail 20  # Windows PowerShell
```

---

### Q6 : Métriques de performance ?

**R** : PANELia collecte automatiquement :
- Temps de scraping par chapitre
- Vitesse de téléchargement (MB/s)
- Taux de succès (%)
- Nombre d'images (trouvées/téléchargées/traitées)

**Export** : Voir `MONITORING.md` pour détails

---

### Q7 : Comment signaler un bug ?

**R** : GitHub Issues :
1. Aller sur [GitHub](https://github.com/nzambipoatyxn-spec/manhwa-panel-pro/issues)
2. Créer un nouveau ticket
3. Inclure :
   - Version Python
   - Version Chrome
   - URL du site
   - Logs (`app.log`)

---

## Bonnes Pratiques

### ✅ À Faire

1. **Tester avec 1-2 chapitres** avant gros lot
2. **Vérifier Chrome à jour** régulièrement
3. **Libérer espace disque** avant gros téléchargements
4. **Consulter logs** en cas d'erreur
5. **Respecter les sites** (pas de scraping abusif)

### ❌ À Éviter

1. **URL de chapitre** au lieu de série
2. **Lots > 200 chapitres** (risque timeout)
3. **Timeout < 10s** (trop agressif)
4. **Largeur min > 600px** (peut filtrer vraies images)
5. **Plusieurs instances** PANELia simultanées

---

## Support

### Documentation

- **Guide installation** : `INSTALLATION.md`
- **Monitoring** : `MONITORING.md`
- **Validation** : `VALIDATION.md`
- **Guide Windows** : `GUIDE_WINDOWS.md`

### Communauté

- **GitHub** : [Issues](https://github.com/nzambipoatyxn-spec/manhwa-panel-pro/issues)
- **Logs** : Consultez `app.log` avant de demander de l'aide

---

**Auteur** : PANELia Team
**Version** : 2.5
**Licence** : Voir LICENSE

🎉 **Bon téléchargement avec PANELia !**
