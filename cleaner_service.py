# cleaner_service.py
"""
Service Sidecar pour le nettoyage IA (Inpainting).
S'exécute typiquement sous Python 3.11 pour compatibilité avec manga-image-translator.
"""

import io
import uvicorn
import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from loguru import logger
from contextlib import asynccontextmanager
import asyncio

# Initialisation différée du cleaner
cleaner = None
processing_lock = asyncio.Lock()

def get_cleaner():
    global cleaner
    if cleaner is None:
        try:
            # Ajout du dossier cloné au sys.path pour trouver tous les sous-modules (utils, detection, etc.)
            import sys
            import os
            git_repo_path = os.path.join(os.getcwd(), "manga-image-translator-git")
            if git_repo_path not in sys.path:
                sys.path.insert(0, git_repo_path)
            
            # Import depuis le package local
            from manga_translator.manga_translator import MangaTranslator
            import torch
            
            device_id = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Initialisation du MangaTranslator sur {device_id} (Lama)...")
            
            # Paramètres de base mimant les arguments CLI
            # Évite l'erreur 'NoneType has no attribute get'
            args = {
                'mode': 'demo', 
                'use_gpu': torch.cuda.is_available(),
                'verbose': True,
                'translator': 'none', # On ne veut que l'inpainting
                'target_lang': 'ENG',
                'inpainter': 'lama_large',
                'detector': 'default',
                'ocr': '48px_ctc',
                'kernel_size': 3
            }
            
            # Initialisation avec la configuration explicite
            cleaner = MangaTranslator(args)
            logger.info("Modèle prêt.")
        except Exception as e:
            logger.error(f"Erreur initialisation modèle : {e}")
            raise RuntimeError(f"Modèle non disponible : {e}")
    return cleaner

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge les modèles au démarrage et libère les ressources à la fin."""
    try:
        get_cleaner()
        logger.info("Modèle initialisé avec succès au démarrage.")
    except Exception as e:
        logger.error(f"Échec du chargement initial : {e}")
    yield
    if cleaner:
        logger.info("Fermeture du service IA...")

app = FastAPI(title="PANELia AI Cleaner Service", lifespan=lifespan)

@app.post("/clean")
async def clean_image(file: UploadFile = File(...)):
    """
    Reçoit une image, la nettoie (Inpainting) et renvoie le résultat.
    """
    try:
        # Lecture de l'image entrante
        content = await file.read()
        pil_img = Image.open(io.BytesIO(content)).convert('RGB')
        
        # Récupération du moteur
        translator = get_cleaner()
        
        from manga_translator.config import Config, Detector, Inpainter, Translator, Ocr
        
        # Configuration pour le nettoyage seulement
        conf = Config()
        conf.translator.translator = Translator.none
        conf.detector.detector = Detector.default
        conf.inpainter.inpainter = Inpainter.lama_large
        conf.ocr.ocr = Ocr.ocr48px_ctc
        
        async with processing_lock:
            # Appel au moteur dans une section critique (un seul à la fois)
            ctx = await translator.translate(pil_img, conf)
        
        # Extraction de l'image "inpainted" (le fond nettoyé)
        # L'objet retourné est généralement un Context qui contient .inpainted (numpy array ou PIL)
        # Si c'est un dictionnaire ou un objet, on essaie d'accéder à l'attribut.
        
        cleaned_image = None
        
        # Debug structure si nécessaire
        if hasattr(ctx, 'inpainted'):
            cleaned_image = ctx.inpainted
        elif isinstance(ctx, dict) and 'inpainted' in ctx:
            cleaned_image = ctx['inpainted']
        elif hasattr(ctx, 'final'):
             # Fallback sur final si inpainted n'est pas accessible (mais final aura le texte traduit)
             logger.warning("Image 'inpainted' non trouvée, utilisation de 'final' (risque de texte traduit).")
             cleaned_image = ctx.final
        
        if cleaned_image is None:
            raise ValueError("Impossible de récupérer l'image nettoyée du contexte.")

        # Conversion en PIL si c'est un numpy array
        if isinstance(cleaned_image, np.ndarray):
            out_img = Image.fromarray(cleaned_image)
        else:
            out_img = cleaned_image
            
        buf = io.BytesIO()
        out_img.save(buf, format="JPEG", quality=95)
        
        return Response(content=buf.getvalue(), media_type="image/jpeg")
    
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage : {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    is_ready = cleaner is not None
    return {
        "status": "ready" if is_ready else "loading",
        "device": "cuda" if cleaner and hasattr(cleaner, 'device') and cleaner.device == 'cuda' else "cpu"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
