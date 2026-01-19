import sys
import os
import traceback

print("=== Diagnostic des Imports PANELia ===")
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")
print(f"Executable: {sys.executable}")
print("-" * 30)

modules_to_test = [
    "streamlit",
    "undetected_chromedriver",
    "webdriver_manager",
    "selenium",
    "bs4",
    "httpx",
    "cv2",
    "numpy",
    "PIL",
    "loguru"
]

for mod in modules_to_test:
    try:
        if mod == "bs4":
            from bs4 import BeautifulSoup
            print(f"✅ {mod}: OK")
        elif mod == "PIL":
            from PIL import Image
            print(f"✅ {mod}: OK")
        else:
            __import__(mod)
            print(f"✅ {mod}: OK")
    except ImportError as e:
        print(f"❌ {mod}: ÉCHEC - {e}")
    except Exception as e:
        print(f"❓ {mod}: Erreur inattendue - {e}")

print("-" * 30)
try:
    print("Tentative d'import local: panelia.scrapers.factory...")
    from panelia.scrapers.factory import discover_chapters_mangadex
    print("✅ panelia.scrapers.factory: OK")
except Exception:
    print("❌ panelia.scrapers.factory: ÉCHEC")
    traceback.print_exc()

print("-" * 30)
print("Diagnostic terminé.")
