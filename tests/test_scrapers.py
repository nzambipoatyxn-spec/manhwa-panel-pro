# tests/test_scrapers.py

# On importe la fonction spécifique qu'on veut tester
from scrapers import discover_chapters_resetscans

def test_discover_chapters_for_resetscans():
    """
    Ce test vérifie si notre scraper pour Reset Scans fonctionne correctement
    sur un échantillon de code HTML.
    """
    # ARRANGE : On prépare les données.
    # Au lieu de visiter le site à chaque fois, on utilise un extrait de son HTML.
    # C'est plus rapide et plus fiable.
    mock_html = """
    <html>
        <body>
            <div class="page-content-listing single-page">
                <ul class="main version-chap">
                    <li class="wp-manga-chapter">
                        <a href="https://reset-scans.org/manga/brawl-dad/chapter-24/">
                            Chapter 24
                        </a>
                    </li>
                    <li class="wp-manga-chapter">
                        <a href="https://reset-scans.org/manga/brawl-dad/chapter-23/">
                            Chapter 23
                        </a>
                    </li>
                    <li class="wp-manga-chapter">
                        <a href="https://reset-scans.org/manga/brawl-dad/chapter-22/">
                            Chapter 22
                        </a>
                    </li>
                    <li>
                        <a href="/autre-page/">Un lien quelconque</a>
                    </li>
                </ul>
            </div>
        </body>
    </html>
    """
    series_url = "https://reset-scans.org/manga/brawl-dad/"

    # On définit le résultat qu'on s'attend à obtenir
    expected_chapters = {
        24.0: "https://reset-scans.org/manga/brawl-dad/chapter-24/",
        23.0: "https://reset-scans.org/manga/brawl-dad/chapter-23/",
        22.0: "https://reset-scans.org/manga/brawl-dad/chapter-22/",
    }

    # ACT : On exécute la fonction qu'on teste.
    result = discover_chapters_resetscans(mock_html, series_url)

    # ASSERT : On vérifie que le résultat est bien celui attendu.
    # Si une de ces affirmations est fausse, le test échouera.
    assert len(result) == 3  # On vérifie qu'on a bien trouvé 3 chapitres
    assert result == expected_chapters # On vérifie que le dictionnaire est identique
    assert 24.0 in result # On vérifie la présence d'une clé spécifique
    assert result[22.0] == "https://reset-scans.org/manga/brawl-dad/chapter-22/" # On vérifie une valeur spécifique