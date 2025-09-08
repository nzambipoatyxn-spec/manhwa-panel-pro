# Dockerfile

# Étape 1: On part d'une image Python officielle et légère.
FROM python:3.11-slim

# Étape 2: Installation des dépendances système. C'est la partie cruciale.
# On installe le navigateur Chromium et les librairies nécessaires pour que Selenium fonctionne.
RUN apt-get update && apt-get install -y \
    chromium \
    libnss3 \
    libatk-bridge2.0-0 \
    libcups2 \
    libgtk-3-0 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Étape 3: On définit le dossier de travail à l'intérieur de la boîte.
WORKDIR /app

# Étape 4: On copie et installe les dépendances Python.
# Copier requirements.txt d'abord permet à Docker d'utiliser le cache si seuleument le code change.
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Étape 5: On copie tout le reste de notre application dans la boîte.
COPY . .

# Étape 6: On indique que l'application écoutera sur le port 8501.
EXPOSE 8501

# Étape 7: C'est la commande qui lance l'application au démarrage du conteneur.
# Les arguments --server.* sont importants pour que Streamlit soit accessible depuis l'extérieur de la boîte.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]