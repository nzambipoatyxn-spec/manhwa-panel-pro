# app.py - Refonte intégrée (Streamlit UI + ScraperEngine)
import streamlit as st
import time
import os
import io
import zipfile
import re
from pathlib import Path
from urllib.parse import urljoin

from loguru import logger

# imports locaux
from core import WebSession
from scrapers import (
    discover_chapters_flamecomics,
    discover_chapters_madara_theme,
    discover_chapters_asuracomic,
    discover_chapters_mangadex,
    discover_chapters_raijin_scans,
    scrape_images_mangadex,
    detect_site_type
)
from sites_config import SUPPORTED_SITES
from scraper_engine import ScraperEngine
from http_utils import download_all_images, download_image_smart
from validation import get_validator, ValidationError

# Configuration logs avec loguru (rotation automatique)
logger.add("app.log", rotation="10 MB", retention="7 days", level="INFO")

# App config Streamlit
st.set_page_config(page_title="PANELia", page_icon="📚", layout="wide")
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

# SIDEBAR - paramètres et initialisation safe
with st.sidebar:
    st.markdown("### 🎛️ Panneau de Contrôle")
    if 'session_stats' not in st.session_state:
        st.session_state.session_stats = {'chapters_processed': 0, 'images_downloaded': 0}
    col1, col2 = st.columns(2)
    col1.metric("Chapitres Traités", st.session_state.session_stats['chapters_processed'])
    col2.metric("Planches Sauvegardées", st.session_state.session_stats['images_downloaded'])
    st.markdown("---")
    with st.expander("⚙️ Paramètres Avancés"):
        # widgets créent automatiquement les clés dans st.session_state
        st.session_state.quality_setting_value = st.slider("Qualité JPEG", 70, 100, st.session_state.get("quality_setting_value", 92))
        st.session_state.min_image_width_value = st.number_input("Largeur minimale (px)", 200, 800, st.session_state.get("min_image_width_value", 400))
        st.session_state.timeout_setting_value = st.number_input("Timeout (sec)", 10, 60, st.session_state.get("timeout_setting_value", 30))

# --- Defensive initialization (assure que les clés existent si UI non rendue)
if "min_image_width_value" not in st.session_state:
    st.session_state.min_image_width_value = 400
if "quality_setting_value" not in st.session_state:
    st.session_state.quality_setting_value = 92
if "timeout_setting_value" not in st.session_state:
    st.session_state.timeout_setting_value = 30
if "session_stats" not in st.session_state:
    st.session_state.session_stats = {'chapters_processed': 0, 'images_downloaded': 0}

# Helper functions
def extract_series_title_from_html(page_html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page_html, 'html.parser')
        h1_tag = soup.find('h1')
        return h1_tag.text.strip() if h1_tag else None
    except Exception:
        return None

def discover_chapters(series_url: str, session: WebSession):
    logger.info(f"Découverte pour : {series_url}")
    scraper_function, needs_selenium, strategy_found = (None, True, False)
    for domain, (func, needs_sel) in SUPPORTED_SITES.items():
        if domain in series_url:
            scraper_function, needs_selenium, strategy_found = func, needs_sel, True
            break

    if not strategy_found:
        st.warning("Aucun scraper spécialisé. Lancement de la cascade de repli...")
        page_html = session.page_source
        fallback_strategies = [("Madara", discover_chapters_madara_theme), ("AsuraComic", discover_chapters_asuracomic)]
        for name, func in fallback_strategies:
            try:
                chapters = func(page_html, series_url)
                if chapters:
                    st.success(f"La stratégie de repli '{name}' a fonctionné !")
                    return chapters, extract_series_title_from_html(page_html)
            except Exception:
                continue
        st.error("Toutes les stratégies de repli ont échoué.")
        return {}, None

    if not needs_selenium:
        chapters = scraper_function(series_url)
        return chapters, None
    else:
        chapters = scraper_function(session, series_url)
        title = extract_series_title_from_html(session.page_source)
        return chapters, title

def create_zip_in_memory(folder_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
        p = Path(folder_path)
        for file in p.glob('**/*.jpg'):
            relative_path = file.relative_to(p.parent)
            zip_file.write(file, arcname=relative_path)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# UI Flow state
if 'app_state' not in st.session_state:
    st.session_state.app_state = 'INPUT'

sites_requiring_human_intervention = ["raijin-scans.fr", "arenascan.com", "mangas-origines.fr"]
sites_requiring_driver_download = ["mangas-origines.fr"]

def cleanup_session():
    if st.session_state.get('web_session'):
        try:
            st.session_state.web_session.quit()
        except Exception:
            pass
    if st.session_state.get('driver_pool'):
        for d in st.session_state.driver_pool:
            try:
                d.quit()
            except Exception:
                pass
    keys_to_reset = ['web_session', 'app_state', 'chapters_discovered', 'title_discovered', 'last_url_searched', 'chapters_to_process', 'final_manhwa_name', 'safe_manhwa_name', 'driver_pool']
    for key in keys_to_reset:
        if key in st.session_state: del st.session_state[key]

# App steps
if st.session_state.app_state == 'INPUT':
    st.markdown("### 1. URL de la Page Principale de la Série")
    st.text_input("URL", key="series_url_input", placeholder="https://...", label_visibility="collapsed")
    if st.button("🔍 Lancer la Découverte", use_container_width=True, disabled=not st.session_state.series_url_input):
        # Valider l'URL avant de continuer
        validator = get_validator()
        try:
            validated_url = validator.validate_url(
                st.session_state.series_url_input,
                allow_any_domain=True  # Permettre fallback
            )
            st.session_state.last_url_searched = validated_url
            st.session_state.is_interactive = any(d in st.session_state.last_url_searched for d in sites_requiring_human_intervention)
            st.session_state.app_state = 'DISCOVERING'
            logger.info(f"URL validée et prête pour découverte : {validated_url}")
            st.rerun()
        except ValidationError as e:
            st.error(f"❌ URL invalide : {e}")
            logger.warning(f"Validation URL échouée : {e}")

elif st.session_state.app_state == 'DISCOVERING':
    is_interactive = st.session_state.get('is_interactive', False)
    if 'web_session' not in st.session_state or st.session_state.web_session is None:
        with st.spinner("Démarrage de la session de navigation..."):
            try:
                st.session_state.web_session = WebSession(headless=not is_interactive)
            except Exception as e:
                st.error(f"Erreur de démarrage du navigateur: {e}")
                cleanup_session()
                st.stop()

    if is_interactive:
        st.session_state.web_session.get(st.session_state.last_url_searched)
        st.session_state.app_state = 'AWAITING_CAPTCHA'
        st.rerun()
    else:
        with st.spinner("Découverte des chapitres..."):
            try:
                chapters, title = discover_chapters(st.session_state.last_url_searched, st.session_state.web_session)
                st.session_state.chapters_discovered = chapters
                st.session_state.title_discovered = title
            except Exception as e:
                st.error(f"Erreur découverte: {e}")
                cleanup_session()
                st.stop()
        st.session_state.app_state = 'READY_TO_PROCESS'
        st.rerun()

elif st.session_state.app_state == 'AWAITING_CAPTCHA':
    st.warning("**ACTION REQUISE !**")
    st.info("Veuillez résoudre le CAPTCHA dans le navigateur, puis revenez ici.")
    if st.button("✅ CAPTCHA résolu, continuer"):
        with st.spinner("Découverte en cours..."):
            chapters, title = discover_chapters(st.session_state.last_url_searched, st.session_state.web_session)
            st.session_state.chapters_discovered = chapters
            st.session_state.title_discovered = title
        st.session_state.app_state = 'READY_TO_PROCESS'
        st.rerun()

elif st.session_state.app_state in ['READY_TO_PROCESS', 'PROCESSING_DONE']:
    if st.button("🔄 Nouvelle Recherche"):
        cleanup_session()
        st.rerun()

    if st.session_state.app_state == 'PROCESSING_DONE':
        st.success("🎉 Traitement du lot terminé !")
        st.markdown("---")
        st.markdown("### 📥 Télécharger le lot complet")
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
        else:
            st.warning("Aucun dossier de sortie trouvé.")

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
            # Valider la plage de chapitres
            validator = get_validator()
            try:
                validated_start, validated_end = validator.validate_chapter_range(start_ch, end_ch)
                st.session_state.chapters_to_process = {n: u for n, u in available_chapters.items() if validated_start <= n <= validated_end}

                # Valider le nom du manhwa
                raw_name = st.session_state.get('title_discovered') or re.sub(r'https?://', '', st.session_state.last_url_searched).split('/')[1].replace('-', ' ').title()
                st.session_state.final_manhwa_name = validator.validate_filename(raw_name, allow_path=False)
                st.session_state.safe_manhwa_name = re.sub(r'[^\w\-_]', '', st.session_state.final_manhwa_name)

                logger.info(f"Plage validée : {validated_start} à {validated_end} ({len(st.session_state.chapters_to_process)} chapitres)")
                st.session_state.app_state = 'PROCESSING'
                st.rerun()
            except ValidationError as e:
                st.error(f"❌ Validation échouée : {e}")
                logger.warning(f"Validation plage/nom échouée : {e}")

elif st.session_state.app_state == 'PROCESSING':
    # Validation des paramètres avant traitement
    validator = get_validator()
    try:
        # Lecture et validation des paramètres UI
        min_width_value = validator.validate_min_width(st.session_state.get("min_image_width_value", 400))
        quality_value = validator.validate_quality(st.session_state.get("quality_setting_value", 92))
        timeout_value = validator.validate_timeout(st.session_state.get("timeout_setting_value", 30))
        final_manhwa_name = st.session_state.final_manhwa_name
        safe_manhwa_name = st.session_state.safe_manhwa_name
        chapters_to_process = st.session_state.chapters_to_process

        logger.info(f"Paramètres validés - Largeur min: {min_width_value}px, Qualité: {quality_value}%, Timeout: {timeout_value}s")
    except ValidationError as e:
        st.error(f"❌ Paramètres invalides : {e}")
        logger.error(f"Validation paramètres échouée : {e}")
        st.session_state.app_state = 'READY_TO_PROCESS'
        st.rerun()

    # Instanciation du moteur (config recommandée)
    try:
        num_drivers_validated = validator.validate_num_drivers(3)
        max_workers_validated = validator.validate_max_workers(4)

        engine = ScraperEngine(
            work_dir="output",
            num_drivers=num_drivers_validated,
            image_workers_per_chap=max_workers_validated,
            throttle_min=0.08,
            throttle_max=0.15,
            driver_start_delay=0.8
        )
    except ValidationError as e:
        st.error(f"❌ Configuration moteur invalide : {e}")
        logger.error(f"Validation config moteur échouée : {e}")
        st.session_state.app_state = 'READY_TO_PROCESS'
        st.rerun()

    total_chapters = len(chapters_to_process)
    overall_progress = st.progress(0)
    status_box = st.empty()

    # IMPORTANT : déclarer juste ici
    completed_counter = 0

    def ui_progress_callback(completed: int, total: int, result: dict):
        overall_progress.progress(completed / total)
        if result.get("error"):
            status_box.error(f"Chapitre {result['chap_num']} : Erreur -> {result['error']}")
        else:
            status_box.success(
                f"Chapitre {result['chap_num']} : {result['panels_saved']} planches sauvegardées "
                f"(sources: {result['found_count']}, téléchargées: {result['downloaded_count']})."
            )

        st.session_state.session_stats['chapters_processed'] += 1
        st.session_state.session_stats['images_downloaded'] += result.get('panels_saved', 0)


    params = {
        "min_image_width_value": min_width_value,
        "quality_value": quality_value,
        "timeout_value": timeout_value,
        "final_manhwa_name": final_manhwa_name
    }

    try:
        st.info(f"🟢 Lancement du traitement parallèle ({total_chapters} chapitres)...")
        results = engine.run_chapter_batch(chapters_to_process, params, ui_progress_callback=ui_progress_callback)
    except Exception as e:
        logger.error("Erreur critique lors du run_chapter_batch: %s", e, exc_info=True)
        st.error("Erreur critique lors du traitement. Voir logs.")
    finally:
        try:
            engine.stop_driver_pool()
        except Exception:
            pass

    st.balloons()
    st.success("🎉 Traitement terminé !")
    st.session_state.app_state = 'PROCESSING_DONE'
    st.rerun()
