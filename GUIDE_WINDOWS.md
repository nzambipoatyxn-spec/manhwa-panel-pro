# Guide Rapide - Windows PowerShell

## Commandes avec environnement virtuel activé

### 1. Activer l'environnement virtuel
```powershell
.\my_venv\Scripts\Activate.ps1
```

### 2. Vérifier l'environnement
```powershell
python check_environment.py
```

### 3. Lancer les tests
```powershell
# Tous les tests
pytest

# Tests avec coverage
pytest --cov=. --cov-report=html

# Ouvrir le rapport HTML
start htmlcov\index.html
```

### 4. Lancer l'application
```powershell
streamlit run app.py
```

---

## Commandes SANS activer l'environnement virtuel

Si vous ne voulez pas activer l'environnement, utilisez le chemin complet :

### 1. Vérifier l'environnement
```powershell
.\my_venv\Scripts\python.exe check_environment.py
```

### 2. Lancer les tests
```powershell
.\my_venv\Scripts\python.exe -m pytest tests/unit/ -v
```

### 3. Tests avec coverage
```powershell
.\my_venv\Scripts\python.exe -m pytest tests/unit/ --cov=. --cov-report=html
```

### 4. Ouvrir le rapport coverage
```powershell
start htmlcov\index.html
```

### 5. Lancer l'application
```powershell
.\my_venv\Scripts\streamlit.exe run app.py
```

---

## Tests rapides

### Test Chrome/ChromeDriver
```powershell
.\my_venv\Scripts\python.exe core.py
```

### Résultat attendu
```
============================================================
TEST DE WEBSESSION
============================================================

OK Systeme detecte : Windows
OK Profil Chrome : C:\Users\...\panelia_profiles\profile_xxx
OK Navigation reussie vers Google
OK Titre de la page : Google

OK TOUS LES TESTS SONT PASSES !
============================================================
```

---

## Résultats actuels

✅ **26 tests créés**
✅ **26/26 tests passent (100%)**
✅ **31% de couverture globale**
✅ **http_utils.py : 100% de couverture**
✅ **core.py : 65% de couverture**

---

## En cas de problème

### Erreur : "pytest n'est pas reconnu"
**Solution :** Utilisez le chemin complet
```powershell
.\my_venv\Scripts\python.exe -m pytest
```

### Erreur : "streamlit n'est pas reconnu"
**Solution :** Utilisez le chemin complet
```powershell
.\my_venv\Scripts\streamlit.exe run app.py
```

### Erreur : "Cannot load script Activate.ps1"
**Solution :** Changez la politique d'exécution PowerShell
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Commandes Git

### Voir les changements
```powershell
git status
```

### Commit avec les tests
```powershell
git add .
git commit -m "feat: add webdriver-manager + test suite (26 tests, 31% coverage)"
```

### Push
```powershell
git push origin crazy-nash
```

---

*Dernière mise à jour : 2025-12-03*
