# Guide d'Installation : PANELia avec Docker 🐳

Ce guide explique comment mettre en place PANELia dans un environnement Docker pour une utilisation simplifiée et isolée.

## 1. Prérequis

* **Docker Desktop** : [Télécharger pour Windows](https://www.docker.com/products/docker-desktop/)
* **Google Drive Desktop** (Facultatif) : Pour la synchronisation Cloud automatique.

## 2. Préparation

Assurez-vous d'avoir Docker Desktop lancé sur votre machine.

## 3. Lancement de PANELia

Ouvrez un terminal dans le dossier racine du projet (`manhwa-panel-pro`) et lancez la commande suivante :

```bash
docker-compose up --build
```

Cette commande va :

1. **Construire** l'image de l'application PANELia.
2. **Construire** l'image du service de nettoyage IA.
3. **Lancer** les deux services en même temps.

Une fois terminé, l'application sera accessible à l'adresse suivante :
👉 **<http://localhost:8501>**

## 4. Configuration du Cloud (Google Drive)

Pour envoyer directement vos scans sur votre Drive sans manipulation manuelle :

1. Ouvrez le fichier `docker-compose.yml`.
2. Trouvez la section `volumes` sous le service `panelia`.
3. Modifiez la ligne pour faire correspondre votre chemin local :

```yaml
volumes:
  - "G:/Mon Drive/PANELia_Scans:/app/output"
```

*(Remplacez `G:/Mon Drive/...` par le chemin réel de votre dossier Drive sur votre PC)*.

## 5. Commandes Utiles

* **Arrêter** : `ctrl + c` dans le terminal ou `docker-compose down`.
* **Mettre à jour** : `git pull` suivi de `docker-compose up --build`.
* **Voir les logs** : `docker-compose logs -f`.

---
💡 **Note pour l'IA** : Si vous avez une carte graphique NVIDIA, vous pouvez activer l'accélération GPU dans le fichier `docker-compose.yml` en décommentant la section `deploy`.
