# cleaning.py
"""
Support du nettoyage IA (Inpainting) pour PANELia via un service Sidecar.
L'application principale (Python 3.13) communique avec le service (Python 3.11) par HTTP.
"""

import io
import httpx
from PIL import Image
from loguru import logger

import os

class ManhwaCleaner:
    """
    Client pour le service de nettoyage IA.
    Envoie des images à un service local (FastAPI) pour l'inpainting.
    """
    def __init__(self, api_url: str = None):
        """
        Initialise le client.
        """
        # Priorité : argument > variable d'env > localhost
        self.api_url = api_url or os.getenv("CLEANER_API_URL", "http://localhost:8000/clean")
        self.health_url = self.api_url.replace("/clean", "/health")
        # Client persistant pour éviter de recréer une connexion à chaque image
        self.client = httpx.Client(timeout=60.0)
        logger.info(f"[Cleaner] Mode client activé - API : {self.api_url}")

    def check_health(self) -> bool:
        """
        Vérifie si le service sidecar est vivant et prêt.
        """
        try:
            response = self.client.get(self.health_url, timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    def process_pil(self, pil_image: Image.Image) -> Image.Image:
        """
        Envoie l'image PIL au service sidecar et renvoie l'image nettoyée.
        """
        try:
            # Conversion PIL -> JPEG en mémoire pour l'envoi
            buf = io.BytesIO()
            pil_image.save(buf, format="JPEG", quality=95)
            image_data = buf.getvalue()

            # Appel au service sidecar
            files = {"file": ("image.jpg", image_data, "image/jpeg")}
            response = self.client.post(self.api_url, files=files)

            if response.status_code == 200:
                return Image.open(io.BytesIO(response.content))
            else:
                logger.warning(f"[Cleaner] Erreur service ({response.status_code})")
                return pil_image

        except Exception as e:
            logger.warning(f"[Cleaner] Erreur connexion au service : {e}")
            return pil_image

    def close(self):
        """Ferme la session HTTP."""
        self.client.close()

    def __del__(self):
        try:
            self.close()
        except:
            pass
