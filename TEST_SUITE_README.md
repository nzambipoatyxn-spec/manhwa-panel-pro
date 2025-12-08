# 🧪 Suite de Tests PANELia v2.0

## Vue d'ensemble

Cette suite de tests offre une couverture complète de PANELia avec 3 niveaux :
1. **Tests unitaires** : Fonctions isolées, rapides
2. **Tests d'intégration** : Modules complets, interaction entre composants
3. **Tests end-to-end** : Workflow complet (optionnel, nécessite réseau)

---

## Structure

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_http_utils.py          # Tests téléchargements HTTP
│   ├── test_scrapers.py             # Tests scrapers individuels
│   ├── test_core.py                 # Tests WebSession
│   └── test_image_processing.py    # Tests découpage panels
├── integration/
│   ├── __init__.py
│   ├── test_scraper_engine.py      # Tests moteur complet
│   └── test_full_workflow.py       # Tests workflow complet
└── fixtures/
    ├── sample_html/
    │   ├── madara_chapters.html
    │   ├── asura_chapters.html
    │   └── mangadex_chapters.json
    └── sample_images/
        ├── test_image_3_panels.jpg
        └── test_image_1_panel.jpg
```

---

## Commandes

### Lancer tous les tests
```bash
pytest
```

### Tests unitaires uniquement (rapides)
```bash
pytest -m unit
```

### Tests avec coverage
```bash
pytest --cov=. --cov-report=html
```

### Tests d'un seul fichier
```bash
pytest tests/unit/test_http_utils.py -v
```

### Tests d'une seule fonction
```bash
pytest tests/unit/test_http_utils.py::TestDownloadImageSmart::test_download_success_first_attempt -v
```

---

## Markers disponibles

```python
@pytest.mark.unit              # Tests unitaires rapides
@pytest.mark.integration       # Tests d'intégration (lents)
@pytest.mark.slow              # Tests nécessitant réseau/Selenium
@pytest.mark.requires_chrome   # Tests nécessitant Chrome
@pytest.mark.requires_network  # Tests nécessitant internet
```

### Exclure les tests lents
```bash
pytest -m "not slow"
```

---

## État actuel de la couverture

**Date : 2025-12-03**
**Tests passés : 26/26 (100%)** ✅
**Coverage globale : 31%** ⬆️

| Module | Tests | Coverage | Statut |
|--------|-------|----------|--------|
| `http_utils.py` | ✅ 8 tests | **100%** | ✅ Complet |
| `core.py` | ✅ 18 tests | **65%** | ✅ Bon |
| `scrapers.py` | ❌ 0 tests | 0% | À faire |
| `scraper_engine.py` | ❌ 0 tests | 0% | À faire |
| `app.py` | ❌ 0 tests | 0% | À faire |

### Objectif actuel : 50% de couverture (en cours)
### Objectif final : 70% de couverture minimum

---

## Tests prioritaires à implémenter

### 1. `test_http_utils.py` ✅ (FAIT - 8 tests, 100% coverage)
- [x] Téléchargement réussi
- [x] Retry avec backoff
- [x] Rotation User-Agent
- [x] HTTP/2 → HTTP/1.1 fallback
- [x] Referer headers
- [x] Téléchargement multiple parallèle
- [x] Gestion erreurs (None on failure)
- [x] Liste vide

### 2. `test_core.py` ✅ (FAIT - 18 tests, 65% coverage)
- [x] Détection système (Windows/Linux/macOS)
- [x] Création profil Chrome multi-plateforme
- [x] Récupération ChromeDriver via webdriver-manager
- [x] Fallback si webdriver-manager échoue
- [x] Navigation vers URL
- [x] Propriété page_source
- [x] Fermeture propre du driver
- [x] Context manager (__enter__/__exit__)
- [x] Options headless/non-headless

### 3. `test_scrapers.py` (À FAIRE)
- [ ] `discover_chapters_madara_theme()` avec HTML mocké
- [ ] `discover_chapters_asuracomic()` avec HTML mocké
- [ ] `discover_chapters_mangadex()` avec JSON mocké
- [ ] `scrape_images_smart()` routing
- [ ] `slice_panels_precision()` avec images de test
- [ ] `process_image_smart()` traitement complet

### 3. `test_core.py` (À FAIRE)
- [ ] `WebSession.__init__()` création profil
- [ ] Détection multi-plateforme (Windows/Linux/macOS)
- [ ] ChromeDriver via webdriver-manager
- [ ] Fallback si webdriver-manager échoue
- [ ] Context manager (`with WebSession()`)

### 4. `test_scraper_engine.py` (À FAIRE)
- [ ] `ScraperEngine.start_driver_pool()` création drivers
- [ ] `ScraperEngine._process_single_chapter()` chapitre complet
- [ ] `ScraperEngine.run_chapter_batch()` parallélisation
- [ ] Throttling et rate limiting
- [ ] Callbacks UI

---

## Exemples de tests

### Test unitaire simple
```python
@pytest.mark.unit
def test_download_success():
    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value.content = b"data"
        result = download_image_smart("http://test.com/img.jpg")
        assert result == b"data"
```

### Test avec fixture
```python
@pytest.fixture
def sample_html():
    return Path("tests/fixtures/sample_html/madara_chapters.html").read_text()

@pytest.mark.unit
def test_discover_madara(sample_html):
    result = discover_chapters_madara_theme(sample_html, "http://test.com")
    assert len(result) > 0
```

### Test d'intégration
```python
@pytest.mark.integration
@pytest.mark.slow
def test_full_chapter_download():
    engine = ScraperEngine(num_drivers=1)
    chapters = {1.0: "http://mangadex.org/chapter/..."}
    results = engine.run_chapter_batch(chapters, {})
    assert len(results) == 1
    assert results[0]['panels_saved'] > 0
```

---

## CI/CD avec GitHub Actions

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest -m "not slow" --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## Prochaines étapes

1. ✅ Créer structure des tests
2. ✅ Configurer pytest
3. ✅ Implémenter tests http_utils
4. ⏳ Implémenter tests scrapers
5. ⏳ Implémenter tests core
6. ⏳ Implémenter tests scraper_engine
7. ⏳ Atteindre 70% couverture
8. ⏳ Configurer CI/CD

---

## Ressources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)

*Dernière mise à jour : 2025-12-03*
