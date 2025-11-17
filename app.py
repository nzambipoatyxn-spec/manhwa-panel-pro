# app.py - v8.5 - Version Finale Stable du MVP

# --- IMPORTS COMPLETS ---
import streamlit as st
import requests
import time
import os
import io
import subprocess
import re
import zipfile
from pathlib import Path
from urllib.parse import urljoin
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import logging

from core import WebSession
from scrapers import (
    discover_chapters_flamecomics,
    discover_chapters_madara_theme,
    discover_chapters_asuracomic,
    discover_chapters_mangadex,
    discover_chapters_raijin_scans,
    scrape_images_mangadex,
    scrape_images_smart,
    process_image_smart,
    detect_site_type
)
from sites_config import SUPPORTED_SITES

# --- CONFIGURATION DU LOGGING ---
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# --- FONCTIONS "CERVEAU" DE L'APPLICATION ---

def extract_series_title_from_html(page_html: str) -> str:
    """Chasse la balise H1 pour trouver le vrai titre de la série."""
    try:
        soup = BeautifulSoup(page_html, 'html.parser')
        h1_tag = soup.find('h1')
        if h1_tag: return h1_tag.text.strip()
    except Exception: pass
    return None

def discover_chapters(series_url: str, session):
    """Fonction manager de découverte, utilisant une WebSession fournie."""
    logging.info(f"Découverte pour : {series_url}")
    
    scraper_function, needs_selenium, strategy_found = (None, True, False)
    
    for domain, (func, needs_sel) in SUPPORTED_SITES.items():
        if domain in series_url:
            scraper_function, needs_selenium, strategy_found = func, needs_sel, True
            break
            
    if not strategy_found:
        st.warning("Aucun scraper spécialisé. Lancement de la cascade de repli...")
        fallback_strategies = [("Madara", discover_chapters_madara_theme), ("AsuraComic", discover_chapters_asuracomic)]
        page_html = session.page_source
        for name, func in fallback_strategies:
            chapters = func(page_html, series_url)
            if chapters:
                st.success(f"La stratégie de repli '{name}' a fonctionné !"); return chapters, extract_series_title_from_html(page_html)
        st.error("Toutes les stratégies de repli ont échoué."); return {}, None

    if not needs_selenium:
        chapters = scraper_function(series_url)
        return chapters, None
    else:
        scrapers_needing_driver = ['discover_chapters_flamecomics', 'discover_chapters_madara_theme']
        if scraper_function.__name__ in scrapers_needing_driver:
            chapters = scraper_function(session, series_url)
            title = extract_series_title_from_html(session.page_source)
            return chapters, title
        else:
            session.get(series_url)
            page_html = session.page_source
            chapters = scraper_function(page_html, series_url)
            title = extract_series_title_from_html(page_html)
            return chapters, title

def download_image_parallel(url_timeout_tuple):
    url, timeout = url_timeout_tuple
    try:
        response = requests.get(url, timeout=timeout); response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException: return None

def download_all_images(image_urls, timeout=30, max_workers=8):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = [(url, timeout) for url in image_urls]
        results = list(executor.map(download_image_parallel, tasks))
    return [res for res in results if res is not None]

def process_and_save(image_bytes_list: list, manhwa_name: str, chapter_num: float, quality: int = 92):
    safe_manhwa_name = re.sub(r'[^\w\-_]', '', manhwa_name)
    safe_chapter_num = str(chapter_num).replace('.', '_')
    output_dir = Path("output") / safe_manhwa_name / safe_chapter_num
    output_dir.mkdir(parents=True, exist_ok=True)
    total_files_saved = 0
    for image_bytes in image_bytes_list:
        try:
            images_to_save = process_image_smart(image_bytes)
            for img in images_to_save:
                filename = f"planche_{total_files_saved + 1:03d}.jpg"
                panel_path = output_dir / filename
                img.convert('RGB').save(panel_path, "JPEG", quality=quality, optimize=True)
                total_files_saved += 1
        except Exception: pass
    return total_files_saved

def create_zip_in_memory(folder_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
        p = Path(folder_path)
        for file in p.glob('**/*.jpg'):
            relative_path = file.relative_to(p.parent)
            zip_file.write(file, arcname=relative_path)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# --- UI & CSS ---
st.set_page_config(page_title="PANELia", page_icon="📚", layout="wide", initial_sidebar_state="expanded")
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
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color), #FF6B6B); color: white; border: none;
        border-radius: var(--border-radius); padding: 0.75rem 2rem; font-weight: 600;
        transition: var(--transition); box-shadow: var(--box-shadow);
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 12px rgba(255, 75, 75, 0.3); }
    .stProgress > div > div > div { background: linear-gradient(90deg, var(--accent-color), var(--secondary-color)); border-radius: 10px; }
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="main-header">
    <h1>📚 PANELia</h1>
    <p>Votre solution moderne pour télécharger et organiser votre matière première</p>
</div>""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🎛️ Panneau de Contrôle")
    if 'session_stats' not in st.session_state: st.session_state.session_stats = {'chapters_processed': 0, 'images_downloaded': 0}
    stats = st.session_state.session_stats
    col1, col2 = st.columns(2); col1.metric("Chapitres Traités", stats['chapters_processed']); col2.metric("Planches Sauvegardées", stats['images_downloaded'])
    st.markdown("---")
    with st.expander("⚙️ Paramètres Avancés"):
        st.session_state.quality_setting_value = st.slider("Qualité JPEG", 70, 100, 92)
        st.session_state.min_image_width_value = st.number_input("Largeur minimale (px)", 200, 800, 400)
        st.session_state.timeout_setting_value = st.number_input("Timeout (sec)", 10, 60, 30)

# --- CORPS PRINCIPAL DE L'APPLICATION ---
st.markdown("## 🚀 Lancer un Nouveau Travail de Scraping")
sites_requiring_human_intervention = ["raijin-scans.fr", "arenascan.com"]

def cleanup_session():
    if 'web_session' in st.session_state and st.session_state.web_session:
        st.session_state.web_session.quit()
    keys_to_reset = ['web_session', 'app_state', 'chapters_discovered', 'title_discovered', 'last_url_searched', 'chapters_to_process', 'final_manhwa_name', 'safe_manhwa_name', 'start_chapter_sel', 'end_chapter_sel']
    for key in keys_to_reset:
        if key in st.session_state: del st.session_state[key]

if 'app_state' not in st.session_state: st.session_state.app_state = 'INPUT'

if st.session_state.app_state == 'INPUT':
    st.markdown("### 1. URL de la Page Principale de la Série")
    st.text_input("URL", placeholder="https://example.com/series/...", label_visibility="collapsed", key="series_url_input")
    if st.button("🔍 Lancer la Découverte", use_container_width=True, disabled=not st.session_state.get("series_url_input")):
        st.session_state.last_url_searched = st.session_state.series_url_input
        st.session_state.is_interactive = any(d in st.session_state.last_url_searched for d in sites_requiring_human_intervention)
        st.session_state.app_state = 'DISCOVERING'
        st.rerun()

elif st.session_state.app_state == 'DISCOVERING':
    is_interactive = st.session_state.get('is_interactive', False)
    with st.spinner("Démarrage de la session de navigation..."):
        if 'web_session' not in st.session_state or st.session_state.web_session is None:
            st.session_state.web_session = WebSession(headless=not is_interactive)
    
    if is_interactive:
        st.session_state.web_session.get(st.session_state.last_url_searched)
        st.session_state.app_state = 'AWAITING_CAPTCHA'
        st.rerun()
    else:
        with st.spinner("Découverte des chapitres..."):
            chapters, title = discover_chapters(st.session_state.last_url_searched, st.session_state.web_session)
            st.session_state.chapters_discovered, st.session_state.title_discovered = chapters, title
        st.session_state.app_state = 'READY_TO_PROCESS'
        st.rerun()

elif st.session_state.app_state == 'AWAITING_CAPTCHA':
    st.warning("**ACTION REQUISE !**"); st.info("Veuillez résoudre le CAPTCHA dans le navigateur, puis revenez ici.")
    if st.button("✅ CAPTCHA résolu, continuer"):
        with st.spinner("Découverte en cours..."):
            chapters, title = discover_chapters(st.session_state.last_url_searched, st.session_state.web_session)
            st.session_state.chapters_discovered, st.session_state.title_discovered = chapters, title
        st.session_state.app_state = 'READY_TO_PROCESS'; st.rerun()

elif st.session_state.app_state in ['READY_TO_PROCESS', 'PROCESSING_DONE']:
    if st.button("🔄 Nouvelle Recherche"): cleanup_session(); st.rerun()

    if st.session_state.app_state == 'PROCESSING_DONE':
        st.success("🎉 Traitement du lot terminé !")
        st.markdown("---"); st.markdown("### 📥 Télécharger le lot complet")
        safe_manhwa_name = st.session_state.safe_manhwa_name
        batch_output_root_dir = Path("output") / safe_manhwa_name
        if batch_output_root_dir.exists() and st.session_state.get('chapters_to_process'):
            with st.spinner("Compression de l'archive ZIP en cours..."):
                zip_bytes = create_zip_in_memory(batch_output_root_dir)
            processed_numbers = list(st.session_state.chapters_to_process.keys())
            start_str = str(min(processed_numbers)).replace('.', '_')
            end_str = str(max(processed_numbers)).replace('.', '_')
            zip_filename = f"{safe_manhwa_name}-Chapitres_{start_str}_a_{end_str}.zip"
            st.download_button(label=f"📂 Télécharger le ZIP", data=zip_bytes, file_name=zip_filename, mime="application/zip", use_container_width=True)
        else: st.warning("Aucun dossier de sortie trouvé.")
    
    available_chapters = st.session_state.get('chapters_discovered', {})
    if not available_chapters:
        st.error("❌ Aucun chapitre n'a pu être découvert.")
    elif st.session_state.app_state == 'READY_TO_PROCESS':
        st.success(f"✅ {len(available_chapters)} chapitres découverts !")
        st.info(f"**Titre Détecté:** {st.session_state.get('title_discovered') or 'Non trouvé'}")
        
        st.markdown("### 2. Sélectionnez la Plage de Chapitres")
        chapters_list = sorted(available_chapters.keys())
        col1, col2 = st.columns(2)
        start_ch = col1.selectbox("Début", chapters_list, key="start_chapter_sel")
        end_ch_opts = [c for c in chapters_list if c >= start_ch]
        end_ch = col2.selectbox("Fin", end_ch_opts, index=len(end_ch_opts)-1, key="end_chapter_sel")

        if st.button("🚀 Lancer le Traitement du Lot", type="primary", use_container_width=True):
            st.session_state.chapters_to_process = {n: u for n, u in available_chapters.items() if start_ch <= n <= end_ch}
            st.session_state.final_manhwa_name = st.session_state.get('title_discovered') or re.sub(r'https?://', '', st.session_state.last_url_searched).split('/')[1].replace('-', ' ').title()
            st.session_state.safe_manhwa_name = re.sub(r'[^\w\-_]', '', st.session_state.final_manhwa_name)
            st.session_state.app_state = 'PROCESSING'; st.rerun()

elif st.session_state.app_state == 'PROCESSING':
    chapters_to_process = st.session_state.chapters_to_process
    final_name = st.session_state.final_manhwa_name
    
    st.markdown(f"### 📊 Traitement de {len(chapters_to_process)} chapitres...")
    overall_progress = st.progress(0)
    sorted_chaps = sorted(chapters_to_process.items())
    total_chapters = len(sorted_chaps)
    
    web_session = st.session_state.get('web_session')
    if not web_session and any(detect_site_type(u) != "mangadex" for u in chapters_to_process.values()):
        st.error("Session navigateur perdue !"); st.stop()

    for i, (chap_num, chap_url) in enumerate(sorted_chaps):
        overall_progress.progress((i + 1) / total_chapters, f"Chapitre {chap_num} ({i+1}/{total_chapters})")
        try:
            with st.spinner(f"📖 Chapitre {chap_num} en cours..."):
                site_type = detect_site_type(chap_url)
                if site_type == "mangadex": image_urls = scrape_images_mangadex(chap_url)
                else: image_urls = scrape_images_smart(web_session, chap_url, min_width=st.session_state.min_image_width_value)
                found_count = len(image_urls)
                st.info(f"🔍 {found_count} images sources trouvées.")
                if image_urls:
                    with st.spinner(f"Téléchargement de {found_count} images..."):
                        image_bytes_list = download_all_images(image_urls, timeout=st.session_state.timeout_setting_value)
                    downloaded_count = len(image_bytes_list)
                    if downloaded_count < found_count: st.warning(f"⚠️ {found_count - downloaded_count} image(s) n'ont pas pu être téléchargée(s).")
                    if downloaded_count > 0:
                        panels_saved = process_and_save(image_bytes_list, final_name, chap_num, quality=st.session_state.quality_setting_value)
                        st.write(f"✅ **{panels_saved} planches sauvegardées.**")
                        st.session_state.session_stats['chapters_processed'] += 1; st.session_state.session_stats['images_downloaded'] += panels_saved
                    else: st.error("❌ Aucune image n'a pu être téléchargée.")
                else: st.warning("⚠️ Aucune image trouvée.")
            if i < total_chapters - 1: time.sleep(3)
        except Exception:
            st.error(f"🔥 Erreur critique sur le Chapitre {chap_num}. Passage au suivant.")
            logging.error(f"ÉCHEC COMPLET pour chapitre {chap_num}", exc_info=True); continue

    st.balloons(); st.success("🎉 Traitement du lot terminé !")
    st.session_state.app_state = 'PROCESSING_DONE'; st.rerun()