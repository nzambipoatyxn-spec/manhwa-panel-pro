import cv2
import numpy as np
from PIL import Image
import io
from typing import List, Tuple
import logging

def detect_narrative_panels(image_bytes: bytes, 
                             min_gap_height: int = 50,        # AUGMENTÉ de 30 → 50
                             min_panel_height: int = 300,     # AUGMENTÉ de 150 → 300
                             min_content_ratio: float = 0.20, # AUGMENTÉ de 0.15 → 0.20
                             gap_consistency_threshold: float = 0.90) -> List[Image.Image]:
    """
    🎯 ALGORITHME V3 : DÉCOUPAGE PAR SCÈNE NARRATIVE
    
    Améliorations critiques :
    1. Seuils plus stricts (gaps plus grands, panels plus hauts)
    2. Validation de "consistance du gap" (doit être uniforme sur toute la largeur)
    3. Analyse de contexte vertical (éviter de couper au milieu d'une scène)
    4. Fusion des micro-panels en scènes cohérentes
    """
    
    try:
        # Charger l'image
        image = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        height, width = gray.shape
        
        logging.info(f"📏 Analyse image : {width}x{height}px")
        
        # ==== ÉTAPE 1 : Détection de lignes uniformes (gaps potentiels) ====
        row_means = gray.mean(axis=1)
        row_stds = gray.std(axis=1)
        
        # Seuil adaptatif
        brightness_threshold = np.percentile(row_means, 95)
        
        is_uniform = row_stds < 12  # Plus strict : variance < 12 (était 15)
        is_bright = row_means > max(brightness_threshold, 235)  # Plus strict : 235 (était 230)
        is_dark = row_means < 10  # Plus strict : 10 (était 15)
        
        candidate_lines = (is_uniform & (is_bright | is_dark))
        
        # ==== ÉTAPE 2 : Regrouper en zones de gap ====
        gap_zones = []
        in_gap = False
        gap_start = 0
        
        for i, is_gap_line in enumerate(candidate_lines):
            if is_gap_line and not in_gap:
                gap_start = i
                in_gap = True
            elif not is_gap_line and in_gap:
                gap_height = i - gap_start
                if gap_height >= min_gap_height:  # Filtre : gaps trop petits = ignorés
                    gap_zones.append((gap_start, i, gap_height))
                in_gap = False
        
        logging.info(f"🔍 {len(gap_zones)} gaps candidats détectés (hauteur ≥ {min_gap_height}px)")
        
        # ==== ÉTAPE 3 : VALIDATION DE CONSISTANCE DU GAP ====
        # Un vrai gap doit être uniforme sur TOUTE la largeur de l'image
        validated_gaps = []
        
        for gap_start, gap_end, gap_height in gap_zones:
            gap_region = gray[gap_start:gap_end, :]
            
            # Calculer la variance horizontale (par colonne)
            col_means = gap_region.mean(axis=0)
            col_variance = col_means.std()
            
            # Un vrai gap a une faible variance horizontale
            # (toutes les colonnes ont la même couleur)
            if col_variance < 15:  # Gap homogène
                # Vérifier aussi la consistance du gap (% de lignes uniformes)
                uniform_lines_in_gap = candidate_lines[gap_start:gap_end].sum()
                consistency_ratio = uniform_lines_in_gap / gap_height
                
                if consistency_ratio >= gap_consistency_threshold:  # 90% du gap est uniforme
                    validated_gaps.append((gap_start, gap_end, gap_height))
                    logging.info(f"  ✅ Gap validé à y={gap_start}-{gap_end} (hauteur: {gap_height}px, consistance: {consistency_ratio:.1%})")
                else:
                    logging.info(f"  ❌ Gap rejeté (inconsistant : {consistency_ratio:.1%})")
            else:
                logging.info(f"  ❌ Gap rejeté (variance horizontale : {col_variance:.1f})")
        
        # ==== ÉTAPE 4 : ANALYSE DE CONTEXTE VERTICAL ====
        # Éviter de couper au milieu d'une scène en analysant le contenu avant/après
        final_cut_points = []
        
        for gap_start, gap_end, gap_height in validated_gaps:
            # Analyser 100px avant et après le gap
            context_before_start = max(0, gap_start - 100)
            context_before = gray[context_before_start:gap_start, :]
            
            context_after_end = min(height, gap_end + 100)
            context_after = gray[gap_end:context_after_end, :]
            
            # Calculer la densité de contenu avant/après
            content_before = np.sum(context_before < 240) / context_before.size
            content_after = np.sum(context_after < 240) / context_after.size
            
            # Si les deux contextes ont du contenu significatif = vrai séparateur de scène
            if content_before > 0.15 and content_after > 0.15:
                cut_y = gap_start + gap_height // 2
                final_cut_points.append(cut_y)
                logging.info(f"  🎬 Cut point validé à y={cut_y} (contenu: {content_before:.1%} | {content_after:.1%})")
            else:
                logging.info(f"  ⚠️ Cut point rejeté (contexte insuffisant)")
        
        # ==== ÉTAPE 5 : DÉCOUPE FINALE AVEC FUSION DES MICRO-PANELS ====
        if not final_cut_points:
            logging.info("ℹ️ Aucun cut point validé → Image gardée entière")
            return [trim_whitespace_smart(image)]
        
        panels = []
        last_cut = 0
        
        for cut_y in final_cut_points:
            panel = image.crop((0, last_cut, width, cut_y))
            
            if panel.height >= min_panel_height:
                if has_sufficient_content(panel, min_content_ratio):
                    panels.append(trim_whitespace_smart(panel))
                    logging.info(f"  ✅ Panel sauvegardé : {panel.height}px")
                else:
                    logging.info(f"  ⚠️ Panel rejeté (contenu insuffisant : {calculate_content_ratio(panel):.1%})")
            else:
                logging.info(f"  ⚠️ Panel trop petit ignoré ({panel.height}px < {min_panel_height}px)")
            
            last_cut = cut_y
        
        # Dernier panel
        final_panel = image.crop((0, last_cut, width, height))
        if final_panel.height >= min_panel_height and has_sufficient_content(final_panel, min_content_ratio):
            panels.append(trim_whitespace_smart(final_panel))
            logging.info(f"  ✅ Panel final sauvegardé : {final_panel.height}px")
        
        result_count = len(panels) if panels else 1
        logging.info(f"🎯 Résultat : {result_count} panel(s) extrait(s)")
        
        return panels if panels else [trim_whitespace_smart(image)]
    
    except Exception as e:
        logging.error(f"❌ Erreur découpage : {e}", exc_info=True)
        return [trim_whitespace_smart(Image.open(io.BytesIO(image_bytes)))]


def calculate_content_ratio(panel: Image.Image, threshold: int = 240) -> float:
    """Calcule le ratio de pixels non-blancs."""
    img_array = np.array(panel.convert('L'))
    total_pixels = img_array.size
    non_white_pixels = np.sum(img_array < threshold)
    return non_white_pixels / total_pixels


def has_sufficient_content(panel: Image.Image, min_ratio: float = 0.20) -> bool:
    """
    Vérifie si le panel a assez de contenu.
    
    V3 : Seuil augmenté à 20% (était 15%) pour éviter les fragments.
    """
    content_ratio = calculate_content_ratio(panel)
    
    if content_ratio < min_ratio:
        return False
    
    # Distribution spatiale (grille 3x3)
    img_array = np.array(panel.convert('L'))
    height, width = img_array.shape
    
    zones_with_content = 0
    for i in range(3):
        for j in range(3):
            zone_h_start = i * height // 3
            zone_h_end = (i + 1) * height // 3
            zone_w_start = j * width // 3
            zone_w_end = (j + 1) * width // 3
            
            zone = img_array[zone_h_start:zone_h_end, zone_w_start:zone_w_end]
            zone_content_ratio = np.sum(zone < 240) / zone.size
            
            if zone_content_ratio > 0.08:  # Seuil augmenté : 8% (était 5%)
                zones_with_content += 1
    
    # V3 : Nécessite au moins 4 zones actives (était 3)
    return zones_with_content >= 4


def trim_whitespace_smart(image: Image.Image, threshold: int = 240) -> Image.Image:
    """Rogne les bords blancs en préservant les bordures décoratives."""
    img_array = np.array(image.convert('L'))
    
    # Détecter bordures noires (décoratives)
    has_black_border = (img_array[0, :].mean() < 50) or (img_array[-1, :].mean() < 50)
    
    if has_black_border:
        return image
    
    # Rogner normalement
    non_white_rows = np.where(np.any(img_array < threshold, axis=1))[0]
    non_white_cols = np.where(np.any(img_array < threshold, axis=0))[0]
    
    if non_white_rows.size > 0 and non_white_cols.size > 0:
        top = max(0, non_white_rows[0] - 5)
        bottom = min(image.height - 1, non_white_rows[-1] + 5)
        left = max(0, non_white_cols[0] - 5)
        right = min(image.width - 1, non_white_cols[-1] + 5)
        
        return image.crop((left, top, right + 1, bottom + 1))
    
    return image


def should_slice_image(image_bytes: bytes) -> bool:
    """
    Décide si une image doit être découpée.
    
    V3 : Critères plus stricts pour éviter le sur-découpage.
    """
    image = Image.open(io.BytesIO(image_bytes))
    ratio = image.height / image.width
    
    # Ratio < 3.5 = probablement manga classique ou double-page
    if ratio < 3.5:  # Augmenté de 3 → 3.5
        logging.info(f"ℹ️ Image non-découpable (ratio {ratio:.1f} < 3.5)")
        return False
    
    # Vérifier la présence de multiples gaps significatifs
    gray = cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2GRAY)
    row_means = gray.mean(axis=1)
    
    # Compter les zones blanches continues > 50px
    bright_lines = (row_means > 240)
    gap_count = 0
    in_gap = False
    gap_size = 0
    
    for is_bright in bright_lines:
        if is_bright:
            if not in_gap:
                in_gap = True
                gap_size = 1
            else:
                gap_size += 1
        else:
            if in_gap and gap_size >= 50:  # Gap significatif trouvé
                gap_count += 1
            in_gap = False
            gap_size = 0
    
    # Nécessite au moins 2 gaps significatifs pour découper
    should_slice = gap_count >= 2
    logging.info(f"ℹ️ {'Découpage activé' if should_slice else 'Image gardée entière'} ({gap_count} gaps ≥50px détectés)")
    
    return should_slice


def process_image_smart(image_bytes: bytes) -> List[Image.Image]:
    """
    🎯 POINT D'ENTRÉE PRINCIPAL V3
    
    Logique :
    1. Vérifier si découpage nécessaire (ratio + gaps)
    2. Si oui : découpage par scène narrative
    3. Si non : garder l'image entière
    """
    if should_slice_image(image_bytes):
        panels = detect_narrative_panels(image_bytes)
        return panels if panels else [trim_whitespace_smart(Image.open(io.BytesIO(image_bytes)))]
    else:
        return [trim_whitespace_smart(Image.open(io.BytesIO(image_bytes)))]