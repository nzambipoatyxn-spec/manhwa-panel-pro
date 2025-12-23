#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification de l'environnement PANELia

Ce script vérifie que toutes les dépendances et outils nécessaires sont
correctement installés et configurés avant de lancer l'application.

Usage:
    python check_environment.py

Retourne:
    0 si tout est OK
    1 si des problèmes sont détectés
"""

import sys
import platform
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Tuple

# Fix encodage Windows
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class Colors:
    """Codes couleur ANSI pour terminal (compatible Windows 10+)"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Affiche un en-tête formaté."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """Affiche un message de succès."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_error(text: str):
    """Affiche un message d'erreur."""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_warning(text: str):
    """Affiche un avertissement."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_info(text: str):
    """Affiche une information."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {text}")


def check_python_version() -> bool:
    """
    Vérifie que la version de Python est compatible (3.11+).

    Returns:
        bool: True si compatible, False sinon
    """
    print_header("Vérification de Python")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    print_info(f"Version Python détectée : {version_str}")
    print_info(f"Exécutable : {sys.executable}")

    if version.major == 3 and version.minor >= 11:
        print_success(f"Python {version_str} est compatible ✓")
        return True
    else:
        print_error(f"Python {version_str} n'est PAS compatible")
        print_error("Version requise : Python 3.11 ou supérieur")
        return False


def check_os() -> Tuple[bool, str]:
    """
    Détecte le système d'exploitation.

    Returns:
        Tuple[bool, str]: (True, nom_os)
    """
    print_header("Vérification du système d'exploitation")

    system = platform.system()
    release = platform.release()
    machine = platform.machine()

    os_map = {
        "Windows": "Windows",
        "Linux": "Linux",
        "Darwin": "macOS"
    }

    os_name = os_map.get(system, "Inconnu")

    print_info(f"Système : {os_name} {release}")
    print_info(f"Architecture : {machine}")

    if system in os_map:
        print_success(f"{os_name} est supporté ✓")
        return True, system
    else:
        print_error(f"{system} n'est pas officiellement supporté")
        return False, system


def check_chrome_installed(system: str) -> bool:
    """
    Vérifie si Chrome ou Chromium est installé.

    Args:
        system (str): Nom du système ('Windows', 'Linux', 'Darwin')

    Returns:
        bool: True si Chrome trouvé, False sinon
    """
    print_header("Vérification de Google Chrome")

    chrome_paths = {
        "Windows": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "Linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ],
        "Darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    }

    paths = chrome_paths.get(system, [])

    for path in paths:
        if Path(path).exists():
            print_success(f"Chrome trouvé : {path}")

            # Tenter d'obtenir la version
            try:
                if system == "Windows":
                    result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                else:
                    result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)

                version = result.stdout.strip()
                print_info(f"Version : {version}")
            except Exception:
                print_warning("Impossible de récupérer la version")

            return True

    print_error("Chrome/Chromium non détecté")

    if system == "Windows":
        print_info("Installez Chrome : https://www.google.com/chrome/")
    elif system == "Linux":
        print_info("Installez avec : sudo apt install chromium-browser")
    elif system == "Darwin":
        print_info("Installez avec : brew install --cask google-chrome")

    return False


def check_required_packages() -> Tuple[bool, List[str]]:
    """
    Vérifie que tous les packages Python requis sont installés.

    Returns:
        Tuple[bool, List[str]]: (all_ok, liste des packages manquants)
    """
    print_header("Vérification des packages Python")

    required = [
        "streamlit",
        "undetected_chromedriver",
        "webdriver_manager",
        "selenium",
        "requests",
        "bs4",  # beautifulsoup4
        "numpy",
        "PIL",  # Pillow
        "cv2",  # opencv-python
        "httpx",
    ]

    missing = []

    for package in required:
        spec = importlib.util.find_spec(package)
        if spec is None:
            print_error(f"{package} : MANQUANT")
            missing.append(package)
        else:
            try:
                module = importlib.import_module(package)
                version = getattr(module, '__version__', 'version inconnue')
                print_success(f"{package} : {version}")
            except Exception as e:
                print_warning(f"{package} : installé mais erreur lors de l'import ({e})")

    if not missing:
        print_success("Tous les packages requis sont installés ✓")
        return True, []
    else:
        print_error(f"{len(missing)} package(s) manquant(s)")
        print_info("Installez avec : pip install -r requirements.txt")
        return False, missing


def check_webdriver_cache() -> bool:
    """
    Vérifie le cache de webdriver-manager.

    Returns:
        bool: True si cache existe
    """
    print_header("Vérification du cache WebDriver")

    home = Path.home()
    cache_dir = home / ".wdm"

    if cache_dir.exists():
        # Compter les drivers en cache
        drivers = list(cache_dir.rglob("chromedriver*"))
        print_success(f"Cache trouvé : {cache_dir}")
        print_info(f"{len(drivers)} ChromeDriver(s) en cache")

        # Afficher les versions
        for driver in drivers[:3]:  # Limiter à 3 pour pas surcharger
            print_info(f"  - {driver.parent.name}")

        return True
    else:
        print_warning("Aucun cache webdriver-manager trouvé")
        print_info("Le cache sera créé au premier lancement")
        return True  # Pas bloquant


def check_output_directory() -> bool:
    """
    Vérifie que le répertoire de sortie existe et est accessible.

    Returns:
        bool: True si OK
    """
    print_header("Vérification du répertoire de sortie")

    output_dir = Path("output")

    try:
        output_dir.mkdir(exist_ok=True)

        # Tester l'écriture
        test_file = output_dir / ".test_write"
        test_file.write_text("test")
        test_file.unlink()

        print_success(f"Répertoire de sortie accessible : {output_dir.absolute()}")
        return True

    except Exception as e:
        print_error(f"Impossible d'écrire dans le répertoire de sortie : {e}")
        return False


def check_streamlit_config() -> bool:
    """
    Vérifie la configuration Streamlit.

    Returns:
        bool: True si config existe
    """
    print_header("Vérification de la configuration Streamlit")

    config_dir = Path(".streamlit")
    secrets_file = config_dir / "secrets.toml"

    if secrets_file.exists():
        print_success(f"Configuration trouvée : {secrets_file}")
        return True
    else:
        print_warning("Fichier .streamlit/secrets.toml non trouvé")
        print_info("L'application utilisera les valeurs par défaut")
        return True  # Pas bloquant


def run_quick_test(auto_skip: bool = False) -> bool:
    """
    Lance un test rapide de WebSession.

    Args:
        auto_skip (bool): Si True, ignore automatiquement le test (pour CI/CD)

    Returns:
        bool: True si le test passe
    """
    print_header("Test de WebSession (optionnel)")

    if auto_skip:
        print_info("Test ignoré (mode automatique)")
        print_info("Pour tester manuellement : python check_environment.py --test")
        return True

    print_info("Voulez-vous tester le démarrage de Chrome ? (peut prendre 10-20s)")
    print_info("Tapez 'oui' pour lancer, ou Entrée pour passer :")

    try:
        response = input().strip().lower()

        if response in ['oui', 'o', 'yes', 'y']:
            print_info("Lancement du test...")

            try:
                from panelia.core.driver import WebSession

                with WebSession(headless=True) as session:
                    print_success(f"Chrome démarré avec succès ({session.system})")
                    print_info(f"Profil : {session.profile_dir}")

                print_success("Test WebSession RÉUSSI ✓")
                return True

            except Exception as e:
                print_error(f"Test WebSession ÉCHOUÉ : {e}")
                return False
        else:
            print_info("Test ignoré")
            return True

    except (KeyboardInterrupt, EOFError):
        print_warning("\nTest ignoré (pas d'entrée disponible)")
        return True


def main():
    """Fonction principale."""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print(r"""
    ____   ___    _   ____________  _
   / __ \ /   |  / | / / ____/ / / (_)___ _
  / /_/ // /| | /  |/ / __/ / / / / / __ `/
 / ____// ___ |/ /|  / /___/ /_/ / / /_/ /
/_/    /_/  |_/_/ |_/_____/\____/_/\__,_/

    Vérification de l'environnement
    """)
    print(Colors.RESET)

    results = []

    # 1. Python
    results.append(("Python", check_python_version()))

    # 2. OS
    os_ok, system = check_os()
    results.append(("Système", os_ok))

    # 3. Chrome
    results.append(("Chrome", check_chrome_installed(system)))

    # 4. Packages
    packages_ok, missing = check_required_packages()
    results.append(("Packages", packages_ok))

    # 5. WebDriver cache
    results.append(("Cache WebDriver", check_webdriver_cache()))

    # 6. Répertoire de sortie
    results.append(("Répertoire output", check_output_directory()))

    # 7. Config Streamlit
    results.append(("Config Streamlit", check_streamlit_config()))

    # Résumé
    print_header("RÉSUMÉ")

    total = len(results)
    passed = sum(1 for _, ok in results if ok)

    for name, ok in results:
        if ok:
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print(f"\n{Colors.BOLD}Score : {passed}/{total} tests passés{Colors.RESET}\n")

    if passed == total:
        print_success("✓ Environnement prêt ! Vous pouvez lancer l'application.")
        print_info("Commande : streamlit run app.py\n")

        # Test optionnel (auto-skip en mode non-interactif)
        auto_skip = not sys.stdin.isatty()
        run_quick_test(auto_skip=auto_skip)

        return 0
    else:
        print_error("✗ Des problèmes ont été détectés. Veuillez les corriger avant de lancer l'application.\n")

        if missing:
            print_info("Packages manquants à installer :")
            for pkg in missing:
                print(f"  - {pkg}")
            print("\nInstallez avec : pip install -r requirements.txt\n")

        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Vérification annulée{Colors.RESET}")
        sys.exit(130)
