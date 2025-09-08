# app.py - v4.3 - Le Scraper d'Images Intelligent
# Intègre un manager pour choisir la méthode de scraping d'images la plus efficace (API ou Selenium).

# --- IMPORTS COMPLETS ---
import streamlit as st
import requests
import time
import os
import io
import re
import zipfile
from pathlib import Path
from urllib.parse import urljoin
import numpy as np
from PIL import Image
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import base64
import logging
from scrapers import (
    discover_chapters_asuracomic, discover_chapters_resetscans, 
    discover_chapters_ravenscans, discover_chapters_mangadex,
    scrape_images_mangadex  # <-- Nouvel import
)

# --- Configuration du Logging ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Fonctions "Cerveau" de l'Application ---

def normalize_url(src, page_url):
    """Gère toutes les URLs, même relatives, pour les rendre absolues."""
    if not src:
        return None
    return urljoin(page_url, src.strip())

def trim_whitespace(image: Image.Image, threshold=245) -> Image.Image:
    """Rogne les bords blancs (ou quasi-blancs) d'une image."""
    image_array = np.array(image.convert('L'))
    non_white_rows = np.where(np.any(image_array < threshold, axis=1))[0]
    if non_white_rows.size > 0:
        top, bottom = non_white_rows[0], non_white_rows[-1]
        return image.crop((0, top, image.width, bottom + 1))
    return image

def slice_and_trim_images(image_bytes):
    """Découpe une image en se basant sur les 'gaps' et rogne le blanc inutile."""
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('L')
        image_array, (W, H) = np.array(image), image.size
        row_means, row_std_devs = image_array.mean(axis=1), image_array.std(axis=1)
        is_gap_line = ((row_means >= 245) | (row_means <= 10)) & (row_std_devs < 10)
        gap_zones, start = [], -1
        for i, is_gap in enumerate(is_gap_line):
            if is_gap and start == -1: start = i
            elif not is_gap and start != -1:
                if i - start >= 40: gap_zones.append(start + (i - start) // 2)
                start = -1
        if not gap_zones: return [trim_whitespace(Image.open(io.BytesIO(image_bytes)))]
        panels, last_cut = [], 0
        for cut_y in gap_zones:
            panel = Image.open(io.BytesIO(image_bytes)).crop((0, last_cut, W, cut_y))
            if panel.height >= 200: panels.append(trim_whitespace(panel))
            last_cut = cut_y
        final_panel = Image.open(io.BytesIO(image_bytes)).crop((0, last_cut, W, H))
        if final_panel.height >= 200: panels.append(trim_whitespace(final_panel))
        return panels
    except Exception: return []

@st.cache_data(ttl=3600)
def discover_chapters(series_url: str) -> dict[float, str]:
    """
    Fonction "Manager" qui choisit le bon scraper en fonction de l'URL de la série.
    """
    logging.info(f"Découverte des chapitres pour l'URL : {series_url}")
    
    SCRAPER_STRATEGIES = {
        "mangadex.org": (discover_chapters_mangadex, False),
        "asuracomic.net": (discover_chapters_asuracomic, True),
        "reset-scans.org": (discover_chapters_resetscans, True),
        "ravenscans.com": (discover_chapters_ravenscans, True),
    }

    def selenium_wrapper(html, url):
        chapter_links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>.*?Chapter\s*([\d\.]+).*?</a>', html, re.IGNORECASE)
        return {float(num): normalize_url(link, url) for link, num in chapter_links if num.replace('.', '', 1).isdigit()}
    
    scraper_function, needs_selenium = (selenium_wrapper, True)
    
    for domain, (func, needs_sel) in SCRAPER_STRATEGIES.items():
        if domain in series_url:
            scraper_function = func
            needs_selenium = needs_sel
            logging.info(f"Stratégie spécialisée trouvée pour {domain}.")
            break
    
    if not needs_selenium:
        logging.info("Exécution du scraper API (sans Selenium).")
        return scraper_function(series_url)

    driver = None
    try:
        logging.info("Lancement de Selenium pour obtenir le HTML de la page.")
        options = uc.ChromeOptions(); options.add_argument("--headless"); options.add_argument("--no-sandbox")
        driver = uc.Chrome(options=options)
        driver.get(series_url)
        time.sleep(5)
        page_html = driver.page_source
        
        return scraper_function(page_html, series_url)
        
    except Exception as e:
        st.error(f"Impossible de découvrir les chapitres : {e}")
        logging.error(f"Échec de la découverte pour {series_url}", exc_info=True)
        return {}
    finally:
        if driver:
            driver.quit()

# --- NOUVELLE FONCTION MANAGER POUR LES IMAGES ---
def scrape_images(chapter_url: str, min_width: int) -> list[str]:
    """
    Fonction "Manager" qui choisit le bon scraper d'IMAGES en fonction de l'URL du chapitre.
    """
    if "mangadex.org" in chapter_url:
        logging.info("Utilisation du scraper d'images spécialisé pour MangaDex (API).")
        return scrape_images_mangadex(chapter_url)
    else:
        # Pour tous les autres sites, on utilise notre scraper générique Selenium.
        logging.info("Utilisation du scraper d'images générique (Selenium).")
        return scrape_images_universally(chapter_url, min_width=min_width)
# --- FIN DE LA NOUVELLE FONCTION ---

def scrape_images_universally(url, min_width=400):
    """Scrape les images de manière automatique et robuste avec Selenium."""
    driver = None
    try:
        options = uc.ChromeOptions(); options.add_argument("--headless"); options.add_argument("--no-sandbox")
        driver = uc.Chrome(options=options)
        driver.get(url); last_h, stable = 0, 0
        for _ in range(80):
            driver.execute_script("window.scrollBy(0, 1000);"); time.sleep(0.4)
            h = driver.execute_script("return document.documentElement.scrollHeight")
            if h == last_h: stable += 1
            if stable >= 3: break; last_h = h
        
        script = f"""
            const imageUrls = new Map();
            document.querySelectorAll('.protected-image-data[data-src]').forEach(div => {{ try {{ const decodedSrc = atob(div.getAttribute('data-src')); imageUrls.set(decodedSrc, 9999 + imageUrls.size); }} catch (e) {{}} }});
            document.querySelectorAll('img').forEach(img => {{ const isVisible = !!(img.offsetWidth || img.offsetHeight || img.getClientRects().length); if (img.src && img.complete && img.naturalHeight > 0 && isVisible) {{ const width = img.clientWidth; const height = img.clientHeight; if (width > {min_width} && height > width * 1.5) {{ if (!imageUrls.has(img.src)) {{ imageUrls.set(img.src, img.getBoundingClientRect().top + window.scrollY); }} }} }} }});
            const sortedImages = Array.from(imageUrls.entries()).sort((a, b) => a[1] - b[1]);
            return sortedImages.map(entry => entry[0]);
        """
        found_urls = driver.execute_script(script)
        return [normalize_url(src, url) for src in found_urls]
    except Exception: return []
    finally:
        if 'driver' in locals() and driver: driver.quit()

def scrape_images_interactively(driver, url):
    """Utilise un driver existant pour une interaction manuelle et le scraping."""
    driver.get(url)
    placeholder = st.empty()
    with placeholder.form("captcha_form"):
        st.warning("Mode interactif : une fenêtre Chrome s'est ouverte.")
        st.info("Interagissez avec la page (résolvez le captcha, bougez la souris) jusqu'à ce que les images apparaissent, PUIS cliquez sur le bouton ci-dessous.")
        if not st.form_submit_button("✅ J'ai terminé, continuer le Scraping"):
            st.stop()

    placeholder.empty()
    st.info("Reprise du contrôle... Défilement de la page pour charger toutes les images.")
    for _ in range(40):
        driver.execute_script("window.scrollBy(0, 1000);"); time.sleep(0.2)
    
    image_urls = []
    all_img_tags = driver.find_elements(By.TAG_NAME, 'img')
    for img_tag in all_img_tags:
        if img_tag.is_displayed() and img_tag.size.get('height', 0) > img_tag.size.get('width', 0) * 1.5:
            src = img_tag.get_attribute('src')
            if src:
                image_urls.append(normalize_url(src, url))
    
    return list(dict.fromkeys(image_urls))

def process_and_save(image_urls, manhwa_name, chapter_num, quality=92, timeout=30):
    """Factorisation de la logique de traitement et de sauvegarde, avec logging."""
    safe_manhwa_name = re.sub(r'[^\w\-_]', '', manhwa_name)
    safe_chapter_num = str(chapter_num).replace('.', '_')
    output_dir = Path("output") / safe_manhwa_name / safe_chapter_num
    output_dir.mkdir(parents=True, exist_ok=True)

    total_panels_saved = 0
    logging.info(f"Starting processing for {manhwa_name} Ch. {chapter_num}. Found {len(image_urls)} images.")

    for i, img_url in enumerate(image_urls):
        try:
            image_bytes = requests.get(img_url, timeout=timeout).content
            panel_images = slice_and_trim_images(image_bytes)
            for panel_img in panel_images:
                filename = f"planche_{total_panels_saved + 1:03d}.jpg"
                panel_path = output_dir / filename
                panel_img.convert('RGB').save(panel_path, "JPEG", quality=quality, optimize=True)
                total_panels_saved += 1
        except Exception as e:
            st.warning(f"Erreur sur une image du chapitre {chapter_num}. Voir app.log pour les détails.")
            logging.error(
                f"Failed to process image {i+1}/{len(image_urls)} ({img_url}) for {manhwa_name} Ch. {chapter_num}.",
                exc_info=True
            )

    logging.info(f"Finished processing for {manhwa_name} Ch. {chapter_num}. Saved {total_panels_saved} panels.")
    return total_panels_saved

def create_zip_in_memory(folder_path):
    """Crée une archive ZIP en mémoire à partir d'un dossier."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
        p = Path(folder_path)
        for file in p.glob('**/*.jpg'):
            relative_path = file.relative_to(p.parent)
            zip_file.write(file, arcname=relative_path)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# --- Fonctions Utilitaires pour l'UI ---
def create_status_indicator(status_type, message):
    icons = {'success': '✅', 'warning': '⚠️', 'info': 'ℹ️', 'error': '❌'}
    return f'<div class="status-indicator status-{status_type}">{icons.get(status_type, "")} {message}</div>'

def create_feature_card(title, description, icon="🔧"):
    return f'<div class="feature-card"><h3>{icon} {title}</h3><p>{description}</p></div>'

# --- Configuration de la Page et CSS ---
st.set_page_config(
    page_title="Manhwa Panel Pro", page_icon="📚", layout="wide", initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/le-genie-civil',
        'Report a bug': "https://github.com/le-genie-civil/Manhwa-Panel-Pro/issues",
        'About': "# Manhwa Panel Pro\nUne application moderne pour télécharger vos manhwa préférés!"
    }
)

st.markdown("""<style>
    :root {
        --primary-color: #FF4B4B; --secondary-color: #00C851; --accent-color: #33A1FF;
        --warning-color: #FF8C00; --success-color: #28A745; --border-radius: 12px;
        --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); --transition: all 0.3s ease;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem 1.5rem;
        border-radius: var(--border-radius); margin-bottom: 2rem; color: white;
        text-align: center; box-shadow: var(--box-shadow);
    }
    .main-header h1 { font-size: 3rem; margin: 0; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
    .main-header p { font-size: 1.2rem; margin: 0.5rem 0 0 0; opacity: 0.9; }
    .feature-card {
        background: rgba(255, 255, 255, 0.05); border-radius: var(--border-radius); padding: 1.5rem;
        margin: 1rem 0; box-shadow: var(--box-shadow); transition: var(--transition);
        border-left: 4px solid var(--accent-color); color: #FFFFFF;
    }
    .feature-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15); }
    .status-indicator {
        display: inline-flex; align-items: center; padding: 0.5rem 1rem; border-radius: 20px;
        font-weight: 500; margin: 0.5rem 0;
    }
    .status-success { background: #d4edda; color: #155724; } .status-warning { background: #fff3cd; color: #856404; }
    .status-info { background: #d1ecf1; color: #0c5460; } .status-error { background: #f8d7da; color: #721c24; }
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color), #FF6B6B); color: white; border: none;
        border-radius: var(--border-radius); padding: 0.75rem 2rem; font-weight: 600;
        transition: var(--transition); box-shadow: var(--box-shadow);
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 12px rgba(255, 75, 75, 0.3); }
    .stProgress > div > div > div { background: linear-gradient(90deg, var(--accent-color), var(--secondary-color)); border-radius: 10px; }
    @media (max-width: 768px) { .main-header h1 { font-size: 2rem; } .main-header p { font-size: 1rem; } }
</style>""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""<div class="main-header">
    <h1>📚 Manhwa Panel Pro</h1>
    <p>Votre solution moderne pour télécharger et organiser vos manhwa préférés</p>
</div>""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🎛️ Panneau de Contrôle")
    if 'session_stats' not in st.session_state:
        st.session_state.session_stats = {'chapters_processed': 0, 'images_downloaded': 0}
    
    stats = st.session_state.session_stats
    col1, col2 = st.columns(2)
    col1.metric("Chapitres Traités", stats['chapters_processed'])
    col2.metric("Planches Sauvegardées", stats['images_downloaded'])
    st.markdown("---")
    
    st.markdown("### 🔄 Mode de Travail")
    app_mode = st.selectbox(
        "Choisissez votre méthode :", ["Chapitre Unique", "Traitement par Lots"],
        help="Chapitre Unique: Pour traiter rapidement un seul chapitre\nTraitement par Lots: Pour télécharger plusieurs chapitres d'une série"
    )
    st.markdown("---")
    
    with st.expander("⚙️ Paramètres Avancés"):
        quality_setting = st.slider(
            "Qualité JPEG", 70, 100, 
            st.secrets.app_settings.default_jpeg_quality, 
            help="Plus élevé = meilleure qualité, fichiers plus lourds"
        )
        min_image_width = st.number_input(
            "Largeur minimale des images (px)", 200, 800, 
            st.secrets.app_settings.default_min_image_width
        )
        timeout_setting = st.number_input(
            "Timeout des requêtes (sec)", 10, 60, 
            st.secrets.app_settings.default_timeout
        )

# --- Corps Principal de l'Application ---
if app_mode == "Chapitre Unique":
    st.markdown("## ⚡ Mode Chapitre Unique")

    if 'scraping_job' not in st.session_state:
        # ... (Interface du formulaire - inchangée)
        col1, col2 = st.columns(2)
        col1.markdown(create_feature_card("Téléchargement Rapide", "Traitez un chapitre en quelques clics", "🚀"), unsafe_allow_html=True)
        col2.markdown(create_feature_card("Mode Interactif", "Contournez les protections CAPTCHA", "🛡️"), unsafe_allow_html=True)
        st.markdown("---")
        with st.container():
            st.markdown("### 📝 Informations du Chapitre")
            col1, col2 = st.columns(2)
            manhwa_name_single = col1.text_input("📖 Nom de la Série", placeholder="Ex: Solo Leveling", key="single_name")
            chapter_num_single = col2.text_input("📄 Numéro du Chapitre", placeholder="Ex: 110 ou 110.5", key="single_num")
            chapter_url_single = st.text_input("🔗 URL du Chapitre", placeholder="https://example.com/series/chapter-110", key="single_url")
            with st.expander("🔧 Options"):
                interactive_mode_single = st.checkbox("🤖 Activer le Mode Interactif", help="Ouvre une fenêtre Chrome pour votre intervention.", key="single_interactive")
                auto_detect = st.checkbox("🎯 Détection Automatique", value=True, help="Tente de remplir le nom et numéro depuis l'URL.", key="single_auto")
            run_single_button = st.button("🚀 Lancer le Traitement", type="primary", use_container_width=True, disabled=not chapter_url_single)
            if run_single_button and chapter_url_single:
                final_manhwa_name, final_chapter_num = manhwa_name_single, chapter_num_single
                if auto_detect:
                    try:
                        url_parts = chapter_url_single.strip('/').split('/')
                        if not final_manhwa_name: final_manhwa_name = url_parts[-2]
                        if not final_chapter_num:
                            match = re.search(r'(\d+(\.\d+)?)', url_parts[-1])
                            if match: final_chapter_num = match.group(1)
                    except IndexError: pass
                final_manhwa_name = final_manhwa_name or "Unknown_Series"
                final_chapter_num = final_chapter_num or "Unknown_Chapter"
                st.session_state['scraping_job'] = {
                    "name": final_manhwa_name, "num": final_chapter_num,
                    "url": chapter_url_single, "interactive": interactive_mode_single
                }
                st.rerun()

    if 'scraping_job' in st.session_state:
        job = st.session_state['scraping_job']
        driver_instance = None
        with st.status(f"Traitement de **{job['name']} - Chapitre {job['num']}**", expanded=True) as status:
            try:
                st.write("Étape 1/4 : Initialisation...")
                image_urls = []
                
                if job['interactive']:
                    st.write("Étape 2/4 : En attente de l'interaction utilisateur...")
                    if 'driver' not in st.session_state:
                        options = uc.ChromeOptions(); driver_instance = uc.Chrome(options=options)
                        st.session_state['driver'] = driver_instance
                    image_urls = scrape_images_interactively(st.session_state.driver, job["url"])
                else:
                    st.write("Étape 2/4 : Scraping des images...")
                    # --- MODIFICATION CLÉ ---
                    image_urls = scrape_images(job["url"], min_width=min_image_width)
                    # --- FIN DE LA MODIFICATION ---

                if not image_urls:
                    status.update(label="Erreur de scraping !", state="error", expanded=True)
                    st.error("❌ Aucune image trouvée. Réessayez ou vérifiez l'URL.")
                else:
                    st.write(f"Étape 3/4 : Découpage et traitement de {len(image_urls)} images...")
                    total_panels = process_and_save(image_urls, job["name"], job["num"], quality=quality_setting, timeout=timeout_setting)
                    
                    st.session_state.session_stats['chapters_processed'] += 1
                    st.session_state.session_stats['images_downloaded'] += total_panels
                    
                    st.write("Étape 4/4 : Finalisation...")
                    status.update(label="Traitement terminé avec succès !", state="complete", expanded=False)
                    
                    st.balloons(); st.success(f"🎉 Chapitre traité avec succès ! {total_panels} planches sauvegardées.")
                    
                    safe_name = re.sub(r'[^\w\-_]', '', job["name"]); safe_num = str(job["num"]).replace('.', '_')
                    output_dir = Path("output") / safe_name / safe_num
                    if output_dir.exists() and total_panels > 0:
                        st.markdown("---")
                        zip_bytes = create_zip_in_memory(output_dir)
                        zip_filename = f"{safe_name}-Chapitre-{safe_num}.zip"
                        st.download_button(
                           label=f"📂 Télécharger le ZIP du Chapitre {job['num']}",
                           data=zip_bytes, file_name=zip_filename, mime="application/zip", use_container_width=True
                        )
            finally:
                if 'driver' in st.session_state:
                    st.session_state.driver.quit(); del st.session_state['driver']
                if 'scraping_job' in st.session_state:
                    del st.session_state['scraping_job']
                    time.sleep(3); st.rerun()

elif app_mode == "Traitement par Lots":
    st.markdown("## 📦 Mode Traitement par Lots")
    # ... (Interface du formulaire - inchangée)
    col1, col2 = st.columns(2)
    col1.markdown(create_feature_card("Découverte Intelligente", "Analyse la page de série pour trouver tous les chapitres", "🔍"), unsafe_allow_html=True)
    col2.markdown(create_feature_card("Traitement en Série", "Télécharge plusieurs chapitres et les regroupe dans un ZIP unique", "⚡"), unsafe_allow_html=True)
    st.markdown("---")
    with st.container():
        st.markdown("### 📝 Configuration du Lot")
        series_page_url = st.text_input("🏠 URL de la Page Principale de la Série", placeholder="https://example.com/series/solo-leveling")
        manhwa_name_batch = st.text_input("📖 Nom de la Série", placeholder="Sera déduit automatiquement si vide")
        st.markdown("### 📊 Plage de Chapitres")
        col1, col2 = st.columns(2)
        start_chapter_input = col1.number_input("Chapitre de Début", 1.0, step=0.5, format="%.1f")
        end_chapter_input = col2.number_input("Chapitre de Fin", start_chapter_input, step=0.5, format="%.1f")
        run_batch_button = st.button("🚀 Lancer la Découverte et le Traitement", type="primary", use_container_width=True, disabled=not series_page_url)

    if run_batch_button and series_page_url:
        with st.spinner("🕵️‍♂️ Découverte des chapitres en cours..."):
            available_chapters = discover_chapters(series_page_url)
        
        if not available_chapters:
            st.error("❌ Aucun chapitre découvert. Vérifiez l'URL de la série.")
        else:
            st.markdown(create_status_indicator('success', f'✅ {len(available_chapters)} chapitres découverts.'), unsafe_allow_html=True)
            chapters_to_process = {num: url for num, url in available_chapters.items() if start_chapter_input <= num <= end_chapter_input}
            
            if not chapters_to_process:
                st.warning("⚠️ Aucun chapitre trouvé dans la plage sélectionnée.")
            else:
                st.success(f"🎯 {len(chapters_to_process)} chapitres à traiter.")
                final_manhwa_name = manhwa_name_batch or series_page_url.strip('/').split('/')[-1]
                safe_manhwa_name = re.sub(r'[^\w\-_]', '', final_manhwa_name)
                
                overall_progress = st.progress(0)
                chapters_sorted = sorted(chapters_to_process.items())
                
                for i, (chap_num, chap_url) in enumerate(chapters_sorted):
                    st.markdown(f"--- \n**📖 Traitement du Chapitre {chap_num}** ({i+1}/{len(chapters_sorted)})")
                    # --- MODIFICATION CLÉ ---
                    image_urls_batch = scrape_images(chap_url, min_width=min_image_width)
                    # --- FIN DE LA MODIFICATION ---
                    
                    if image_urls_batch:
                        panels_saved = process_and_save(image_urls_batch, final_manhwa_name, chap_num, quality=quality_setting, timeout=timeout_setting)
                        st.session_state.session_stats['chapters_processed'] += 1
                        st.session_state.session_stats['images_downloaded'] += panels_saved
                        st.write(f"-> {panels_saved} planches sauvegardées.")
                    else:
                        st.warning(f"-> Aucune image trouvée pour le chapitre {chap_num}.")
                    overall_progress.progress((i + 1) / len(chapters_sorted))
                
                st.balloons()
                st.success(f"🎉 Traitement par lots terminé !")

                st.markdown("---"); st.markdown("### 📥 Télécharger le lot complet")
                batch_output_root_dir = Path("output") / safe_manhwa_name
                if batch_output_root_dir.exists():
                    with st.spinner("Compression de l'archive ZIP en cours..."):
                        zip_bytes = create_zip_in_memory(batch_output_root_dir)
                    start_str = str(start_chapter_input).replace('.', '_'); end_str = str(end_chapter_input).replace('.', '_')
                    zip_filename = f"{safe_manhwa_name}-Chapitres_{start_str}_a_{end_str}.zip"
                    st.download_button(
                       label=f"📂 Télécharger le ZIP de la série ({len(chapters_to_process)} chapitres)",
                       data=zip_bytes, file_name=zip_filename, mime="application/zip", use_container_width=True
                    )
                else:
                    st.warning("Aucun dossier de sortie à compresser n'a été trouvé.")