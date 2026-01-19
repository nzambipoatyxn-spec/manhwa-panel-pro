import httpx
import io
from PIL import Image
import os
import sys

def test_ai_connectivity(api_url="http://localhost:8000"):
    print(f"--- Diagnostic IA PANELia ---")
    print(f"Tentative de connexion à : {api_url}")
    
    try:
        # 1. Test de Santé
        print("\n[STEP 1] Vérification de l'état du service...")
        r = httpx.get(f"{api_url}/health", timeout=5.0)
        if r.status_code == 200:
            print(f"✅ Service en ligne ! Détails : {r.json()}")
        else:
            print(f"❌ Service répond avec le code {r.status_code}")
            return

        # 2. Test de Nettoyage Réel
        print("\n[STEP 2] Test de nettoyage d'une image factice...")
        # Création d'une image blanche de 100x100
        img = Image.new('RGB', (100, 100), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        image_data = buf.getvalue()

        files = {"file": ("test.jpg", image_data, "image/jpeg")}
        r = httpx.post(f"{api_url}/clean", files=files, timeout=60.0)

        if r.status_code == 200:
            print("✅ Succès ! L'IA a renvoyé une image nettoyée.")
            out_img = Image.open(io.BytesIO(r.content))
            print(f"Taille de l'image reçue : {out_img.size}")
            
            # Sauvegarde du résultat pour vérification visuelle
            out_path = "test_ai_result.jpg"
            out_img.save(out_path)
            print(f"👉 Résultat sauvegardé sous : {os.path.abspath(out_path)}")
        else:
            print(f"❌ Échec du nettoyage. Code : {r.status_code}")
            print(f"Erreur : {r.text}")

    except Exception as e:
        print(f"🚨 Erreur critique : {str(e)}")
        print("\n💡 Vérifiez que :")
        print("1. Le service est bien lancé : `python cleaner_service.py` dans le terminal dédié.")
        print("2. Les dépendances IA sont installées.")

if __name__ == "__main__":
    test_ai_connectivity()
