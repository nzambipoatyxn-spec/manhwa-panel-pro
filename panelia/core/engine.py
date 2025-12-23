# scraper_engine.py
"""
ScraperEngine : backend indépendant pour exécuter le scraping en batch parallèle,
gérer un pool de drivers Selenium, limiter globalement le débit, et retourner
les résultats via une callback exécutée côté UI (streamlit).
"""

import time
import random
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import threading

from loguru import logger
from panelia.core.driver import WebSession
from panelia.scrapers.factory import (
    scrape_images_mangadex,
    scrape_images_smart,
    process_image_smart
)

from panelia.utils.http import download_all_images
from panelia.utils.metrics import get_collector
from panelia.utils.validation import get_validator, ValidationError
from panelia.utils.errors import get_error_handler, classify_and_log_error, ErrorCategory

class ScraperEngine:
    def __init__(
        self,
        work_dir: str = "output",
        num_drivers: int = 3,
        image_workers_per_chap: int = 4,
        throttle_min: float = 0.08,
        throttle_max: float = 0.15,
        driver_start_delay: float = 0.8
    ):
        # Valider les paramètres d'entrée
        validator = get_validator()
        num_drivers = validator.validate_num_drivers(num_drivers)
        image_workers_per_chap = validator.validate_max_workers(image_workers_per_chap)

        self.work_dir = Path(work_dir)
        self.num_drivers = max(1, num_drivers)
        self.image_workers_per_chap = max(1, image_workers_per_chap)
        self.throttle_min = throttle_min
        self.throttle_max = throttle_max
        self.driver_start_delay = driver_start_delay

        self.driver_pool: List[WebSession] = []
        self.global_download_slots = threading.Semaphore(self.num_drivers * self.image_workers_per_chap)

        logger.info(f"ScraperEngine initialisé avec validation - Drivers: {self.num_drivers}, Workers: {self.image_workers_per_chap}")

    def start_driver_pool(self):
        logger.info(f"Initialisation du pool de {self.num_drivers} drivers Selenium...")
        drivers = []
        for i in range(self.num_drivers):
            try:
                # small delay to reduce race conditions during undetected_chromedriver patching
                time.sleep(self.driver_start_delay)
                ws = WebSession(headless=True)
                drivers.append(ws)
                logger.info(f"Driver {i} initialisé.")
            except Exception as e:
                logger.error(f"Erreur création driver {i} : {e}", exc_info=True)
                # cleanup
                for d in drivers:
                    try: d.quit()
                    except: pass
                raise
        self.driver_pool = drivers
        logger.info("Pool de drivers initialisé.")

    def stop_driver_pool(self):
        logger.info("Fermeture du driver pool...")
        for idx, d in enumerate(self.driver_pool):
            try:
                d.quit()
                logger.info(f"Driver pool: instance {idx} fermée.")
            except Exception:
                logger.warning(f"Driver pool: échec fermeture instance {idx}.")
        self.driver_pool = []

    def _throttle_short(self):
        time.sleep(random.uniform(self.throttle_min, self.throttle_max))

    def _process_single_chapter(self, chap_num: float, chap_url: str, driver_ws: WebSession, params: Dict[str, Any]) -> Dict[str, Any]:
        # Valider les entrées
        validator = get_validator()
        try:
            chap_num = validator.validate_chapter_number(chap_num)
            chap_url = validator.validate_url(chap_url, allow_any_domain=True)
        except ValidationError as e:
            error_msg = f"Validation échouée : {e}"
            logger.error(f"[CHAP {chap_num}] {error_msg}")
            return {"chap_num": chap_num, "chap_url": chap_url, "found_count": 0, "downloaded_count": 0, "panels_saved": 0, "error": error_msg}

        prefix = f"[CHAP {chap_num}]"
        result = {"chap_num": chap_num, "chap_url": chap_url, "found_count": 0, "downloaded_count": 0, "panels_saved": 0, "error": None}

        # Démarrer le tracking des métriques
        collector = get_collector()
        collector.start_chapter(chap_num, chap_url)

        try:
            site_type = "mangadex" if "mangadex" in chap_url else "madara"
            logger.info(f"{prefix} Détection site -> {site_type}")

            # Valider les paramètres avant utilisation
            validated_params = validator.validate_params_dict(params)

            # extraction des URLs images
            if site_type == "mangadex":
                image_urls = scrape_images_mangadex(chap_url)
            else:
                image_urls = scrape_images_smart(driver_ws, chap_url, min_width=validated_params.get("min_image_width_value", 400))

            result["found_count"] = len(image_urls)
            logger.info(f"{prefix} {result['found_count']} images trouvées.")

            # Mettre à jour les métriques avec le nombre d'images trouvées
            collector.update_chapter(chap_num, images_found=len(image_urls))

            if not image_urls:
                collector.end_chapter(chap_num, success=False, error_message="Aucune image trouvée")
                return result

            # throttle court avant download
            self._throttle_short()

            # Acquire global slot to avoid flooding
            acquired = self.global_download_slots.acquire(timeout=10)
            try:
                image_bytes_list = download_all_images(
                    image_urls,
                    chapter_num=chap_num,
                    referer=chap_url,
                    timeout=validated_params.get("timeout_value", 30),
                    max_workers=self.image_workers_per_chap
                )
            finally:
                if acquired:
                    self.global_download_slots.release()

            result["downloaded_count"] = len(image_bytes_list)
            logger.info(f"{prefix} {result['downloaded_count']} images téléchargées.")

            # Mettre à jour les métriques avec le nombre d'images téléchargées
            collector.update_chapter(chap_num, images_downloaded=len(image_bytes_list))

            if result["downloaded_count"] == 0:
                collector.end_chapter(chap_num, success=False, error_message="Aucune image téléchargée")
                return result

            # traitement et sauvegarde
            try:
                saved = process_image_bytes_and_save(
                    image_bytes_list,
                    validated_params.get("final_manhwa_name", "unknown"),
                    chap_num,
                    quality=validated_params.get("quality_value", 92)
                )
                result["panels_saved"] = saved
                logger.info(f"{prefix} {saved} planches sauvegardées.")

                # Mettre à jour les métriques avec le nombre de planches traitées
                collector.update_chapter(chap_num, images_processed=saved)
            except Exception as e:
                context = classify_and_log_error(e, chapter_num=chap_num)
                logger.error(f"{prefix} Erreur processing: {context.user_message}", exc_info=True)
                result["error"] = context.user_message
                collector.end_chapter(chap_num, success=False, error_message=context.user_message)
                return result

            # Terminer le tracking avec succès
            collector.end_chapter(chap_num, success=True)
            return result

        except Exception as e:
            context = classify_and_log_error(e, chapter_num=chap_num, url=chap_url)
            logger.error(f"{prefix} Erreur critique: {context.user_message}", exc_info=True)
            result["error"] = context.user_message
            collector.end_chapter(chap_num, success=False, error_message=context.user_message)
            return result

    def run_chapter_batch(self, chapters: Dict[float, str], params: Dict[str, Any], ui_progress_callback=None) -> List[Dict[str, Any]]:
        """
        Exécute les chapitres en parallèle en utilisant un ThreadPoolExecutor
        (max_workers = num_drivers).
        ui_progress_callback(completed, total, result) est appelé dans le thread principal.
        """
        if not self.driver_pool:
            self.start_driver_pool()

        sorted_chaps = sorted(chapters.items())
        total = len(sorted_chaps)
        results = []

        with ThreadPoolExecutor(max_workers=self.num_drivers) as executor:
            futures = []
            for idx, (chap_num, chap_url) in enumerate(sorted_chaps):
                driver_ws = self.driver_pool[idx % len(self.driver_pool)]
                future = executor.submit(self._process_single_chapter, chap_num, chap_url, driver_ws, params)
                futures.append((future, chap_num, chap_url))

            completed = 0
            for fut, chap_num, chap_url in futures:
                res = fut.result()
                results.append(res)
                completed += 1
                if ui_progress_callback:
                    try:
                        ui_progress_callback(completed, total, res)
                    except Exception:
                        pass

        return results

# petit wrapper local pour utiliser process_image_smart (qui retourne PIL images)
def process_image_bytes_and_save(image_bytes_list, manhwa_name, chapter_num, quality=92):
    """
    Utilise process_image_smart (importé de scrapers) puis sauvegarde les images.
    Retourne le nombre de fichiers sauvegardés.
    """
    from pathlib import Path
    from panelia.scrapers.factory import process_image_smart

    safe_manhwa_name = ''.join(c for c in manhwa_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
    safe_chap = str(chapter_num).replace('.', '_')
    output_dir = Path("output") / safe_manhwa_name / safe_chap
    output_dir.mkdir(parents=True, exist_ok=True)

    total_files = 0
    for image_bytes in image_bytes_list:
        try:
            images_to_save = process_image_smart(image_bytes)
            for img in images_to_save:
                filename = f"planche_{total_files+1:03d}.jpg"
                panel_path = output_dir / filename
                img.convert('RGB').save(panel_path, "JPEG", quality=quality, optimize=True)
                total_files += 1
        except Exception as e:
            logger.warning(f"Erreur sauvegarde panel: {e}", exc_info=True)
    return total_files
