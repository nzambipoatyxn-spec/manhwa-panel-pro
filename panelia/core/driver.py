# core.py
"""
WebSession - Gestion robuste et multi-plateforme de Selenium avec undetected-chromedriver

SOLUTION DÉFINITIVE aux problèmes de versions ChromeDriver :
- Détection automatique de la version Chrome installée
- Téléchargement automatique du ChromeDriver compatible via webdriver-manager
- Support multi-plateforme : Windows, Linux, macOS
- Gestion des profils isolés (Windows : %TEMP%, Linux/macOS : /tmp)
- Mode headless moderne
- Anti-détection via undetected-chromedriver

Auteur: PANELia Team
Dernière mise à jour: 2025-12-03
"""

import os
import platform
import random
import time
import tempfile
from pathlib import Path
from typing import Optional

import undetected_chromedriver as uc
from loguru import logger
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType


class WebSession:
    """
    Gestionnaire de session Selenium multi-plateforme avec gestion automatique
    des versions ChromeDriver.

    Attributes:
        headless (bool): Mode sans interface graphique
        profile_dir (str): Répertoire du profil utilisateur Chrome isolé
        driver (uc.Chrome): Instance du WebDriver
        system (str): Système d'exploitation détecté (Windows, Linux, Darwin)
    """

    def __init__(self, headless: bool = True, driver_version: Optional[str] = None, profile_id: Optional[str] = None):
        """
        Initialise une session WebDriver.

        Args:
            headless (bool): Si True, Chrome tourne en mode headless
            driver_version (str, optional): Version spécifique de ChromeDriver à utiliser.
            profile_id (str, optional): Identifiant pour un profil persistant (ex: 'default').
                                       Si fourni, le profil est stocké dans ./profiles/[profile_id]
        """
        self.headless = headless
        self.driver_version = driver_version
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
        self.profile_id = profile_id
        self.profile_dir = self._make_profile()
        self.driver = None

        logger.info(f"Initialisation WebSession - OS: {self.system}, Headless: {headless}, Profil: {profile_id or 'Temp'}")
        self._start_driver()

    def _make_profile(self) -> str:
        """
        Crée un répertoire de profil Chrome isolé ou persistant.
        """
        # Si profile_id est fourni, on utilise un dossier local persistant
        if self.profile_id:
            base = Path.cwd() / "profiles"
            base.mkdir(exist_ok=True)
            profile_path = base / self.profile_id
            profile_path.mkdir(exist_ok=True)
            logger.info(f"Utilisation du profil PERSISTANT : {profile_path}")
            return str(profile_path)

        # Sinon, utilisation du dossier temporaire classique
        if self.system == "Windows":
            base = Path(tempfile.gettempdir()) / "panelia_profiles"
        else:
            base = Path("/tmp/panelia_profiles")

        base.mkdir(exist_ok=True, parents=True)

        # Profil unique par processus pour éviter les conflits
        profile_name = f"profile_{os.getpid()}_{random.randint(1000, 9999)}"
        profile_path = base / profile_name
        profile_path.mkdir(exist_ok=True)

        logger.info(f"Profil Chrome TEMPORAIRE créé : {profile_path}")
        return str(profile_path)

    def _get_chromedriver_path(self) -> Optional[str]:
        """
        Télécharge ou récupère le chemin du ChromeDriver compatible avec la version
        de Chrome installée sur le système.

        Returns:
            str: Chemin vers l'exécutable ChromeDriver, ou None si échec

        Note:
            Utilise webdriver-manager qui :
            1. Détecte la version de Chrome installée
            2. Télécharge le ChromeDriver correspondant si nécessaire
            3. Le met en cache pour les utilisations futures
        """
        try:
            logger.info("Recherche de la version Chrome installée...")

            # webdriver-manager télécharge automatiquement la bonne version
            driver_path = ChromeDriverManager(
                chrome_type=ChromeType.GOOGLE,
                driver_version=self.driver_version
            ).install()

            logger.info(f"ChromeDriver trouvé/téléchargé : {driver_path}")
            return driver_path

        except Exception as e:
            logger.warning(f"Échec webdriver-manager : {e}")
            logger.warning("Undetected ChromeDriver va tenter sa propre gestion...")
            return None

    def _start_driver(self):
        """
        Démarre le driver Chrome avec undetected-chromedriver et configuration optimale.

        Stratégie de démarrage :
        1. Tente d'utiliser webdriver-manager pour obtenir le bon ChromeDriver
        2. Si échec, laisse undetected-chromedriver gérer (fallback)
        3. Configure les options Chrome (profil, headless, sandbox, etc.)
        4. Lance le driver

        Raises:
            Exception: Si le démarrage échoue après tous les fallbacks
        """
        logger.info("Démarrage de Chrome avec undetected-chromedriver...")

        # Configuration des options Chrome
        options = uc.ChromeOptions()
        options.page_load_strategy = "eager"  # Ne pas attendre le chargement complet
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--window-size=1920,1080")

        # Options de sécurité/performance
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")  # Recommandé pour Windows

        if self.headless:
            # Mode headless moderne (Chrome 109+)
            options.add_argument("--headless=new")
        else:
            # Mode visible : désactiver l'automatisation flag pour plus de discrétion
            options.add_argument("--disable-infobars")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

        try:
            # Stratégie 1 : Utiliser webdriver-manager
            driver_path = self._get_chromedriver_path()

            if driver_path:
                logger.info("Utilisation du ChromeDriver via webdriver-manager")
                # IMPORTANT : utiliser driver_executable_path au lieu de service
                # car undetected-chromedriver patche le driver
                self.driver = uc.Chrome(
                    options=options,
                    driver_executable_path=driver_path,
                    use_subprocess=True,
                    version_main=None  # Laisser UC détecter
                )
            else:
                # Stratégie 2 : Fallback - laisser UC gérer
                logger.info("Fallback : undetected-chromedriver gère la version")
                self.driver = uc.Chrome(
                    options=options,
                    use_subprocess=True,
                    version_main=None  # Auto-détection
                )

            logger.info("✅ Chrome initialisé avec succès")

            # Afficher la version pour debugging
            chrome_version = self.driver.capabilities.get('browserVersion', 'Inconnue')
            driver_version = self.driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'Inconnue')
            logger.info(f"Chrome: {chrome_version} | ChromeDriver: {driver_version}")

        except Exception as e:
            logger.error(f"❌ Échec du démarrage Chrome : {e}", exc_info=True)
            self._log_troubleshooting_tips()
            raise

    def _log_troubleshooting_tips(self):
        """
        Affiche des conseils de dépannage selon le système d'exploitation.
        """
        logger.error("=" * 60)
        logger.error("CONSEILS DE DÉPANNAGE :")

        if self.system == "Windows":
            logger.error("1. Vérifiez que Chrome est installé : C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
            logger.error("2. Mettez à jour Chrome : chrome://settings/help")
            logger.error("3. Réinstallez Chrome si nécessaire")
        elif self.system == "Linux":
            logger.error("1. Installez Chrome/Chromium : sudo apt install chromium-browser")
            logger.error("2. Vérifiez : which chromium-browser")
            logger.error("3. Installez les dépendances : sudo apt install libnss3 libgconf-2-4")
        elif self.system == "Darwin":
            logger.error("1. Installez Chrome : brew install --cask google-chrome")
            logger.error("2. Autorisez Chrome dans Préférences Système > Sécurité")

        logger.error("4. Videz le cache webdriver-manager : rm -rf ~/.wdm")
        logger.error("5. Réinstallez : pip install --force-reinstall undetected-chromedriver webdriver-manager")
        logger.error("=" * 60)

    def get(self, url: str, timeout: int = 25):
        """
        Navigue vers une URL avec délai aléatoire pour simuler un comportement humain.

        Args:
            url (str): URL de destination
            timeout (int): Timeout de chargement en secondes (défaut: 25)
        """
        self.driver.set_page_load_timeout(timeout)
        logger.info(f"Navigation vers : {url}")
        self.driver.get(url)

        # Délai aléatoire pour anti-détection
        delay = random.uniform(0.5, 1.5)
        time.sleep(delay)

    @property
    def page_source(self) -> str:
        """
        Retourne le code HTML de la page actuelle.

        Returns:
            str: Code source HTML complet
        """
        return self.driver.page_source

    def quit(self):
        """
        Ferme proprement le driver et nettoie les ressources.
        """
        try:
            if self.driver:
                self.driver.quit()
                logger.info("✅ Chrome fermé proprement")
        except Exception as e:
            logger.warning(f"Erreur lors de la fermeture : {e}")

    def __enter__(self):
        """Support du context manager (with statement)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Nettoyage automatique à la sortie du context manager."""
        self.quit()


# ===== Fonction utilitaire pour tests rapides =====

def test_websession():
    """
    Fonction de test pour vérifier que WebSession fonctionne correctement.

    Usage:
        python core.py
    """
    # Fix encodage Windows
    if platform.system() == "Windows":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Loguru est configuré par défaut, pas besoin de basicConfig

    print("\n" + "=" * 60)
    print("TEST DE WEBSESSION")
    print("=" * 60)

    try:
        with WebSession(headless=True) as session:
            print(f"\nOK Systeme detecte : {session.system}")
            print(f"OK Profil Chrome : {session.profile_dir}")

            # Test de navigation
            session.get("https://www.google.com", timeout=10)
            print(f"OK Navigation reussie vers Google")
            print(f"OK Titre de la page : {session.driver.title}")

        print("\nOK TOUS LES TESTS SONT PASSES !")
        print("=" * 60 + "\n")
        return True

    except Exception as e:
        print(f"\nERREUR ECHEC DU TEST : {e}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    # Lancer le test si ce fichier est exécuté directement
    success = test_websession()
    sys.exit(0 if success else 1)
