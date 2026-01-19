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
from typing import List, Dict, Any, Optional
import threading

from loguru import logger
from panelia.core.driver import WebSession
from panelia.scrapers.factory import (
    scrape_images_mangadex,
    scrape_images_smart,
    process_image_smart
)

from panelia.utils.http import stream_download_images
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
        driver_start_delay: float = 0.8,
        headless: bool = True,
        profile_id: Optional[str] = None
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
        self.headless = headless
        self.profile_id = profile_id

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
                ws = WebSession(headless=self.headless, profile_id=self.profile_id)
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
        """
        Process un seul chapitre. driver_ws peut être None pour les sites 'driverless'.
        """
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
                if driver_ws is None:
                    # Sécurité si on arrive ici sans driver pour un site qui en a besoin
                    logger.error(f"{prefix} Site non-MangaDex demande driverless mais driver_ws est None.")
                    return {"chap_num": chap_num, "chap_url": chap_url, "found_count": 0, "downloaded_count": 0, "panels_saved": 0, "error": "Driver manquant pour ce site"}
                
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

            # Création du dossier de sortie à l'avance
            manhwa_name = validated_params.get("final_manhwa_name", "unknown")
            safe_manhwa_name = ''.join(c for c in manhwa_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            safe_chap = str(chap_num).replace('.', '_')
            output_dir = Path(self.work_dir) / safe_manhwa_name / safe_chap
            output_dir.mkdir(parents=True, exist_ok=True)

            # --- LOOP DE STREAMING ---
            acquired = self.global_download_slots.acquire(timeout=10)
            try:
                # On itère sur le générateur pour traiter les images une par une
                generator = stream_download_images(
                    image_urls,
                    chapter_num=chap_num,
                    referer=chap_url,
                    timeout=validated_params.get("timeout_value", 30),
                    max_workers=self.image_workers_per_chap
                )

                panels_saved_total = 0
                downloaded_count = 0

                for img_bytes in generator:
                    downloaded_count += 1
                    # Traitement et sauvegarde immédiate d'une image
                    saved_count = process_and_save_single_image(
                        img_bytes,
                        output_dir,
                        current_panel_index=panels_saved_total,
                        chap_num=chap_num,
                        quality=validated_params.get("quality_value", 92),
                        cleaner=params.get("cleaner_instance") if validated_params.get("enable_cleaning") else None
                    )
                    panels_saved_total += saved_count
                    
                    # Mise à jour des métriques au fil de l'eau
                    collector.update_chapter(chap_num, images_downloaded=downloaded_count, images_processed=panels_saved_total)

                result["downloaded_count"] = downloaded_count
                result["panels_saved"] = panels_saved_total
                
            finally:
                if acquired:
                    self.global_download_slots.release()

            if result["panels_saved"] == 0 and result["downloaded_count"] > 0:
                logger.warning(f"{prefix} Aucune planche n'a pu être sauvée malgré les téléchargements.")

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
        from panelia.scrapers.config import SUPPORTED_SITES
        
        sorted_chaps = sorted(chapters.items())
        total = len(sorted_chaps)
        results = []

        # ... (IA Setup logic kept later)
        cleaner_instance = None
        if params.get("enable_cleaning"):
            from panelia.utils.cleaning import ManhwaCleaner
            cleaner_instance = ManhwaCleaner()
            params["cleaner_instance"] = cleaner_instance

        # ANALYSE DU MÉLANGE SELENIUM / DRIVERLESS
        # MangaDex supporte le driverless. Pour les autres, on force Selenium.
        driverless_tasks = []
        selenium_tasks = []
        
        for chap_num, chap_url in sorted_chaps:
            is_driverless = False
            for domain, cfg in SUPPORTED_SITES.items():
                if domain in chap_url:
                    # cfg = (func, needs_selenium, allow_driverless)
                    if len(cfg) >= 3 and cfg[2]: # allow_driverless is True
                        is_driverless = True
                    break
            
            if is_driverless:
                driverless_tasks.append((chap_num, chap_url))
            else:
                selenium_tasks.append((chap_num, chap_url))

        # On démarre le driver pool seulement si nécessaire
        if selenium_tasks and not self.driver_pool:
            self.start_driver_pool()

        # On utilise un pool de threads global dimensionné pour absorber le driverless
        # (Pool Selenium + 10 workers driverless fixe par sécurité)
        max_total_workers = self.num_drivers + 10
        
        with ThreadPoolExecutor(max_workers=max_total_workers) as executor:
            futures = []
            
            # 1. Soumission des tâches Selenium (consomment le pool limité)
            for idx, (chap_num, chap_url) in enumerate(selenium_tasks):
                driver_ws = self.driver_pool[idx % len(self.driver_pool)]
                future = executor.submit(self._process_single_chapter, chap_num, chap_url, driver_ws, params)
                futures.append(future)

            # 2. Soumission des tâches Driverless (volent de leurs propres ailes)
            for chap_num, chap_url in driverless_tasks:
                future = executor.submit(self._process_single_chapter, chap_num, chap_url, None, params)
                futures.append(future)

            completed = 0
            for fut in futures:
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
def process_and_save_single_image(image_bytes: bytes, output_dir: Path, current_panel_index: int, chap_num: float, quality=92, cleaner=None):
    """
    Traite une SEULE image téléchargée (découpage + IA) et la sauvegarde dans output_dir.
    Retourne le nombre de planches générées.
    Nomenclature : ChXX_PXX.jpg
    """
    from panelia.scrapers.factory import process_image_smart
    
    saved_count = 0
    try:
        images_to_save = process_image_smart(image_bytes)
        safe_chap = str(chap_num).replace('.', '_')
        for img in images_to_save:
            # Nettoyage IA
            if cleaner:
                img = cleaner.process_pil(img)

            # Nomenclature demandée : ChXX_PXX
            filename = f"Ch{safe_chap}_P{current_panel_index + saved_count + 1:03d}.jpg"
            panel_path = output_dir / filename
            img.convert('RGB').save(panel_path, "JPEG", quality=quality, optimize=True)
            saved_count += 1
    except Exception as e:
        logger.warning(f"Erreur processing image individuelle: {e}")
    
    return saved_count
