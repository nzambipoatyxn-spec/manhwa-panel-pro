# scrapers.py - v2.0 - Moteur Amélioré

import re
import logging
import time
import json
import io
from typing import List
from urllib.parse import urljoin

import requests
import cv2
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==============================================================================
# SECTION 1 : DÉCOUVERTE DES CHAPITRES (Logique existante et stable)
# ==============================================================================

def discover_chapters_madara_theme(session_or_url, series_url: str = None) -> dict[float, str]:
    """
    Scraper Madara v5 - Tolérant & robuste.
    Compatible WebSession, webdriver.Chrome ou simple URL string.
    Gère les iFrames publicitaires et les structures Madara modernes.
    """
    from core import WebSession  # Sécurité pour usage indépendant
    try:
        # --- 1️⃣ Déterminer si le premier argument est une session ou juste une URL ---
        if isinstance(session_or_url, str):
            # Cas d'appel direct : discover_chapters_madara_theme("https://...")
            session = WebSession(headless=True)
            series_url = session_or_url
        else:
            # Cas normal depuis app.py
            session = session_or_url

        logging.info(f"[MadaraV5] Découverte des chapitres sur {series_url}")
        session.get(series_url)
        time.sleep(5)  # Laisse le temps aux éléments publicitaires de charger

        # --- 2️⃣ Tentative de nettoyage d'iFrames publicitaires ---
        try:
            iframes = session.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logging.info(f"[MadaraV5] {len(iframes)} iFrame(s) détectée(s). Tentative de nettoyage...")
                for iframe in iframes:
                    try:
                        session.switch_to.frame(iframe)
                        close_buttons = session.find_elements(By.CSS_SELECTOR, "[aria-label*='close' i], .close, .x")
                        if close_buttons:
                            close_buttons[0].click()
                            logging.info("🧹 Pub fermée dans une iFrame.")
                            session.switch_to.default_content()
                            time.sleep(1)
                            break
                        session.switch_to.default_content()
                    except Exception:
                        session.switch_to.default_content()
                        continue
        except Exception as e:
            logging.debug(f"[MadaraV5] Aucun iframe gênant détecté ou nettoyage ignoré : {e}")

        # --- 3️⃣ Extraction du HTML une fois la page propre ---
        page_html = session.page_source
        soup = BeautifulSoup(page_html, 'html.parser')

        # Certains thèmes Madara utilisent #chapterlist, d'autres .chapter-list ou ul.main
        container = soup.find('div', id='chapterlist') or soup.find('ul', class_='main') or soup.find('div', class_='listing-chapters')
        if not container:
            logging.warning(f"[MadaraV5] Aucun conteneur Madara détecté pour {series_url}")
            return {}

        chapter_map = {}
        items = container.find_all(['li', 'div'], recursive=True)
        for item in items:
            link_tag = item.find('a')
            if not link_tag:
                continue
            href = link_tag.get('href')
            text = item.get_text(strip=True)
            match = re.search(r'(?:Chapter|Ch\.?)\s*([\d\.]+)', text, re.IGNORECASE)
            if href and match:
                try:
                    chap_num = float(match.group(1))
                    if chap_num not in chapter_map:
                        chapter_map[chap_num] = urljoin(series_url, href.strip())
                except (ValueError, IndexError):
                    continue

        logging.info(f"[MadaraV5] ✅ {len(chapter_map)} chapitres détectés pour {series_url}")
        return chapter_map

    except Exception as e:
        logging.error(f"❌ Erreur critique dans MadaraV5 pour {series_url}: {e}", exc_info=True)
        return {}
    finally:
        # Si on a créé une session temporairement, on la ferme à la fin
        if isinstance(session_or_url, str):
            session.quit()


def discover_chapters_asuracomic(source, series_url: str) -> dict[float, str]:
    """
    Scraper AsuraComic v5 - 2025
    Gère le scroll dynamique et les classes Tailwind du nouveau design.
    """
    from core import WebSession
    try:
        # 1️⃣ Récupération du HTML depuis une WebSession ou string
        if not isinstance(source, str):
            session = source
            session.get(series_url)
            time.sleep(3)

            # Scroll complet pour forcer le rendu dynamique
            logging.info("AsuraComic : Scroll pour charger tous les chapitres...")
            last_height, stable = 0, 0
            while stable < 4:
                session.execute_script("window.scrollBy(0, 1000);")
                time.sleep(0.8)
                new_height = session.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    stable += 1
                else:
                    stable = 0
                last_height = new_height

            page_html = session.page_source
        else:
            page_html = source

        soup = BeautifulSoup(page_html, 'html.parser')
        chapter_map = {}

        # 2️⃣ Extraction via les liens "chapter/"
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/chapter/' not in href:
                continue
            text = a_tag.get_text(strip=True)
            match = re.search(r'(?:Chapter|Ch\.?)\s*([\d\.]+)', text, re.IGNORECASE)
            if match:
                try:
                    chap_num = float(match.group(1))
                    abs_url = urljoin(series_url, href)
                    if chap_num not in chapter_map:
                        chapter_map[chap_num] = abs_url
                except ValueError:
                    continue

        # 3️⃣ Vérification finale
        if not chapter_map:
            logging.warning(f"AsuraComic : aucun chapitre trouvé après scroll pour {series_url}")
        else:
            logging.info(f"✅ AsuraComic v5 : {len(chapter_map)} chapitres détectés pour {series_url}")

        return chapter_map

    except Exception as e:
        logging.error(f"Erreur critique dans discover_chapters_asuracomic : {e}", exc_info=True)
        return {}

def discover_chapters_mangadex(series_url: str) -> dict[float, str]:
    """Scraper pour MangaDex via API officielle."""
    # Cette logique est stable et reste inchangée
    chapter_map = {}
    uuid_match = re.search(r'title/([a-f0-9\-]{36})', series_url)
    if not uuid_match: return {}
    manga_uuid = uuid_match.group(1)
    api_url = f"https://api.mangadex.org/manga/{manga_uuid}/feed"
    params = {"translatedLanguage[]": "en", "order[chapter]": "desc", "limit": 500}
    offset, total = 0, None
    while total is None or offset < total:
        params["offset"] = offset
        try:
            response = requests.get(api_url, params=params, timeout=10); response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur API MangaDex : {e}"); break
        if data.get("result") != "ok" or not data.get("data"): break
        if total is None: total = data.get("total", 0)
        for chapter_data in data["data"]:
            attrs = chapter_data.get("attributes", {})
            chap_num_str, chap_id = attrs.get("chapter"), chapter_data.get("id")
            if chap_num_str and chap_id:
                try:
                    chap_num = float(chap_num_str)
                    if chap_num not in chapter_map:
                        chapter_map[chap_num] = f"https://mangadex.org/chapter/{chap_id}"
                except (ValueError, TypeError): continue
        offset += len(data["data"])
        if not data.get("data"): break
    return chapter_map

def discover_chapters_flamecomics(session, series_url: str) -> dict[float, str]:
    """Scraper FlameComics v8 FINAL - Parse les éléments DOM après scroll."""
    # Cette logique est stable et reste inchangée
    chapter_map = {}
    try:
        session.get(series_url); time.sleep(3)
        last_height, stable_iterations, max_stable = 0, 0, 3
        logging.info("🔄 Début du scroll infini FlameComics...")
        while stable_iterations < max_stable:
            session.execute_script("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(2)
            new_height = session.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                stable_iterations += 1
            else:
                stable_iterations = 0
            last_height = new_height
        logging.info("✅ Scroll terminé, parsing des chapitres...")
        chapter_elements = session.find_elements(By.CSS_SELECTOR, "a[href*='/series/']")
        for element in chapter_elements:
            try:
                href, text = element.get_attribute('href'), element.text.strip()
                if not href or '/series/' not in href: continue
                match = re.search(r'(?:Chapter|Ch\.?)\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
                if match and href:
                    chap_num = float(match.group(1))
                    parts = href.rstrip('/').split('/')
                    if len(parts) >= 5 and chap_num not in chapter_map:
                        chapter_map[chap_num] = href
            except Exception: continue
        logging.info(f"✅ FlameComics: {len(chapter_map)} chapitres uniques extraits")
    except Exception as e:
        logging.error(f"❌ Erreur FlameComics scraper: {e}", exc_info=True)
    return chapter_map

def discover_chapters_raijin_scans(page_html: str, series_url: str) -> dict[float, str]:
    """
    NOUVEAU : Scraper spécialisé pour la structure "custom" de Raijin Scans.
    """
    soup = BeautifulSoup(page_html, 'html.parser')
    chapter_map = {}
    
    # On cible la liste qui contient tous les chapitres
    chapter_list_container = soup.find('ul', class_='scroll-sm')
    
    if not chapter_list_container:
        logging.warning(f"Raijin Scans : conteneur de chapitres 'ul.scroll-sm' introuvable.")
        return {}
        
    # On trouve tous les éléments de la liste
    chapter_items = chapter_list_container.find_all('li', class_='item')

    for item in chapter_items:
        link_tag = item.find('a')
        if not link_tag:
            continue
            
        href = link_tag.get('href')
        # Le texte du lien contient déjà "Chapitre XXX"
        text = link_tag.text.strip()
        
        # Regex pour extraire le numéro, ex: "Chapitre 207"
        match = re.search(r'Chapitre\s*([\d\.]+)', text, re.IGNORECASE)
        
        if href and match:
            try:
                chap_num = float(match.group(1))
                
                # urljoin gère le fait de construire l'URL complète
                full_url = urljoin(series_url, href.strip())
                
                if chap_num not in chapter_map:
                    chapter_map[chap_num] = full_url
            except (ValueError, IndexError):
                continue
                
    return chapter_map

# ==============================================================================
# SECTION 2 : SCRAPING D'IMAGES (NOUVELLE LOGIQUE AMÉLIORÉE)
# ==============================================================================

def scrape_images_mangadex(chapter_url: str) -> list[str]:
    """Scrape images MangaDex via API /at-home/server."""
    # Cette logique est stable et reste inchangée
    chapter_uuid_match = re.search(r'chapter/([a-f0-9\-]{36})', chapter_url)
    if not chapter_uuid_match: return []
    chapter_uuid = chapter_uuid_match.group(1)
    try:
        api_url = f"https://api.mangadex.org/at-home/server/{chapter_uuid}"
        response = requests.get(api_url, timeout=10); response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur API /at-home/server MangaDex : {e}"); return []
    if data.get("result") != "ok" or not data.get("baseUrl") or not data.get("chapter"): return []
    base_url, chapter_hash = data["baseUrl"], data["chapter"]["hash"]
    image_filenames = data["chapter"]["data"]
    return [f"{base_url}/data/{chapter_hash}/{filename}" for filename in image_filenames]

def scrape_images_flamecomics(session, chapter_url: str) -> list[str]:
    """Scraper d'images spécialisé pour FlameComics."""
    # Cette logique est stable et reste inchangée
    try:
        session.get(chapter_url); time.sleep(3)
        last_height, stable = 0, 0
        while stable < 3:
            session.execute_script("window.scrollBy(0, 1000);"); time.sleep(0.5)
            new_height = session.execute_script("return document.body.scrollHeight")
            if new_height == last_height: stable += 1
            else: stable = 0
            last_height = new_height
        image_elements = session.find_elements(By.TAG_NAME, "img")
        image_urls = []
        for img in image_elements:
            try:
                if img.is_displayed():
                    width, height = img.size.get('width', 0), img.size.get('height', 0)
                    if width > 200 and height > width * 1.2:
                        src = img.get_attribute('src')
                        if src and src not in image_urls: image_urls.append(src)
            except: continue
        logging.info(f"✅ FlameComics images: {len(image_urls)} trouvées"); return image_urls
    except Exception as e:
        logging.error(f"❌ Erreur scraping images FlameComics: {e}"); return []
    
def scrape_images_madara_protected(session, chapter_url: str) -> list[str]:
    """
    Scraper Madara Protégé v3 : Cible une liste de sélecteurs, dont #readerarea.
    """
    try:
        session.get(chapter_url)
        time.sleep(10)

        # --- Gestion iFrame --- (inchangée)
        try:
            logging.info("Recherche d'iFrames publicitaires sur la page du chapitre...")
            iframes = session.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                for iframe in iframes:
                    try:
                        session.switch_to.frame(iframe)
                        # On cherche un bouton fermer générique à l'intérieur
                        close_button = session.find_element(By.CSS_SELECTOR, "*[aria-label*='Close'], *[aria-label*='close']")
                        if close_button:
                            close_button.click()
                            session.switch_to.default_content()
                            logging.info("Pop-up d'image fermé avec succès.")
                            time.sleep(2)
                            break
                    except Exception:
                        session.switch_to.default_content()
                        continue
        except Exception:
            logging.warning("Aucune iFrame n'a pu être gérée.")

        # --- RECHERCHE DU CONTENEUR D'IMAGES (LOGIQUE FINALE) ---
        logging.info("Recherche du conteneur d'images principal...")
        
        possible_selectors = ["div#readerarea", "div.reading-content"]
        reading_content = None
        for selector in possible_selectors:
            try:
                reading_content = session.find_element(By.CSS_SELECTOR, selector)
                if reading_content:
                    logging.info(f"Conteneur trouvé avec le sélecteur : '{selector}'")
                    break
            except:
                continue
        
        if not reading_content:
            logging.error("Aucun conteneur d'images valide (readerarea, reading-content) n'a été trouvé.")
            return []
        
        # --- Extraction des images ---
        images = reading_content.find_elements(By.TAG_NAME, "img")
        image_urls = []
        for img in images:
            src = img.get_attribute('src') or img.get_attribute('data-src')
            if src and src.startswith('http') and src not in image_urls:
                image_urls.append(src)
        
        logging.info(f"✅ Scraper Madara Protégé : {len(image_urls)} images trouvées")
        return image_urls

    except Exception as e:
        logging.error(f"❌ Erreur scraping images Madara Protégé: {e}", exc_info=True)
        return []

def scrape_images_madara_optimized(session, chapter_url: str) -> list[str]:
    """(NOUVEAU) Scraper spécialisé pour sites Madara. Plus rapide et précis."""
    session.get(chapter_url)
    try:
        # Attendre que le conteneur soit présent
        WebDriverWait(session, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "reading-content"))
        )
        # Extraire toutes les images dans ce conteneur
        reading_content = session.find_element(By.CLASS_NAME, "reading-content")
        images = reading_content.find_elements(By.TAG_NAME, "img")
        image_urls = []
        for img in images:
            src = img.get_attribute('src') or img.get_attribute('data-src')
            if src and src.startswith('http') and src not in image_urls:
                image_urls.append(src)
        logging.info(f"✅ Madara scraper : {len(image_urls)} images trouvées")
        return image_urls
    except Exception:
        logging.warning("Structure Madara non détectée, utilisation du scraper générique amélioré")
        return scrape_images_generic_improved(session, chapter_url)

def scrape_images_generic_improved(session, chapter_url: str, min_width: int = 400) -> list[str]:
    """(NOUVEAU) Scraper générique AMÉLIORÉ avec scroll intelligent et filtrage avancé."""
    session.get(chapter_url)
    try:
        WebDriverWait(session, 10).until(EC.presence_of_element_located((By.TAG_NAME, "img")))
    except:
        logging.warning(f"Timeout initial pour {chapter_url}"); return []
    time.sleep(2)
    last_image_count, stable_count, max_scrolls = 0, 0, 50
    for i in range(max_scrolls):
        session.execute_script("window.scrollBy(0, 800);"); time.sleep(0.7)
        current_count = len(session.find_elements(By.TAG_NAME, "img"))
        if current_count == last_image_count:
            stable_count += 1
            if stable_count >= 4:
                logging.info(f"Fin du scroll détectée après {i} itérations."); break
        else:
            stable_count = 0
        last_image_count = current_count
    
    image_candidates = []
    blacklisted_keywords = ['ad', 'banner', 'sponsor', 'thumbnail', 'avatar', 'logo']
    for img in session.find_elements(By.TAG_NAME, "img"):
        try:
            src, width, height = img.get_attribute('src'), img.size.get('width', 0), img.size.get('height', 0)
            if not src or not src.startswith('http'): continue
            if width < min_width or height < 200: continue
            if height / width < 1.2: continue # Filtre ratio vertical
            classes, alt = (img.get_attribute('class') or ""), (img.get_attribute('alt') or "")
            if any(k in classes.lower() for k in blacklisted_keywords) or any(k in alt.lower() for k in blacklisted_keywords): continue
            image_candidates.append({'src': src, 'position_y': img.location.get('y', 0)})
        except Exception: continue
    
    image_candidates.sort(key=lambda x: x['position_y'])
    seen_urls, final_urls = set(), []
    for img_data in image_candidates:
        if img_data['src'] not in seen_urls:
            seen_urls.add(img_data['src']); final_urls.append(img_data['src'])
    logging.info(f"✅ Scraping générique terminé : {len(final_urls)} images valides.")
    return final_urls

def detect_site_type(chapter_url: str) -> str:
    url = chapter_url.lower()
    if "mangadex" in url: return "mangadex"
    if "flamecomics" in url: return "flamecomics"
    if "raijin-scans" in url: return "raijin_scans"

    protected_madara_domains = ["arenascan.com"]
    if any(domain in url for domain in protected_madara_domains):
        return "madara_protected"

    madara_domains = ["reaperscans.com", "luminousscans.com", "asurascans.com", "manhuaus.com"]
    if any(domain in url for domain in madara_domains): return "madara"

    return "generic"


# (Dans scrapers.py, remplacez la fonction scrape_images_raijin_scans)
def scrape_images_raijin_scans(session, chapter_url: str) -> list[str]:
    """
    V5 - FINAL : Scraper robuste pour Raijin Scans (structure confirmée 2025).
    Gère le lazy-loading, les data-src, et les conteneurs 'div#ch-images'.
    """
    try:
        session.get(chapter_url)
        logging.info(f"📖 Ouverture du chapitre Raijin : {chapter_url}")

        # 1️⃣ Attente du conteneur principal
        WebDriverWait(session, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.reading-content div#ch-images"))
        )
        time.sleep(2)

        # 2️⃣ Scroll complet pour charger le lazy-loading
        logging.info("🌀 Scroll en cours pour charger toutes les images Raijin...")
        last_height, stable = 0, 0
        for i in range(40):  # limite de sécurité
            session.execute_script("window.scrollBy(0, 1000);")
            time.sleep(0.8)
            new_height = session.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                stable += 1
                if stable >= 4:
                    logging.info(f"✅ Fin du scroll détectée après {i+1} itérations.")
                    break
            else:
                stable = 0
            last_height = new_height

        # 3️⃣ Extraction du conteneur d'images
        container = session.find_element(By.CSS_SELECTOR, "div.reading-content div#ch-images")
        image_elements = container.find_elements(By.TAG_NAME, "img")

        # 4️⃣ Collecte des URLs
        image_urls = []
        for img in image_elements:
            try:
                src = img.get_attribute("data-src") or img.get_attribute("src")
                if src and src.startswith("http") and src not in image_urls:
                    image_urls.append(src)
            except Exception:
                continue

        logging.info(f"✅ Raijin Scans : {len(image_urls)} images extraites avec succès.")
        return image_urls

    except Exception as e:
        logging.error(f"❌ Erreur scraping Raijin Scans : {e}", exc_info=True)
        return []
    
def scrape_images_smart(session, chapter_url: str, min_width: int = 400) -> list[str]:
    try:
        site_type = detect_site_type(chapter_url)
        logging.info(f"🔍 Scraping images pour type : {site_type}")

        if site_type == "raijin_scans":
            return scrape_images_raijin_scans(session, chapter_url)
        elif site_type == "flamecomics":
            return scrape_images_flamecomics(session, chapter_url)
        elif site_type == "madara_protected":
            return scrape_images_madara_protected(session, chapter_url)
        elif site_type == "madara":
            return scrape_images_madara_optimized(session, chapter_url)
        else:
            return scrape_images_generic_improved(session, chapter_url, min_width)
    except Exception as e:
        logging.error(f"Erreur dans scrape_images_smart pour {chapter_url}: {e}", exc_info=True)
        return []

    


# ==============================================================================
# SECTION 3 : NOUVEAU MOTEUR DE DÉCOUPAGE "DE PRÉCISION" (NUMPY V3)
# ==============================================================================

def slice_panels_precision(image_bytes: bytes, 
                             min_gap_height: int = 15,    # Seuil bas pour détecter les gaps fins
                             min_panel_height: int = 150, # Hauteur minimale pour un panel valide
                             content_threshold: float = 0.05) -> List[Image.Image]: # Un panel doit avoir au moins 5% de contenu
    """
    ALGORITHME DE DÉCOUPAGE DE PRÉCISION (NUMPY V3)
    Objectif : Découper agressivement à chaque gap blanc OU noir significatif.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # On passe en niveaux de gris pour l'analyse
        gray_image = np.array(image.convert('L'))
        h, w = gray_image.shape

        # --- 1. Détection des lignes de gap (blanches ou noires) ---
        row_means = gray_image.mean(axis=1)
        row_stds = gray_image.std(axis=1)
        
        # Un gap a une couleur très uniforme (faible écart-type)
        is_uniform = row_stds < 15
        
        # Un gap est soit très clair, soit très foncé
        is_white_gap = row_means > 235
        is_black_gap = row_means < 20
        
        is_gap_line = is_uniform & (is_white_gap | is_black_gap)

        # --- 2. Trouver les points de coupe au centre des zones de gap ---
        cut_points = []
        in_gap = False
        gap_start = 0
        for i, is_gap in enumerate(is_gap_line):
            if is_gap and not in_gap:
                gap_start = i
                in_gap = True
            elif not is_gap and in_gap:
                gap_height = i - gap_start
                # Si le gap est assez haut, on ajoute un point de coupe au milieu
                if gap_height >= min_gap_height:
                    cut_points.append(gap_start + gap_height // 2)
                in_gap = False

        # --- 3. Découper et filtrer les panels ---
        panels = []
        last_cut = 0
        all_cuts = sorted(list(set([0] + cut_points + [h])))

        for i in range(len(all_cuts) - 1):
            start_y, end_y = all_cuts[i], all_cuts[i+1]
            panel_height = end_y - start_y

            # Filtre 1 : Le panel doit avoir une hauteur minimale
            if panel_height < min_panel_height:
                continue

            panel_img = image.crop((0, start_y, w, end_y))
            
            # Filtre 2 : Le panel doit avoir un minimum de "contenu" (pixels non-blancs)
            panel_gray = np.array(panel_img.convert('L'))
            content_ratio = np.sum(panel_gray < 250) / panel_gray.size
            if content_ratio < content_threshold:
                continue
            
            panels.append(panel_img)

        logging.info(f"Découpage de précision : {len(panels)} panels extraits.")
        
        # Si aucun découpage n'a fonctionné, retourner l'image entière
        if not panels:
            return [trim_whitespace_smart(image)]

        return [trim_whitespace_smart(p) for p in panels]

    except Exception as e:
        logging.error(f"Erreur dans slice_panels_precision: {e}", exc_info=True)
        # En cas d'erreur, retourner l'image entière pour ne pas perdre de données
        return [Image.open(io.BytesIO(image_bytes))]

# On remplace l'appel dans `process_image_smart` pour utiliser notre nouvel algorithme
def process_image_smart(image_bytes: bytes) -> List[Image.Image]:
    """Point d'entrée qui utilise maintenant le découpeur de précision V3."""
    # On supprime la logique "should_slice" car on veut toujours essayer de découper
    logging.info("Activation du moteur de découpage de précision (Numpy V3)...")
    return slice_panels_precision(image_bytes)


# trim_whitespace_smart reste utile et inchangé
def trim_whitespace_smart(image: Image.Image, threshold: int = 240) -> Image.Image:
    """Rogne les bords blancs en préservant les bordures décoratives."""
    img_array = np.array(image.convert('L'))
    has_black_border = (img_array[0, :].mean() < 50) or (img_array[-1, :].mean() < 50)
    if has_black_border:
        return image
    non_white_rows = np.where(np.any(img_array < threshold, axis=1))[0]
    non_white_cols = np.where(np.any(img_array < threshold, axis=0))[0]
    if non_white_rows.size > 0 and non_white_cols.size > 0:
        top = max(0, non_white_rows[0] - 5)
        bottom = min(image.height - 1, non_white_rows[-1] + 5)
        left = max(0, non_white_cols[0] - 5)
        right = min(image.width - 1, non_white_cols[-1] + 5)
        return image.crop((left, top, right + 1, bottom + 1))
    return image