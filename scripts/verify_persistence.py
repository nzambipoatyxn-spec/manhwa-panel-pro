import sys
import os
import shutil
from pathlib import Path

sys.path.append(os.getcwd())
from panelia.core.driver import WebSession

def test_persistent_profile():
    profile_id = "test_persistence"
    profile_dir = Path.cwd() / "profiles" / profile_id
    
    # Nettoyage si existe déjà
    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    
    print(f"Tentative de creation du profil : {profile_dir}")
    try:
        with WebSession(headless=True, profile_id=profile_id) as session:
            print("Session initialisee.")
            if profile_dir.exists():
                print(f"✅ SUCCES : Le dossier {profile_dir} a ete cree.")
            else:
                print(f"❌ ECHEC : Le dossier {profile_dir} n'existe pas.")
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")

if __name__ == "__main__":
    test_persistent_profile()
