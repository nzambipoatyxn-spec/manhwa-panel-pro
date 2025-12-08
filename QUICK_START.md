# Démarrage Rapide - PANELia

**Temps estimé** : 5 minutes
**Pour** : Nouveaux utilisateurs

---

## En 4 Étapes

### 1️⃣ Installation (2 min)

```bash
# Cloner
git clone https://github.com/nzambipoatyxn-spec/manhwa-panel-pro.git
cd manhwa-panel-pro

# Environnement virtuel
python -m venv my_venv
my_venv\Scripts\activate  # Windows
# source my_venv/bin/activate  # Linux/macOS

# Dépendances
pip install -r requirements.txt
```

### 2️⃣ Vérification (30 sec)

```bash
python check_environment.py
```

**Attendu** : 7/7 checks ✅

### 3️⃣ Lancement (10 sec)

```bash
streamlit run app.py
```

**Navigateur** : S'ouvre automatiquement sur `http://localhost:8501`

### 4️⃣ Premier Téléchargement (2 min)

1. **Collez l'URL** de la série manhwa
   ```
   Exemple : https://mangadex.org/title/abc123/series-name
   ```

2. **Cliquez "Lancer la Découverte"**

3. **Sélectionnez 1-2 chapitres** pour tester

4. **Cliquez "Lancer le Traitement"**

5. **Attendez** la barre de progression

6. **Téléchargez le ZIP** 📥

---

## Résultat

```
output/
└── Series-Name/
    ├── Chapitre-01/
    │   ├── page_001.jpg
    │   ├── page_002.jpg
    │   └── ...
    └── Chapitre-02/
        └── ...
```

**ZIP disponible** : `Series-Name-Chapitres_1_a_2.zip`

---

## Problèmes Courants

### Chrome non trouvé
```bash
# Installer Chrome puis :
pip install --force-reinstall undetected-chromedriver
```

### Aucun chapitre trouvé
- Vérifier que l'URL est celle de la **série**, pas d'un chapitre
- Essayer un autre site

### Erreur de téléchargement
- Vérifier connexion internet
- Augmenter timeout dans la barre latérale (30s → 45s)

---

## Prochaines Étapes

📖 **Guide complet** : `USER_GUIDE.md`
🔧 **Dépannage** : `USER_GUIDE.md#résolution-de-problèmes`
📊 **Métriques** : `MONITORING.md`

---

**Bon téléchargement ! 🎉**
