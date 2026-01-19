# sites_config.py - v1.0 Final
from panelia.scrapers.factory import (
    discover_chapters_madara_theme,
    discover_chapters_asuracomic,
    discover_chapters_mangadex,
    discover_chapters_flamecomics,
    discover_chapters_raijin_scans
)

SUPPORTED_SITES = {
    # (domaine, (fonction_scraper, needs_selenium, allow_driverless))
    "mangadex.org": (discover_chapters_mangadex, False, True),
    "flamecomics.xyz": (discover_chapters_flamecomics, True, False),
    "asuracomic.net": (discover_chapters_asuracomic, True, False),
    "asurascans.com": (discover_chapters_asuracomic, True, False),
    "reaperscans.com": (discover_chapters_madara_theme, True, False),
    "luminousscans.com": (discover_chapters_madara_theme, True, False),
    "arenascan.com": (discover_chapters_madara_theme, True, False),
    "raijin-scans.fr": (discover_chapters_raijin_scans, True, False),
    "manhuaus.com": (discover_chapters_madara_theme, True, False),
    "mangas-origines.fr": (discover_chapters_madara_theme, True, False),
    "manga-scantrad.io": (discover_chapters_madara_theme, True, False),
}