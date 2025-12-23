# 📊 Monitoring Performance - PANELia

**Date**: 2025-12-08
**Amélioration**: #5 - Monitoring Performance
**Priorité**: Haute

---

## 🎯 Objectif

Ajouter un système de monitoring pour tracker les performances du scraping :
- Temps de scraping par chapitre
- Vitesse de téléchargement
- Taux de succès/échec
- Statistiques globales

---

## 📦 Module metrics.py

### Fonctionnalités

**Tracking automatique** :
- Temps de début/fin de chaque chapitre
- Nombre d'images trouvées/téléchargées/traitées
- Taille des données téléchargées
- Erreurs rencontrées

**Métriques calculées** :
- Durée de scraping
- Vitesse de téléchargement (MB/s)
- Taux de succès (%)
- Statistiques agrégées

**Export** :
- JSON : Métriques complètes
- CSV : Métriques par chapitre

---

## 🔧 Utilisation

### API Simple

```python
from metrics import get_collector

# Récupérer le collecteur global
collector = get_collector()

# Démarrer tracking d'un chapitre
collector.start_chapter(1.0, "https://example.com/chapter/1")

# Mettre à jour les métriques
collector.update_chapter(1.0, images_found=10)
collector.add_download(1.0, bytes_downloaded=1024000, success=True)

# Terminer le tracking
collector.end_chapter(1.0, success=True)

# Obtenir les statistiques
stats = collector.get_stats()
print(stats)

# Exporter
collector.export_json("metrics.json")
collector.export_csv("metrics.csv")
```

### Intégration Automatique

Le tracking est **automatique** dans :
- `scraper_engine.py` : Track chaque chapitre
- `http_utils.py` : Track chaque téléchargement

Aucune configuration nécessaire !

---

## 📊 Métriques Collectées

### Par Chapitre

```python
{
  "chapter_num": 1.0,
  "url": "https://example.com/chapter/1",
  "duration": 45.2,  # secondes
  "images_found": 10,
  "images_downloaded": 10,
  "images_processed": 10,
  "download_errors": 0,
  "total_bytes": 15728640,  # ~15 MB
  "download_speed_mbps": 0.33,
  "success_rate": 100.0,
  "success": true
}
```

### Globales

```python
{
  "session": {
    "start_time": "2025-12-08T18:00:00",
    "duration_seconds": 180.5,
    "duration_human": "3m 0s"
  },
  "chapters": {
    "attempted": 10,
    "succeeded": 9,
    "failed": 1,
    "success_rate": 90.0,
    "avg_duration_seconds": 18.5
  },
  "images": {
    "found": 100,
    "downloaded": 95,
    "processed": 95,
    "errors": 5
  },
  "performance": {
    "total_bytes_downloaded": 157286400,  # ~150 MB
    "total_mb_downloaded": 150.0,
    "avg_speed_mbps": 0.83,
    "total_scraping_time": 180.5
  }
}
```

---

## 💾 Export

### JSON

```python
collector.export_json("metrics.json")
```

**Contient** : Toutes les métriques (session + chapitres)

**Usage** : Analyse détaillée, graphiques

---

### CSV

```python
collector.export_csv("metrics.csv")
```

**Contient** : Métriques par chapitre (format tabulaire)

**Usage** : Excel, analyse statistique

**Format** :
```csv
chapter_num,url,duration,images_found,images_downloaded,images_processed,download_errors,total_bytes,download_speed_mbps,success_rate,success
1.0,https://...,45.2,10,10,10,0,15728640,0.33,100.0,True
2.0,https://...,38.1,12,11,11,1,18874368,0.42,91.67,True
```

---

## 🔍 Exemple Complet

```python
from metrics import get_collector, reset_collector

# Réinitialiser pour une nouvelle session
reset_collector()

# Récupérer le collecteur
collector = get_collector()

# Scraper 3 chapitres
for chap_num in [1.0, 2.0, 3.0]:
    url = f"https://example.com/chapter/{int(chap_num)}"

    # Démarrer tracking
    collector.start_chapter(chap_num, url)

    try:
        # Simuler scraping
        images_found = 10
        collector.update_chapter(chap_num, images_found=images_found)

        # Simuler téléchargements
        for _ in range(images_found):
            collector.add_download(chap_num, 1024000, success=True)

        # Succès
        collector.update_chapter(chap_num, images_processed=images_found)
        collector.end_chapter(chap_num, success=True)

    except Exception as e:
        # Échec
        collector.end_chapter(chap_num, success=False, error_message=str(e))

# Obtenir stats
stats = collector.get_stats()

# Exporter
collector.export_json("session_metrics.json")
collector.export_csv("chapters_metrics.csv")

# Afficher résumé
print(f"Chapitres réussis: {stats['chapters']['succeeded']}/{stats['chapters']['attempted']}")
print(f"Taux de succès: {stats['chapters']['success_rate']}%")
print(f"Vitesse moyenne: {stats['performance']['avg_speed_mbps']} MB/s")
print(f"Données téléchargées: {stats['performance']['total_mb_downloaded']} MB")
```

---

## 📈 Avantages

### 1. Visibilité Performance
- Identifier les chapitres lents
- Détecter les bottlenecks
- Optimiser les paramètres

### 2. Debugging Facilité
- Logs détaillés avec métriques
- Erreurs tracées par chapitre
- Export pour analyse

### 3. Statistiques Précises
- Taux de succès réel
- Vitesse de téléchargement
- Temps total vs temps effectif

### 4. Analyse Historique
- Export JSON/CSV
- Comparaison entre sessions
- Graphiques possibles

---

## 🔧 Intégration

### scraper_engine.py

Tracking automatique dans `_process_single_chapter()` :

```python
# Démarrage
collector.start_chapter(chap_num, chap_url)

# Mise à jour progressive
collector.update_chapter(chap_num, images_found=len(image_urls))
collector.update_chapter(chap_num, images_downloaded=len(image_bytes_list))
collector.update_chapter(chap_num, images_processed=saved)

# Fin (succès ou échec)
collector.end_chapter(chap_num, success=True)
# ou
collector.end_chapter(chap_num, success=False, error_message=str(e))
```

### http_utils.py

Tracking des téléchargements individuels :

```python
# Succès
collector.add_download(chapter_num, len(img_bytes), success=True)

# Échec
collector.add_download(chapter_num, 0, success=False)
```

---

## 🧪 Tests

### Test Basique

```bash
python -c "
from metrics import MetricsCollector
import time

collector = MetricsCollector()
collector.start_chapter(1.0, 'https://example.com/chapter/1')
collector.update_chapter(1.0, images_found=10)
time.sleep(0.1)
collector.add_download(1.0, 1024000, success=True)
collector.end_chapter(1.0, success=True)

stats = collector.get_stats()
print('Duration:', stats['chapter_details'][0]['duration'], 's')
print('Speed:', stats['chapter_details'][0]['download_speed_mbps'], 'MB/s')
"
```

**Résultat attendu** :
```
Duration: 0.1 s
Speed: 9.77 MB/s
```

---

## 📊 Prochaines Étapes (Optionnel)

### Dashboard Streamlit
Ajouter un onglet "Métriques" dans app.py pour afficher :
- Graphique temps par chapitre
- Graphique vitesse téléchargement
- Taux de succès
- Statistiques globales

### Alertes
- Alerter si vitesse < seuil
- Alerter si taux d'échec > X%
- Notifier fin de batch

### Historique
- Sauvegarder métriques dans DB
- Comparer sessions
- Tendances

---

## 🛠️ Troubleshooting

### Métriques ne s'affichent pas
```python
from metrics import get_collector

collector = get_collector()
stats = collector.get_stats()

if stats['chapters']['attempted'] == 0:
    print("Aucun chapitre tracké")
else:
    print(f"{stats['chapters']['attempted']} chapitres trackés")
```

### Reset métriques
```python
from metrics import reset_collector

reset_collector()  # Nouvelle session
```

### Vérifier tracking
```python
collector = get_collector()
print(f"Chapitres en cours: {list(collector.chapters.keys())}")
```

---

## ✅ Checklist Migration

- [x] Créer module metrics.py
- [x] Intégrer dans scraper_engine.py
- [x] Intégrer dans http_utils.py
- [x] Tester le tracking basique
- [x] Documentation créée
- [ ] Dashboard Streamlit (optionnel)
- [ ] Alertes (optionnel)
- [ ] Historique (optionnel)

---

## 📝 Changelog

**v1.0 - 2025-12-08** :
- Module metrics.py créé
- Intégration scraper_engine.py
- Intégration http_utils.py
- Export JSON/CSV
- Documentation

---

**Date** : 2025-12-08
**Version** : v1.0
**Statut** : ✅ Fonctionnel
**Amélioration** : #5 - Monitoring Performance

🎉 **Système de monitoring opérationnel !**
