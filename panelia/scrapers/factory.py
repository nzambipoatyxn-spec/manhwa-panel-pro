# scrapers.py - Version 2025 FULLY FIXED
# ENTIEREMENT réadapté à la nouvelle logique WebSession
# 100% compatible : driver parallèle, UC, app.py, scraper_engine, core.py
# UNIQUEMENT driver = get_driver(session) utilisé pour Selenium

import re
import time
import json
import io
from typing import List
from urllib.parse import urljoin

import httpx
import cv2
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
from loguru import logger
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

###############################################################
# 🔥 0. DRIVER ACCESS - LE POINT CENTRAL
###############################################################
def get_driver(session):
    """
    Retourne le webdriver interne depuis WebSession.
    C'est LA fonction qui empêche toute erreur "session.find_element".
    Toute interaction Selenium DOIT passer par ce driver.
    """
    return session.driver

###############################################################
# 🔥 1. MOTEUR DECOUVERTE CHAPITRES (stable)
###############################################################
# --- A. MADARA ---
def discover_chapters_madara_theme(session_or_url, series_url: str = None) -> dict[float, str]:
    from panelia.core.driver import WebSession
    session, is_temp = None, False
    try:
        if isinstance(session_or_url, str):
            # Si c'est du HTML brut (détecté par la présence de balises)
            if "<html" in session_or_url.lower() or "<div" in session_or_url.lower():
                soup = BeautifulSoup(session_or_url, "html.parser")
                # On ne logue pas le HTML, juste qu'on utilise du HTML fourni
                logger.info(f"[MadaraV7] Découverte via HTML fourni pour : {series_url or 'URL inconnue'}")
                return _parse_madara_chapters(soup, series_url)
            
            # Sinon c'est une URL
            session = WebSession(headless=True)
            series_url = session_or_url
            is_temp = True
        else:
            session = session_or_url
        
        driver = get_driver(session)
        logger.info(f"[MadaraV7] Découverte : {series_url}")
        session.get(series_url)
        time.sleep(2) # Réduit de 4 à 2 pour plus de fluidité

        # Nettoyage onglets
        if len(driver.window_handles) > 1:
            base = driver.current_window_handle
            for h in driver.window_handles:
                if h != base:
                    driver.switch_to.window(h)
                    driver.close()
            driver.switch_to.window(base)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        return _parse_madara_chapters(soup, series_url)
    finally:
        if is_temp and session:
            session.quit()

def _parse_madara_chapters(soup: BeautifulSoup, series_url: str) -> dict[float, str]:
    container = (soup.find('div', id='chapterlist')
                or soup.find('ul', class_='main')
                or soup.find('div', class_='listing-chapters_wrap')
                or soup.find('ul', class_='scroll-sm'))
    if not container: return {}

    chap_map = {}
    for li in container.find_all('li'):
        a = li.find('a')
        if not a: continue
        href = a.get('href')
        txt = li.get_text(strip=True)
        m = re.search(r'(?:Chapter|Chapitre|Ch\.?|Ep)\s*([\d\.]+)', txt, re.I)
        if m and href:
            num = float(m.group(1))
            chap_map[num] = urljoin(series_url, href)
    return chap_map

# --- B. ASURA ---
def discover_chapters_asuracomic(source, series_url: str) -> dict[float, str]:
    from panelia.core.driver import WebSession
    session, is_temp = None, False
    try:
        if isinstance(source, str):
            # Si c'est du HTML brut
            if "<html" in source.lower() or "<div" in source.lower():
                logger.info(f"[Asura] Découverte via HTML fourni pour : {series_url}")
                return _parse_asura_chapters(source, series_url)
            
            # Sinon c'est une URL
            session = WebSession(headless=True)
            series_url = source
            is_temp = True
        else:
            session = source
            
        driver = get_driver(session)
        logger.info(f"[Asura] Découverte : {series_url}")
        session.get(series_url)
        time.sleep(2)
        
        last, stable = 0, 0
        while stable < 4:
            driver.execute_script("window.scrollBy(0,1000);")
            time.sleep(0.7)
            h = driver.execute_script("return document.body.scrollHeight")
            if h == last: stable += 1
            else: stable = 0
            last = h
        
        return _parse_asura_chapters(driver.page_source, series_url)
    except Exception as e:
        logger.warning(f"[Asura] Erreur discovery : {e}")
        return {}
    finally:
        if is_temp and session:
            session.quit()

def _parse_asura_chapters(html: str, series_url: str) -> dict[float, str]:
    soup = BeautifulSoup(html, "html.parser")
    mp = {}
    for a in soup.find_all('a', href=True):
        if '/chapter/' not in a['href']: continue
        text = a.get_text(strip=True)
        # Regex plus robuste pour Asura
        m = re.search(r'(?:Chapter|Ch\.?|Ep)\s*([\d\.]+)', text, re.I)
        if m:
            num = float(m.group(1))
            mp[num] = urljoin(series_url, a['href'])
    return mp

# --- C. MANGADEX --- (inchangé)
def discover_chapters_mangadex(series_url: str) -> dict[float, str]:
    chap = {}
    mid = re.search(r'title/([a-f0-9\-]{36})', series_url)
    if not mid: return {}
    uid = mid.group(1)
    api = f"https://api.mangadex.org/manga/{uid}/feed"
    params = {"translatedLanguage[]": "en", "order[chapter]": "desc", "limit": 500}
    off, total = 0, None
    # On tente avec HTTP/2, sinon fallback vers HTTP/1.1 (évite ImportError: No module named 'h2')
    try:
        with httpx.Client(http2=True, timeout=15) as client:
            while total is None or off < total:
                params['offset'] = off
                r = client.get(api, params=params)
                if r.status_code != 200: break
                d = r.json()
                if d.get("result") != "ok": break
                total = d.get("total", 0) if total is None else total
                for c in d.get('data', []):
                    attrs = c.get('attributes', {})
                    ch = attrs.get('chapter')
                    cid_val = c.get('id')
                    if ch and cid_val:
                        try: chap[float(ch)] = f"https://mangadex.org/chapter/{cid_val}"
                        except: pass
                off += len(d.get('data', []))
    except (ImportError, httpx.UnsupportedProtocol):
        logger.info("HTTP/2 non supporté (h2 manquant). Rebasculement vers HTTP/1.1...")
        with httpx.Client(http2=False, timeout=15) as client:
            while total is None or off < total:
                params['offset'] = off
                r = client.get(api, params=params)
                if r.status_code != 200: break
                d = r.json()
                if d.get("result") != "ok": break
                total = d.get("total", 0) if total is None else total
                for c in d.get('data', []):
                    attrs = c.get('attributes', {})
                    ch = attrs.get('chapter')
                    cid_val = c.get('id')
                    if ch and cid_val:
                        try: chap[float(ch)] = f"https://mangadex.org/chapter/{cid_val}"
                        except: pass
                    off += len(d.get('data', []))
    except Exception as e:
        logger.warning(f"Erreur API MangaDex : {e}")
    return chap

# --- D. FLAME ---
def discover_chapters_flamecomics(session, series_url):
    session.get(series_url); time.sleep(3)
    driver = get_driver(session)
    last, stable = 0,0
    while stable < 3:
        driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
        time.sleep(1.5)
        h = driver.execute_script("return document.body.scrollHeight")
        (stable := stable+1) if h == last else (stable := 0)
        last = h
    soup = BeautifulSoup(driver.page_source, "html.parser")
    mp = {}
    for el in soup.find_all('a', href=True):
        href = el['href']; txt = el.text.strip()
        m = re.search(r'(?:Chapter|Ch)\s*(\d+(?:\.\d+)?)', txt, re.I)
        if m:
            mp[float(m.group(1))] = href
    return mp

def discover_chapters_raijin_scans(session_or_html, series_url: str = None) -> dict[float, str]:
    """
    Détecteur Raijin Scans compatible WebSession + HTML brut.
    Structure simple et agressive car Raijin change souvent son DOM.
    """
    from panelia.core.driver import WebSession
    html = None

    # Si on reçoit directement du HTML → pas besoin Selenium
    if isinstance(session_or_html, str):
        html = session_or_html

    else:
        # Sinon on utilise la session Selenium
        session = session_or_html
        session.get(series_url)
        time.sleep(2)
        driver = get_driver(session)
        html = driver.page_source

    soup = BeautifulSoup(html, "html.parser")
    chapters = {}

    # Raijin a des URLs du type /chapter-xx ou /chapitre-xx
    for a in soup.find_all('a', href=True):
        href = a['href']
        txt = a.get_text(strip=True)

        # Doit contenir un mot-clé de chapitre
        if not any(k in href.lower() for k in ["chapter", "chap", "chapitre", "ep"]):
            continue

        # Extraction du numéro
        m = re.search(r"(\d+(?:\.\d+)?)", txt)
        if not m:
            continue

        num = float(m.group(1))
        chapters[num] = urljoin(series_url, href)

    return chapters

###############################################################
# 🔥 2. SCRAPING IMAGES - Nouvelle logique UNIFIÉE
###############################################################
# Détection du site
def detect_site_type(url: str) -> str:
    u = url.lower()
    if "mangadex" in u: return "mangadex"
    if "flamecomics" in u: return "flame"
    if "raijin-scans" in u: return "raijin"
    if "arenascan" in u: return "madara_protected"
    if any(d in u for d in ["manga-scantrad", "mangas-origines", "asurascans", "reaperscans", "luminousscans"]):
        return "madara"
    return "generic"

# --- A. MangaDex (API) ---
def scrape_images_mangadex(chapter_url):
    cid = re.search(r'chapter/([a-f0-9\-]{36})', chapter_url)
    if not cid: return []
    api = f"https://api.mangadex.org/at-home/server/{cid.group(1)}"
    # On tente avec HTTP/2, sinon fallback vers HTTP/1.1
    try:
        with httpx.Client(http2=True, timeout=15) as client:
            r = client.get(api)
            if r.status_code != 200: return []
            d = r.json()
            if d.get('result') != 'ok': return []
            base = d['baseUrl']; h = d['chapter']['hash']
            return [f"{base}/data/{h}/{fn}" for fn in d['chapter']['data']]
    except (ImportError, httpx.UnsupportedProtocol):
        with httpx.Client(http2=False, timeout=15) as client:
            r = client.get(api)
            if r.status_code != 200: return []
            d = r.json()
            if d.get('result') != 'ok': return []
            base = d['baseUrl']; h = d['chapter']['hash']
            return [f"{base}/data/{h}/{fn}" for fn in d['chapter']['data']]
    except Exception as e:
        logger.warning(f"Erreur scrape MangaDex images : {e}")
        return []

# --- B. Madara optimisé ---
def scrape_images_madara(session, url, min_width=400):
    session.get(url); time.sleep(2)
    driver = get_driver(session)
    try:
        WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR,".reading-content img")))
        root = driver.find_elements(By.CSS_SELECTOR, ".reading-content img")
        out = []
        for img in root:
            src = (img.get_attribute('data-src') or 
                   img.get_attribute('data-lazy-src') or 
                   img.get_attribute('data-srcset') or 
                   img.get_attribute('src'))
            if not src: continue
            if src not in out: out.append(src)
        logger.info(f"[Madara] {len(out)} images.")
        return out
    except:
        return scrape_images_generic(session,url,min_width)

# --- C. Raijin ---
def scrape_images_raijin(session,url):
    session.get(url); time.sleep(2)
    driver = get_driver(session)
    WebDriverWait(driver,20).until(EC.presence_of_element_located((By.CSS_SELECTOR,"#ch-images img")))
    imgs = driver.find_elements(By.CSS_SELECTOR,"#ch-images img")
    out = []
    for i in imgs:
        s = i.get_attribute('data-src') or i.get_attribute('src')
        if s and s not in out: out.append(s)
    return out

# --- D. FLAME ---
def scrape_images_flame(session,url):
    session.get(url); time.sleep(3)
    driver = get_driver(session)
    for _ in range(40):
        driver.execute_script("window.scrollBy(0,1000);")
        time.sleep(0.4)
    imgs = driver.find_elements(By.TAG_NAME, "img")
    out = []
    for i in imgs:
        try:
            w,h = i.size['width'], i.size['height']
            if w>200 and h>w*1.2:
                s=i.get_attribute('src');
                if s: out.append(s)
        except: continue
    return out

# --- E. GENERIC ---
def scrape_images_generic(session,url,min_width=400):
    session.get(url); time.sleep(2)
    driver = get_driver(session)
    try:
        WebDriverWait(driver,10).until(EC.presence_of_element_located((By.TAG_NAME,"img")))
    except:
        return []
    imgs = driver.find_elements(By.TAG_NAME,"img")
    out=[]
    for i in imgs:
        try:
            s=i.get_attribute('src')
            if not s or not s.startswith('http'): continue
            w=i.size['width']; h=i.size['height']
            if w<min_width or h<250: continue
            if h/w < 1.1: continue
            out.append(s)
        except: continue
    return out

# --- F. ROUTEUR INTELLIGENT ---
def scrape_images_smart(session,url,min_width=400):
    t = detect_site_type(url)
    logger.info(f"[ScraperSmart] Type détecté: {t}")
    if t=="mangadex": return scrape_images_mangadex(url)
    if t=="flame": return scrape_images_flame(session,url)
    if t=="raijin": return scrape_images_raijin(session,url)
    if t=="madara": return scrape_images_madara(session,url,min_width)
    return scrape_images_generic(session,url,min_width)

###############################################################
# 🔥 3. TRAITEMENT IMAGES (Numpy V3 – déjà présent)
###############################################################
def slice_panels_precision(image_bytes: bytes, min_gap_height: int = 15, min_panel_height: int = 150, content_threshold: float = 0.05) -> List[Image.Image]:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        gray = np.array(img.convert('L'))
        h,w = gray.shape
        row_means = gray.mean(axis=1)
        row_stds = gray.std(axis=1)
        uniform = row_stds < 15
        white = row_means > 235
        black = row_means < 20
        is_gap = uniform & (white | black)
        cuts=[]; in_gap=False; gs=0
        for i,g in enumerate(is_gap):
            if g and not in_gap:
                gs=i; in_gap=True
            elif not g and in_gap:
                gh=i-gs
                if gh>=min_gap_height: cuts.append(gs+gh//2)
                in_gap=False
        all_cuts = [0]+cuts+[h]
        panels=[]
        for i in range(len(all_cuts)-1):
            sy,ey=all_cuts[i],all_cuts[i+1]
            ph=ey-sy
            if ph<min_panel_height: continue
            p = img.crop((0,sy,w,ey))
            
            # --- AUTO-TRIM ---
            # On nettoie chaque planche après découpe
            p = trim_borders_smart(p)
            
            g2=np.array(p.convert('L'))
            if np.sum(g2<250)/g2.size < content_threshold: continue
            panels.append(p)
        return panels if panels else [img]
    except:
        return [Image.open(io.BytesIO(image_bytes))]

###############################################################
# 🔥 4. PROCESS IMAGE SMART
###############################################################

# On remplace l'appel dans `process_image_smart` pour utiliser notre nouvel algorithme
def process_image_smart(image_bytes: bytes) -> List[Image.Image]:
    """
    Doit retourner une LISTE d’images PIL.
    Exemple :
        return [img] ou [img1, img2, img3]
    """
    # On supprime la logique "should_slice" car on veut toujours essayer de découper
    logger.info("Activation du moteur de découpage de précision (Numpy V3)...")
    return slice_panels_precision(image_bytes)


def trim_borders_smart(image: Image.Image, padding: int = 2) -> Image.Image:
    """
    Rogne intelligemment les bords blancs OU noirs autour d'une image/planche.
    Détecte automatiquement la couleur dominante des bords.
    """
    try:
        # Conversion en noir et blanc pour analyse
        img_array = np.array(image.convert('L'))
        h, w = img_array.shape

        # 1. Détecter si le fond est plutôt noir ou blanc
        # On regarde la moyenne des pixels sur les 4 bords
        edge_pixels = np.concatenate([
            img_array[0, :],          # Haut
            img_array[-1, :],         # Bas
            img_array[:, 0],          # Gauche
            img_array[:, -1]          # Droite
        ])
        edge_mean = edge_pixels.mean()
        
        # Seuil de décision : si > 127, on considère que le fond est clair (blanc)
        is_white_bg = edge_mean > 127
        
        if is_white_bg:
            # Pour un fond blanc, on cherche tout ce qui n'est PAS blanc (pixel < 245)
            mask = img_array < 245
        else:
            # Pour un fond noir, on cherche tout ce qui n'est PAS noir (pixel > 30)
            mask = img_array > 15

        # 2. Trouver les limites du contenu
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            return image # Rien trouvé, on garde l'original

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]

        # 3. Appliquer un padding léger pour ne pas "étouffer" le dessin
        left = max(0, cmin - padding)
        top = max(0, rmin - padding)
        right = min(w, cmax + padding + 1)
        bottom = min(h, rmax + padding + 1)

        return image.crop((left, top, right, bottom))
    except Exception as e:
        logger.warning(f"Erreur lors du recadrage : {e}")
        return image
