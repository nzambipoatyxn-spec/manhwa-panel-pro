# 🛠️ Feuille de Route : Dette Technique & Améliorations

Ce document répertorie les dettes techniques identifiées lors de l'audit du 23 décembre 2025, classées par priorité.

## 🔴 Priorité Haute (Immédiat)
*Impacte la scalabilité, la fiabilité et les performances globales.*

1.  **Refactorisation des Scrapers (`scrapers.py`)**
    *   **Problème** : Logique dupliquée et fonctions isolées.
    *   **Action** : Créer une classe de base `BaseScraper` et transformer les scrapers actuels en classes spécialisées.
2.  **Attentes Explicites Selenium**
    *   **Problème** : Utilisation excessive de `time.sleep()`.
    *   **Action** : Remplacer par des `WebDriverWait` avec conditions attendues (`EC.presence_of_element_located`, etc.).
3.  **Centralisation de la Configuration**
    *   **Problème** : Paramètres de sites (`sites_requiring_human_intervention`, etc.) hardcodés dans l'UI.
    *   **Action** : Tout déplacer dans `sites_config.py`.

## 🟡 Priorité Moyenne (Court/Moyen terme)
*Optimisations de performance et découplage.*

1.  **Optimisation des Sessions HTTP (`http_utils.py`)**
    *   **Problème** : Création d'un client `httpx` pour chaque téléchargement.
    *   **Action** : Utiliser un client `httpx.Client()` persistant avec un pool de connexions.
2.  **Découplage UI-Moteur (`app.py`)**
    *   **Problème** : La fonction `discover_chapters` est dans le fichier UI.
    *   **Action** : Créer un service de découverte (`DiscoveryService`) indépendant.
3.  **Nettoyage des Exceptions**
    *   **Problème** : Blocs `except:` vides masquant des bugs.
    *   **Action** : Capturer des exceptions spécifiques et ajouter des logs explicites.

## 🟢 Priorité Basse (Long terme)
*Robustesse système et monitoring avancé.*

1.  **Gestion Dynamique des Drivers**
    *   **Problème** : Pool de drivers statique.
    *   **Action** : Implémenter un système de "recréation" de driver en cas de crash.
2.  **Limitation Fine de la Concurrence**
    *   **Problème** : Risque de saturation CPU par multiplication des threads.
    *   **Action** : Centraliser la gestion de tous les threads sous un seul orchestrateur.

---
*Dernière mise à jour : 23/12/2025*
