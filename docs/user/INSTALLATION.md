# 🚀 Guide d'Installation - PANELia

## Prérequis

- **Python 3.11 ou 3.12** (recommandé : Python 3.11)
- **Google Chrome ou Chromium** installé sur le système
- **Git** (pour cloner le dépôt)

## Installation rapide

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-repo/manhwa-panel-pro.git
cd manhwa-panel-pro/crazy-nash
```

### 2. Créer un environnement virtuel

**Windows :**
```bash
python -m venv my_venv
my_venv\Scripts\activate
```

**Linux/macOS :**
```bash
python3 -m venv my_venv
source my_venv/bin/activate
```

### 3. Installer les dépendances

```bash
# Installation complète (toutes les améliorations)
pip install -r requirements.txt

# OU installation minimale (fonctionnalités de base uniquement)
pip install streamlit undetected-chromedriver setuptools requests beautifulsoup4 numpy Pillow selenium opencv-python httpx
```

### 4. Lancer l'application

```bash
streamlit run app.py
```

L'application sera accessible à : **http://localhost:8501**

---

## 🔍 Vérification de l'environnement

**NOUVEAU** : Avant de lancer l'application, vérifiez que tout est correctement installé :

```bash
python check_environment.py
```

Ce script vérifie automatiquement :
- ✓ Version de Python (3.11+)
- ✓ Système d'exploitation (Windows/Linux/macOS)
- ✓ Installation de Chrome/Chromium
- ✓ Packages Python requis
- ✓ Cache webdriver-manager
- ✓ Permissions sur le répertoire de sortie
- ✓ Configuration Streamlit

**Résultat attendu :**
```
✓ Python : 3.11.7 compatible
✓ Système : Windows 11 supporté
✓ Chrome : Version 142.0.7444.176 trouvée
✓ Packages : Tous installés
✓ Environnement prêt !
```

---

## 🐛 Résolution de problèmes courants

### ⚡ PROBLÈME PRINCIPAL : Incompatibilité de version ChromeDriver

**Erreur :**
```
session not created: This version of ChromeDriver only supports Chrome version 143
Current browser version is 142.0.7444.176
```

**SOLUTION DÉFINITIVE (déjà implémentée dans v2.0) :**

L'application utilise maintenant **webdriver-manager** qui :
1. ✅ Détecte automatiquement votre version de Chrome
2. ✅ Télécharge le ChromeDriver compatible
3. ✅ Fonctionne sur Windows, Linux et macOS
4. ✅ Se met à jour automatiquement quand vous mettez à jour Chrome

**Actions à faire :**
```bash
# 1. Installer webdriver-manager (déjà dans requirements.txt)
pip install webdriver-manager>=4.0.1

# 2. Vider le cache (optionnel, si problèmes persistent)
# Windows
rmdir /s /q %USERPROFILE%\.wdm

# Linux/macOS
rm -rf ~/.wdm

# 3. Relancer l'application
streamlit run app.py
```

Le ChromeDriver correct sera téléchargé automatiquement au premier lancement !

---

### Erreur : `ModuleNotFoundError: No module named 'distutils'`

**Cause :** Python 3.12+ a supprimé le module `distutils`, mais `undetected-chromedriver` en dépend.

**Solution :**
```bash
pip install setuptools>=65.5.0
```

### Erreur : `Chrome binary not found`

**Cause :** Chrome/Chromium n'est pas installé ou non détecté.

**Solutions :**

**Windows :**
- Installez [Google Chrome](https://www.google.com/chrome/)
- OU installez Chromium via Chocolatey : `choco install chromium`

**Linux (Ubuntu/Debian) :**
```bash
sudo apt update
sudo apt install chromium-browser
```

**macOS :**
```bash
brew install --cask google-chrome
```

### Erreur : `selenium.common.exceptions.WebDriverException`

**Cause :** Version incompatible de ChromeDriver.

**Solution :**
```bash
pip install --upgrade undetected-chromedriver selenium
```

### Erreur : `OSError: [Errno 98] Address already in use`

**Cause :** Le port 8501 est déjà utilisé.

**Solution :**
```bash
# Utiliser un port différent
streamlit run app.py --server.port 8502
```

---

## 🐳 Installation avec Docker

### 1. Build l'image Docker

```bash
docker build -t panelia .
```

### 2. Lancer le conteneur

```bash
docker run -p 8501:8501 -v $(pwd)/output:/app/output panelia
```

**Accès :** http://localhost:8501

---

## 📦 Installation par amélioration

Si vous souhaitez installer les dépendances progressivement :

### Core (minimum requis)
```bash
pip install streamlit undetected-chromedriver setuptools requests beautifulsoup4 numpy Pillow selenium opencv-python httpx
```

### Amélioration 1 : Base de données
```bash
pip install sqlalchemy alembic
```

### Amélioration 2 : Async/Await
```bash
pip install aiohttp asyncio-throttle
```

### Amélioration 3 : Tests
```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio responses faker
```

### Amélioration 4 : Logs structurés
```bash
pip install structlog loguru python-json-logger sentry-sdk
```

### Amélioration 5 : Monitoring
```bash
pip install prometheus-client opentelemetry-api opentelemetry-sdk psutil
```

### Amélioration 6 : API REST
```bash
pip install fastapi "uvicorn[standard]" pydantic python-multipart
```

### Outils de développement
```bash
pip install black flake8 mypy isort pre-commit
```

---

## ⚙️ Configuration

### Configuration Streamlit

Créez `.streamlit/secrets.toml` :

```toml
[app_settings]
default_jpeg_quality = 92
default_timeout = 30
default_min_image_width = 400
```

### Variables d'environnement (optionnel)

Créez un fichier `.env` :

```bash
# Logs
LOG_LEVEL=INFO
LOG_FILE=app.log

# Sentry (monitoring)
SENTRY_DSN=https://your-sentry-dsn

# Database (si amélioration #1 activée)
DATABASE_URL=sqlite:///panelia.db
```

---

## 🧪 Lancer les tests

```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_scrapers.py
```

---

## 🔧 Outils de développement

### Formatage automatique du code

```bash
# Black (formatage)
black .

# isort (tri des imports)
isort .

# Linting
flake8 .

# Type checking
mypy .
```

### Pre-commit hooks

```bash
# Installer les hooks
pre-commit install

# Lancer manuellement
pre-commit run --all-files
```

---

## 📊 Versions testées

| Composant | Version testée | Statut |
|-----------|---------------|--------|
| Python | 3.11.7 | ✅ Recommandé |
| Python | 3.12.1 | ✅ Compatible (avec setuptools) |
| Streamlit | 1.29.0+ | ✅ |
| undetected-chromedriver | 3.5.4+ | ✅ |
| Chrome | 120.0+ | ✅ |
| Chromium | 119.0+ | ✅ |

---

## 📝 Notes importantes

1. **Python 3.13** n'est pas encore supporté par toutes les dépendances
2. **Windows** : Utilisez PowerShell ou Git Bash pour une meilleure compatibilité
3. **Linux** : Assurez-vous que les dépendances système de Chromium sont installées
4. **macOS** : Autorisez Chrome dans les paramètres de sécurité si demandé

---

## 🆘 Besoin d'aide ?

- **Issues GitHub :** [Créer une issue](https://github.com/votre-repo/issues)
- **Documentation :** Consultez le README.md principal
- **Logs :** Vérifiez `app.log` pour les erreurs détaillées

---

## 🎉 Première utilisation

Une fois l'application lancée :

1. Collez l'URL d'une série manga/manhwa
2. Cliquez sur "🔍 Lancer la Découverte"
3. Sélectionnez la plage de chapitres à télécharger
4. Cliquez sur "🚀 Lancer le Traitement du Lot"
5. Téléchargez le ZIP une fois terminé

**Sites supportés :** MangaDex, Asura Scans, Flame Comics, Reaper Scans, et plus !

Bon téléchargement ! 📚✨
