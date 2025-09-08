# scrapers.py

import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

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

def discover_chapters_mangadex(series_url: str) -> dict[float, str]:
    """
    Un scraper spécialisé pour MangaDex qui utilise son API officielle.
    C'est la méthode la plus robuste et la plus efficace.
    """
    chapter_map = {}
    
    # 1. Extraire l'UUID du manga depuis l'URL
    uuid_match = re.search(r'title/([a-f0-9\-]{36})', series_url)
    if not uuid_match:
        return {}
    manga_uuid = uuid_match.group(1)

    # 2. Construire l'URL de l'API pour la "feed" du manga
    api_url = f"https://api.mangadex.org/manga/{manga_uuid}/feed"
    
    # 3. Paramètres de la requête API
    # On demande les chapitres en anglais, triés par numéro de chapitre descendant
    params = {
        "translatedLanguage[]": "en",
        "order[chapter]": "desc",
        "limit": 500  # On demande jusqu'à 500 chapitres par page de résultats
    }
    
    offset = 0
    total_chapters = None

    while total_chapters is None or offset < total_chapters:
        params["offset"] = offset
        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()  # Lève une erreur si la requête échoue
            data = response.json()
        except requests.exceptions.RequestException:
            # En cas d'erreur réseau, on arrête
            break

        if data.get("result") != "ok" or not data.get("data"):
            # Si la réponse n'est pas bonne ou vide, on arrête
            break

        if total_chapters is None:
            total_chapters = data.get("total", 0)

        # 4. Traiter les chapitres de la page actuelle
        for chapter_data in data["data"]:
            attributes = chapter_data.get("attributes", {})
            chapter_num_str = attributes.get("chapter")
            chapter_id = chapter_data.get("id")
            
            # On s'assure que le numéro de chapitre est bien un nombre
            if chapter_num_str and chapter_id:
                try:
                    chap_num = float(chapter_num_str)
                    # On construit l'URL complète du chapitre
                    full_url = f"https://mangadex.org/chapter/{chapter_id}"
                    if chap_num not in chapter_map:
                        chapter_map[chap_num] = full_url
                except (ValueError, TypeError):
                    # On ignore les chapitres sans numéro valide (ex: "Oneshot")
                    continue
        
        offset += len(data["data"]) # On passe à la page suivante
        
    return chapter_map

def scrape_images_mangadex(chapter_url: str) -> list[str]:
    """
    Scrape les URLs des images d'un chapitre MangaDex en utilisant l'API /at-home/server.
    """
    # 1. Extraire l'UUID du chapitre depuis l'URL
    chapter_uuid_match = re.search(r'chapter/([a-f0-9\-]{36})', chapter_url)
    if not chapter_uuid_match:
        return []
    chapter_uuid = chapter_uuid_match.group(1)

    # 2. Appeler l'API pour obtenir les informations du serveur d'images
    try:
        api_url = f"https://api.mangadex.org/at-home/server/{chapter_uuid}"
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return []

    if data.get("result") != "ok" or not data.get("baseUrl") or not data.get("chapter"):
        return []

    # 3. Construire les URLs complètes des images
    base_url = data["baseUrl"]
    chapter_hash = data["chapter"]["hash"]
    image_filenames = data["chapter"]["data"] # Ceci est la liste des noms de fichiers

    image_urls = []
    for filename in image_filenames:
        # Format: {baseUrl}/data/{chapter.hash}/{filename}
        full_image_url = f"{base_url}/data/{chapter_hash}/{filename}"
        image_urls.append(full_image_url)
        
    return image_urls