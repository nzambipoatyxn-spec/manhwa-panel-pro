# core.py
"""
Version professionnelle, stable, future-proof :
- Google Chrome stable (DEB)
- Undetected ChromeDriver auto-adapté
- Profil utilisateur isolé
- Aucun version_main forcé
"""

import logging
import os
import random
import time
from pathlib import Path
import undetected_chromedriver as uc


class WebSession:
    def __init__(self, headless=True):
        self.headless = headless
        self.profile_dir = self._make_profile()
        self.driver = None
        self._start_driver()

    def _make_profile(self):
        base = Path("/tmp/panelia_profiles")
        base.mkdir(exist_ok=True, parents=True)
        p = base / f"profile_{os.getpid()}_{random.randint(1000,9999)}"
        p.mkdir(exist_ok=True)
        return str(p)

    def _start_driver(self):
        logging.info("Démarrage Chrome...")

        options = uc.ChromeOptions()
        options.page_load_strategy = "eager"
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        if self.headless:
            options.add_argument("--headless=new")

        # UC auto-détecte la version de Google Chrome STABLE
        self.driver = uc.Chrome(options=options, use_subprocess=True)

        logging.info("Chrome initialisé.")

    def get(self, url, timeout=25):
        self.driver.set_page_load_timeout(timeout)
        self.driver.get(url)
        time.sleep(random.uniform(0.5, 1.0))

    @property
    def page_source(self):
        return self.driver.page_source

    def quit(self):
        try:
            self.driver.quit()
        except:
            pass
        logging.info("Chrome fermé proprement.")
