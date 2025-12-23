# PANELia - Manhwa Panel Pro

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production-brightgreen.svg)]()

**Application web moderne pour télécharger et découper automatiquement des chapitres de manhwa/manga en planches individuelles.**

---

## ✨ Fonctionnalités

- ✅ **Téléchargement Automatique** - Détection et téléchargement parallèle des chapitres
- ✅ **Traitement Intelligent** - Découpage automatique en planches avec filtrage
- ✅ **Interface Moderne** - UI Streamlit intuitive avec progression temps réel
- ✅ **Sites Multiples** - Support MangaDex, FlameComics, AsuraComic, et plus
- ✅ **Robustesse** - Retry automatique, circuit breaker, gestion d'erreurs avancée
- ✅ **Métriques** - Tracking performance (vitesse, taux de succès, durée)
- ✅ **Validation** - Entrées utilisateur validées (sécurité, path traversal)
- ✅ **Export ZIP** - Téléchargement un clic de tous les chapitres

---

## 🚀 Démarrage Rapide

### Installation

```bash
# Cloner le repo
git clone https://github.com/nzambipoatyxn-spec/manhwa-panel-pro.git
cd manhwa-panel-pro

# Créer environnement virtuel
python -m venv my_venv
my_venv\Scripts\activate  # Windows
# source my_venv/bin/activate  # Linux/macOS

# Installer dépendances
pip install -r requirements.txt
```

### Lancement

```bash
streamlit run app.py
```

Ouvre automatiquement `http://localhost:8501` dans votre navigateur.

### Premier Téléchargement

1. Collez l'URL de la série manhwa
2. Cliquez "Lancer la Découverte"
3. Sélectionnez la plage de chapitres
4. Cliquez "Lancer le Traitement"
5. Téléchargez le ZIP 📥

**Guide complet** : [`docs/user/QUICK_START.md`](docs/user/QUICK_START.md)

---

## 📋 Prérequis

- **Python 3.11+**
- **Google Chrome** (version récente)
- **Connexion Internet** stable

### Vérification

```bash
python check_environment.py
```

---

## 🏗️ Architecture

```
PANELia/
├── app.py                    # Interface Streamlit
├── core.py                   # Gestion WebDriver
├── scraper_engine.py         # Moteur de scraping
├── scrapers.py               # Scrapers spécialisés
├── http_utils.py             # Download robuste (retry, backoff)
├── validation.py             # Validation entrées (sécurité)
├── error_handler.py          # Gestion erreurs (circuit breaker)
├── metrics.py                # Monitoring performance
├── tests/                    # Suite de tests (26 tests)
└── output/                   # Chapitres téléchargés
```

---

## 🌐 Sites Supportés

| Site | Type | Status | Notes |
|------|------|--------|-------|
| **MangaDex** | API | ✅ Optimal | Très rapide, stable |
| **FlameComics** | Selenium | ✅ Stable | Bon support |
| **AsuraComic** | Selenium | ✅ Stable | Très fiable |
| **Raijin Scans** | Selenium | ⚠️ CAPTCHA | Mode interactif |
| **Autres (Madara)** | Fallback | 🟡 Variable | Selon structure |

---

## 🎛️ Paramètres Avancés

**Barre Latérale** :

- **Qualité JPEG** (70-100%) - Recommandé: 92%
- **Largeur Minimale** (200-800px) - Recommandé: 400px
- **Timeout** (10-60s) - Recommandé: 30s

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest

# Avec coverage
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest tests/unit/test_core.py -v
```

**Résultats** :
- ✅ 26/26 tests passent (100%)
- ✅ Coverage : 31% global, 65% core, 100% http_utils

---

## 📊 Métriques & Monitoring

PANELia collecte automatiquement :
- Temps de scraping par chapitre
- Vitesse de téléchargement (MB/s)
- Taux de succès/échec (%)
- Nombre d'images (trouvées/téléchargées/traitées)

**Export** : JSON, CSV
**Documentation** : [`docs/technical/MONITORING.md`](docs/technical/MONITORING.md)

---

## 🛡️ Sécurité & Validation

**Validation Automatique** :
- ✅ URLs (schéma, domaine, longueur)
- ✅ Numéros de chapitres (plage, format)
- ✅ Paramètres (qualité, timeout, largeur)
- ✅ Noms de fichiers (path traversal, injection)

**Protection** :
- Path traversal (`../`)
- Command injection (`;`, `|`, `&`)
- DoS (limites strictes)

**Documentation** : [`docs/technical/VALIDATION.md`](docs/technical/VALIDATION.md)

---

## 🔧 Gestion d'Erreurs

**Features** :
- ✅ Classification automatique (7 catégories)
- ✅ Circuit Breaker (anti-cascade)
- ✅ Retry avec backoff exponentiel
- ✅ Messages utilisateur clairs

**Exemple** :
```
❌ Délai d'attente dépassé. Nouvelle tentative...
💡 Vérifiez votre connexion internet.
```

**Documentation** : [`docs/archive/IMPROVEMENT_2_SUMMARY.md`](docs/archive/IMPROVEMENT_2_SUMMARY.md)

---

## 📚 Documentation

### Utilisateurs
- **Guide complet** : [`docs/user/USER_GUIDE.md`](docs/user/USER_GUIDE.md)
- **Démarrage rapide** : [`docs/user/QUICK_START.md`](docs/user/QUICK_START.md)
- **Installation** : [`docs/user/INSTALLATION.md`](docs/user/INSTALLATION.md)
- **Guide Windows** : [`docs/user/GUIDE_WINDOWS.md`](docs/user/GUIDE_WINDOWS.md)

### Développeurs
- **Tests** : [`docs/technical/TESTING.md`](docs/technical/TESTING.md)
- **Monitoring** : [`docs/technical/MONITORING.md`](docs/technical/MONITORING.md)
- **Validation** : [`docs/technical/VALIDATION.md`](docs/technical/VALIDATION.md)
- **Logs** : [`docs/technical/LOGS_LOGURU.md`](docs/technical/LOGS_LOGURU.md)
- **ChromeDriver** : [`docs/technical/CHROME_DRIVER.md`](docs/technical/CHROME_DRIVER.md)
- **Dette Technique** : [`docs/technical/ROADMAP_TECH_DEBT.md`](docs/technical/ROADMAP_TECH_DEBT.md)

---

## 🐛 Dépannage

### Chrome non trouvé

```bash
pip install --force-reinstall undetected-chromedriver webdriver-manager
```

### Aucun chapitre trouvé

- Vérifier que l'URL est celle de la **série** (liste chapitres)
- Essayer un autre site

### Erreurs de téléchargement

- Vérifier connexion internet
- Augmenter timeout (barre latérale)

**Guide complet** : [`docs/user/USER_GUIDE.md#résolution-de-problèmes`](docs/user/USER_GUIDE.md#résolution-de-problèmes)

---

## 🤝 Contributions

Les contributions sont les bienvenues !

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📝 Changelog

### v2.5 (2025-12-08) - Version Actuelle

**Améliorations** :
- ✅ #1 - Validation des entrées (sécurité)
- ✅ #2 - Gestion d'erreurs avancée (circuit breaker)
- ✅ #3 - Suite de tests complète (26 tests)
- ✅ #4 - Logs structurés (Loguru)
- ✅ #5 - Monitoring performance (métriques)
- ✅ #6 - Documentation utilisateur

**Détails** : [`docs/archive/CHANGELOG_V2.md`](docs/archive/CHANGELOG_V2.md)

---

## 📄 Licence

Ce projet est sous licence MIT - voir [`LICENSE`](LICENSE) pour détails.

---

## 👥 Auteurs

**PANELia Team**

---

## 🌟 Remerciements

- [Streamlit](https://streamlit.io) - Framework UI
- [Selenium](https://selenium.dev) - Automation navigateur
- [BeautifulSoup](https://beautiful-soup-4.readthedocs.io) - Parsing HTML
- [Loguru](https://github.com/Delgan/loguru) - Logging moderne
- [httpx](https://www.python-httpx.org) - Client HTTP

---

## 📞 Support

- **Issues** : [GitHub Issues](https://github.com/nzambipoatyxn-spec/manhwa-panel-pro/issues)
- **Documentation** : [`docs/user/USER_GUIDE.md`](docs/user/USER_GUIDE.md)
- **Logs** : Consultez `app.log` pour détails

---

**⭐ N'oubliez pas de starrer le repo si PANELia vous est utile !**

---

Made with ❤️ by PANELia Team
