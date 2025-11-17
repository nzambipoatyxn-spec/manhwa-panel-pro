# core.py - v2.2 - Moteur Selenium Stable (Migration Ready)

import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException
import logging
import subprocess
import re
import time


def get_chrome_main_version():
    """
    Détecte la version principale de Chrome/Chromium sur le système.
    Renvoie None si la détection échoue (uc.Chrome gérera automatiquement la compatibilité).
    """
    try:
        # Vérifie d’abord Chromium
        process = subprocess.Popen(['chromium', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = process.communicate()
        version_str = output.decode('utf-8')
        match = re.search(r'(\d+)\.', version_str)
        if match:
            version = int(match.group(1))
            logging.info(f"Version de Chromium détectée : {version}")
            return version
    except FileNotFoundError:
        pass

    try:
        # Sinon teste Google Chrome
        process = subprocess.Popen(['google-chrome', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = process.communicate()
        version_str = output.decode('utf-8')
        match = re.search(r'(\d+)\.', version_str)
        if match:
            version = int(match.group(1))
            logging.info(f"Version de Google Chrome détectée : {version}")
            return version
    except FileNotFoundError:
        logging.warning("Aucune installation Chrome/Chromium détectée automatiquement.")
        return None


class WebSession:
    """
    Gère le cycle de vie d’un driver Selenium avec :
      - redémarrage automatique en cas de crash
      - proxy d’attributs (accès direct comme un vrai driver)
      - support du mode headless
    """

    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self._start_driver()

    def __getattr__(self, name):
        """
        Proxy automatique vers les attributs du vrai driver Selenium.
        Permet d’utiliser directement :
            session.page_source
            session.find_element(...)
            session.execute_script(...)
        """
        if self.driver:
            return getattr(self.driver, name)
        raise AttributeError(f"'WebSession' object has no attribute '{name}'")

    def _start_driver(self):
        """Initialise une nouvelle instance du driver avec une configuration plus robuste."""
        try:
            logging.info(f"Démarrage d'une nouvelle session WebSession (headless={self.headless})...")
            options = uc.ChromeOptions()
            
            # --- AMÉLIORATION DE ROBUSTESSE ---
            # Stratégie "eager": Ne pas attendre que toutes les images soient chargées,
            # juste que le DOM soit prêt. Cela nous rend la main plus vite.
            options.page_load_strategy = 'eager'
            
            if self.headless: options.add_argument("--headless=new")
            options.add_argument("--no-sandbox"); options.add_argument("--disable-gpu"); options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")

            chrome_version = get_chrome_main_version()
            
            # --- AMÉLIORATION DE ROBUSTESSE ---
            # On augmente le timeout par défaut pour la communication entre le script et le driver.
            self.driver = uc.Chrome(
                version_main=chrome_version, 
                options=options,
                timeouts={'implicit': 0, 'pageLoad': 300, 'script': 30} # pageLoad à 5 minutes
            )
            logging.info("✅ Nouvelle instance de Chrome initialisée avec succès.")
        except Exception as e:
            logging.error("❌ Échec critique du démarrage du driver.", exc_info=True)
            raise e

    def get(self, url: str, retries: int = 2, delay: int = 3):
        """
        Navigue vers une URL avec gestion automatique des erreurs et redémarrage.
        """
        if not self.driver:
            self._start_driver()

        for attempt in range(retries + 1):
            try:
                logging.info(f"🌐 Navigation vers {url} (tentative {attempt+1}/{retries+1})")
                self.driver.get(url)
                return
            except WebDriverException as e:
                logging.warning(f"⚠️ WebDriverException : {e}. Tentative de redémarrage du driver...")
                self.quit()
                self._start_driver()
                time.sleep(delay)
        raise RuntimeError(f"Échec répété du chargement de {url} après {retries+1} tentatives.")

    def refresh(self):
        """Recharge la page courante."""
        try:
            self.driver.refresh()
            time.sleep(2)
        except Exception:
            logging.warning("Impossible de rafraîchir la page — relance du driver.")
            self._start_driver()

    def screenshot(self, path="screenshot.png"):
        """Capture d’écran de la page actuelle (debug)."""
        if self.driver:
            self.driver.save_screenshot(path)
            logging.info(f"📸 Capture enregistrée : {path}")

    def quit(self):
        """Ferme le driver proprement."""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("🧹 Session Selenium fermée proprement.")
            except Exception:
                logging.warning("⚠️ Le driver était déjà arrêté ou inaccessible.")
        self.driver = None
