# sites_config.py
# Ce fichier contient la configuration des sites supportés par PANELia.
# Pour ajouter un nouveau site, ajoutez simplement une ligne dans le dictionnaire ci-dessous.

from scrapers import (
    discover_chapters_madara_theme,
    discover_chapters_asuracomic,
    discover_chapters_mangadex,
    discover_chapters_flamecomics,
    discover_chapters_raijin_scans
)

SUPPORTED_SITES = {
    # (domaine, (fonction_scraper, needs_selenium))
    "mangadex.org": (discover_chapters_mangadex, False),
    "flamecomics.xyz": (discover_chapters_flamecomics, True),
    "asuracomic.net": (discover_chapters_asuracomic, True),
    "asurascans.com": (discover_chapters_asuracomic, True),
    # Sites Madara (exemples)
    "reaperscans.com": (discover_chapters_madara_theme, True),
    "luminousscans.com": (discover_chapters_madara_theme, True),
    "arenascan.com": (discover_chapters_madara_theme, True),
    "raijin-scans.fr": (discover_chapters_raijin_scans, True),
    "manhuaus.com": (discover_chapters_madara_theme, True),

}