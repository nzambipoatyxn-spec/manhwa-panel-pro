# scrapers.py

import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def discover_chapters_asuracomic(page_html: str, series_url: str) -> dict[float, str]:
    """
    Un scraper spécialisé pour découvrir les chapitres sur des sites ayant une structure
    similaire à asuracomic.net (anciennement asurascans).

    Il recherche des balises <a> dont le href contient '/chapter/'.
    """
    soup = BeautifulSoup(page_html, 'html.parser')
    chapter_map = {}
    
    # On cible toutes les balises <a> qui contiennent un lien vers un chapitre.
    # C'est une méthode plus robuste que de se baser sur des classes CSS.
    chapter_links = soup.find_all('a', href=re.compile(r'/chapter/'))

    for link in chapter_links:
        href = link.get('href')
        if not href:
            continue

        # Le texte peut contenir le numéro de chapitre, ex: "Chapter 53"
        text = link.text.strip()
        match = re.search(r'Chapter\s*([\d\.]+)', text, re.IGNORECASE)
        
        if match:
            try:
                chap_num = float(match.group(1))
                full_url = urljoin(series_url, href)
                
                # On évite les doublons en ne gardant que le premier lien trouvé pour un chapitre
                if chap_num not in chapter_map:
                    chapter_map[chap_num] = full_url
            except (ValueError, IndexError):
                # On ignore les cas où le numéro n'est pas un nombre valide
                continue
                
    return chapter_map


def discover_chapters_resetscans(page_html: str, series_url: str) -> dict[float, str]:
    """
    Un scraper spécialisé pour découvrir les chapitres sur des sites basés sur le thème
    WordPress Madara (comme reset-scans.org).

    Il recherche des balises <li> avec la classe 'wp-manga-chapter'.
    """
    soup = BeautifulSoup(page_html, 'html.parser')
    chapter_map = {}
    
    # On cible toutes les balises <li> qui représentent un chapitre.
    # C'est la méthode la plus fiable pour ce type de site.
    chapter_list_items = soup.find_all('li', class_='wp-manga-chapter')

    for item in chapter_list_items:
        link_tag = item.find('a')
        if not link_tag:
            continue
            
        href = link_tag.get('href')
        text = link_tag.text.strip()
        
        # On extrait le numéro de chapitre du texte (ex: "Chapter 24")
        match = re.search(r'Chapter\s*([\d\.]+)', text, re.IGNORECASE)
        
        if href and match:
            try:
                chap_num = float(match.group(1))
                
                # L'URL est déjà absolue, pas besoin de urljoin
                full_url = href.strip()
                
                if chap_num not in chapter_map:
                    chapter_map[chap_num] = full_url
            except (ValueError, IndexError):
                continue
                
    return chapter_map

def discover_chapters_ravenscans(page_html: str, series_url: str) -> dict[float, str]:
    """
    Un scraper spécialisé pour découvrir les chapitres sur des sites ayant une structure
    similaire à ravenscans.com.

    Il recherche des balises <span> avec la classe 'chapternum' à l'intérieur d'un <div id="chapterlist">.
    """
    soup = BeautifulSoup(page_html, 'html.parser')
    chapter_map = {}
    
    # On cible d'abord le conteneur principal pour être plus précis
    chapter_list_container = soup.find('div', id='chapterlist')
    
    if not chapter_list_container:
        return {} # On ne trouve pas le conteneur, on renvoie un dictionnaire vide

    # On trouve tous les éléments de chapitre à l'intérieur du conteneur
    chapter_items = chapter_list_container.find_all('li')

    for item in chapter_items:
        link_tag = item.find('a')
        chapter_span = item.find('span', class_='chapternum')

        if link_tag and chapter_span:
            href = link_tag.get('href')
            text = chapter_span.text.strip()
            
            # On utilise une regex pour extraire proprement le numéro
            match = re.search(r'([\d\.]+)', text, re.IGNORECASE)
            
            if href and match:
                try:
                    chap_num = float(match.group(1))
                    full_url = href.strip() # Les liens sont déjà absolus
                    
                    if chap_num not in chapter_map:
                        chapter_map[chap_num] = full_url
                except (ValueError, IndexError):
                    continue
                    
    return chapter_map