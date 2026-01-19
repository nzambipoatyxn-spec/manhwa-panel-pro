import pytest
import numpy as np
from PIL import Image
import io
import sys
import os

# Ajouter le répertoire racine au path pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from panelia.scrapers.factory import trim_borders_smart

@pytest.mark.unit
def test_trim_white_borders():
    """Test le recadrage sur fond blanc."""
    # Créer une image 100x100 blanche avec un carré rouge 20x20 au milieu (40,40)
    img = Image.new('RGB', (100, 100), color='white')
    for x in range(40, 60):
        for y in range(40, 60):
            img.putpixel((x, y), (255, 0, 0))
    
    # Avec un padding de 2, la boîte doit être (38, 38, 62, 62)
    trimmed = trim_borders_smart(img, padding=2)
    
    assert trimmed.width == 24 # 20 + 2*2
    assert trimmed.height == 24
    # Vérifier que le coin est bien blanc (padding)
    assert trimmed.getpixel((0, 0)) == (255, 255, 255)
    # Vérifier que le centre est rouge
    assert trimmed.getpixel((12, 12)) == (255, 0, 0)

@pytest.mark.unit
def test_trim_black_borders():
    """Test le recadrage sur fond noir."""
    # Créer une image 100x100 noire avec un carré rouge 20x20 au milieu (40,40)
    img = Image.new('RGB', (100, 100), color='black')
    for x in range(40, 60):
        for y in range(40, 60):
            img.putpixel((x, y), (255, 0, 0))
    
    trimmed = trim_borders_smart(img, padding=2)
    
    assert trimmed.width == 24
    assert trimmed.height == 24
    # Vérifier que le coin est noir
    assert trimmed.getpixel((0, 0)) == (0, 0, 0)
    # Vérifier que le centre est rouge
    assert trimmed.getpixel((12, 12)) == (255, 0, 0)

@pytest.mark.unit
def test_trim_no_content():
    """Test sur une image unie (ne doit pas crasher)."""
    img = Image.new('RGB', (50, 50), color='white')
    trimmed = trim_borders_smart(img)
    assert trimmed.size == (50, 50)

@pytest.mark.unit
def test_trim_already_tight():
    """Test sur une image déjà serrée."""
    img = Image.new('RGB', (10, 10), color='red')
    trimmed = trim_borders_smart(img, padding=0)
    assert trimmed.size == (10, 10)
