import sys
import os
sys.path.append(os.getcwd())

# Force UTF-8 encoding for stdout
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from panelia.scrapers.factory import detect_site_type, discover_chapters_madara_theme
from panelia.core.driver import WebSession
from loguru import logger

def test_manga_scantrad():
    url = "https://manga-scantrad.io/manga/solo-leveling-ragnarok/"
    site_type = detect_site_type(url)
    print(f"Type detecte pour {url} : {site_type}")
    
    if site_type != "madara":
        print("[ERREUR] : Le site devrait etre detecte comme 'madara'")
        return

    print("Tentative de decouverte des chapitres (necessite Selenium)...")
    try:
        with WebSession(headless=True) as session:
            chapters = discover_chapters_madara_theme(session, url)
            print(f"[OK] Nombre de chapitres trouves : {len(chapters)}")
            if chapters:
                sorted_chaps = sorted(chapters.items(), reverse=True)
                for num, link in sorted_chaps[:3]:
                    print(f"   - Chapitre {num}: {link}")
            else:
                print("[ALERTE] Aucun chapitre trouve. Verification du HTML...")
                with open("debug_manga_scantrad.html", "w", encoding="utf-8") as f:
                    f.write(session.page_source)
                print("Dump HTML sauvegarde dans debug_manga_scantrad.html")
    except Exception as e:
        print(f"[ERREUR] lors du test : {e}")

if __name__ == "__main__":
    test_manga_scantrad()
