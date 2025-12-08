# http_utils.py
"""
Utilitaires HTTP robustes : download_image_smart + download_all_images
Retry + backoff exponentiel, rotation User-Agent, referer, fallback HTTP2 -> HTTP1
Utilisé par app.py et scraper_engine.py
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor
import httpx
from loguru import logger
from metrics import get_collector

USER_AGENTS = [
    # Desktop Chrome / Firefox / Safari
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
    # Mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
]

def download_image_smart(url, referer=None, chapter_num=None, timeout=30):
    """
    Télécharge une image en mode robuste :
      - retry exponentiel (max_retries)
      - rotation User-Agent
      - HTTP2 first then HTTP1 fallback
      - referer si fourni
    Retourne bytes ou None.
    """
    max_retries = 4
    backoff_base = 0.5

    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "image/avif,image/webp,image/png,image/*;q=0.8",
            }
            if referer:
                headers["Referer"] = referer

            use_http2 = (attempt == 0)

            # httpx client context
            with httpx.Client(http2=use_http2, timeout=httpx.Timeout(timeout), follow_redirects=True, headers=headers) as client:
                r = client.get(url)
                r.raise_for_status()
                img_bytes = r.content
                logger.info(f"[DL][CHAP {chapter_num}] Succès tentative {attempt+1} ({len(img_bytes)} octets)")

                # Enregistrer le téléchargement réussi dans les métriques
                if chapter_num is not None:
                    collector = get_collector()
                    collector.add_download(chapter_num, len(img_bytes), success=True)

                return img_bytes

        except Exception as e:
            wait_time = backoff_base * (2 ** attempt)
            logger.warning(f"[DL][CHAP {chapter_num}] Tentative {attempt+1} échouée -> {e}. Nouvelle tentative dans {wait_time:.1f}s.")
            time.sleep(wait_time)

    logger.error(f"[DL][CHAP {chapter_num}] ÉCHEC FINAL pour {url}")

    # Enregistrer l'échec dans les métriques
    if chapter_num is not None:
        collector = get_collector()
        collector.add_download(chapter_num, 0, success=False)

    return None


def download_all_images(image_urls, chapter_num=None, referer=None, timeout=30, max_workers=4):
    """
    Télécharge en parallèle les URLs passées, en utilisant download_image_smart.
    Retourne la liste des bytes téléchargés (ordre pouvant différer).
    """
    results = []
    def _task(url):
        return download_image_smart(url, referer=referer, chapter_num=chapter_num, timeout=timeout)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_task, url) for url in image_urls]
        for fut in futures:
            res = fut.result()
            if res:
                results.append(res)

    return results
