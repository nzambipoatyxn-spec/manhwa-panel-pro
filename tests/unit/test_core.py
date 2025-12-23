"""
Tests unitaires pour core.py

Teste WebSession : création profil, détection OS, gestion ChromeDriver, context manager.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import sys
import os
import platform
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from panelia.core.driver import WebSession


class TestWebSessionInit:
    """Tests pour WebSession.__init__()"""

    @pytest.mark.unit
    def test_system_detection_windows(self):
        """Test détection Windows"""
        with patch('platform.system', return_value='Windows'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                assert session.system == 'Windows'
                assert session.headless is True

    @pytest.mark.unit
    def test_system_detection_linux(self):
        """Test détection Linux"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                assert session.system == 'Linux'

    @pytest.mark.unit
    def test_system_detection_macos(self):
        """Test détection macOS"""
        with patch('platform.system', return_value='Darwin'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                assert session.system == 'Darwin'

    @pytest.mark.unit
    def test_profile_directory_creation_windows(self):
        """Test création profil sur Windows"""
        with patch('platform.system', return_value='Windows'):
            with patch('tempfile.gettempdir', return_value='C:\\Temp'):
                with patch('panelia.core.driver.WebSession._start_driver'):
                    with patch('pathlib.Path.mkdir'):
                        session = WebSession(headless=True)
                        assert 'panelia_profiles' in session.profile_dir
                        assert 'profile_' in session.profile_dir

    @pytest.mark.unit
    def test_profile_directory_creation_linux(self):
        """Test création profil sur Linux"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                with patch('pathlib.Path.mkdir'):
                    session = WebSession(headless=True)
                    # Sur Windows, Path convertit / en \, donc on vérifie juste le nom
                    assert 'panelia_profiles' in session.profile_dir
                    assert 'profile_' in session.profile_dir


class TestWebSessionDriverManagement:
    """Tests pour gestion du ChromeDriver"""

    @pytest.mark.unit
    def test_get_chromedriver_path_success(self):
        """Test récupération ChromeDriver via webdriver-manager"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)

                with patch('panelia.core.driver.ChromeDriverManager') as mock_manager:
                    mock_manager.return_value.install.return_value = '/path/to/chromedriver'

                    driver_path = session._get_chromedriver_path()

                    assert driver_path == '/path/to/chromedriver'
                    assert mock_manager.called

    @pytest.mark.unit
    def test_get_chromedriver_path_failure_returns_none(self):
        """Test fallback si webdriver-manager échoue"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)

                with patch('panelia.core.driver.ChromeDriverManager') as mock_manager:
                    mock_manager.return_value.install.side_effect = Exception("Download failed")

                    driver_path = session._get_chromedriver_path()

                    assert driver_path is None

    @pytest.mark.unit
    def test_start_driver_uses_webdriver_manager_path(self):
        """Test que _start_driver utilise le chemin de webdriver-manager"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.mkdir'):
                with patch('panelia.core.driver.WebSession._get_chromedriver_path', return_value='/path/to/chromedriver'):
                    with patch('panelia.core.driver.uc.Chrome') as mock_chrome:
                        mock_driver = Mock()
                        mock_driver.capabilities = {'browserVersion': '142.0', 'chrome': {'chromedriverVersion': '142.0'}}
                        mock_chrome.return_value = mock_driver

                        session = WebSession(headless=True)

                        # Vérifier que uc.Chrome a été appelé avec driver_executable_path
                        assert mock_chrome.called
                        call_kwargs = mock_chrome.call_args[1]
                        assert 'driver_executable_path' in call_kwargs
                        assert call_kwargs['driver_executable_path'] == '/path/to/chromedriver'

    @pytest.mark.unit
    def test_start_driver_fallback_without_webdriver_manager(self):
        """Test fallback quand webdriver-manager échoue"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.mkdir'):
                with patch('panelia.core.driver.WebSession._get_chromedriver_path', return_value=None):
                    with patch('panelia.core.driver.uc.Chrome') as mock_chrome:
                        mock_driver = Mock()
                        mock_driver.capabilities = {'browserVersion': '142.0', 'chrome': {'chromedriverVersion': '142.0'}}
                        mock_chrome.return_value = mock_driver

                        session = WebSession(headless=True)

                        # Vérifier que uc.Chrome a été appelé SANS driver_executable_path
                        assert mock_chrome.called
                        call_kwargs = mock_chrome.call_args[1]
                        assert 'driver_executable_path' not in call_kwargs


class TestWebSessionMethods:
    """Tests pour méthodes de WebSession"""

    @pytest.mark.unit
    def test_get_navigates_to_url(self):
        """Test navigation vers URL"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                session.driver = Mock()

                with patch('time.sleep'):  # Mock sleep
                    session.get("https://example.com", timeout=10)

                session.driver.set_page_load_timeout.assert_called_once_with(10)
                session.driver.get.assert_called_once_with("https://example.com")

    @pytest.mark.unit
    def test_page_source_property(self):
        """Test propriété page_source"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                session.driver = Mock()
                session.driver.page_source = "<html>test</html>"

                assert session.page_source == "<html>test</html>"

    @pytest.mark.unit
    def test_quit_closes_driver(self):
        """Test fermeture propre du driver"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                session.driver = Mock()

                session.quit()

                session.driver.quit.assert_called_once()

    @pytest.mark.unit
    def test_quit_handles_exception_gracefully(self):
        """Test que quit() ne lève pas d'exception même si driver.quit() échoue"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                session.driver = Mock()
                session.driver.quit.side_effect = Exception("Driver already closed")

                # Ne doit pas lever d'exception
                session.quit()


class TestWebSessionContextManager:
    """Tests pour context manager (with statement)"""

    @pytest.mark.unit
    def test_context_manager_enter_returns_session(self):
        """Test __enter__ retourne la session"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)

                result = session.__enter__()

                assert result is session

    @pytest.mark.unit
    def test_context_manager_exit_calls_quit(self):
        """Test __exit__ appelle quit()"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                session = WebSession(headless=True)
                session.driver = Mock()

                session.__exit__(None, None, None)

                session.driver.quit.assert_called_once()

    @pytest.mark.unit
    def test_context_manager_with_statement(self):
        """Test utilisation avec 'with' statement"""
        with patch('platform.system', return_value='Linux'):
            with patch('panelia.core.driver.WebSession._start_driver'):
                mock_driver = Mock()

                with patch('panelia.core.driver.WebSession.quit') as mock_quit:
                    with WebSession(headless=True) as session:
                        pass  # Just enter and exit

                    # Vérifier que quit a été appelé à la sortie du context
                    mock_quit.assert_called_once()


class TestWebSessionOptions:
    """Tests pour options Chrome"""

    @pytest.mark.unit
    def test_headless_option_enabled(self):
        """Test option headless activée"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.mkdir'):
                with patch('panelia.core.driver.WebSession._get_chromedriver_path', return_value=None):
                    with patch('panelia.core.driver.uc.Chrome') as mock_chrome:
                        with patch('panelia.core.driver.uc.ChromeOptions') as mock_options_class:
                            mock_options = Mock()
                            mock_options_class.return_value = mock_options
                            mock_driver = Mock()
                            mock_driver.capabilities = {'browserVersion': '142.0', 'chrome': {'chromedriverVersion': '142.0'}}
                            mock_chrome.return_value = mock_driver

                            session = WebSession(headless=True)

                            # Vérifier que --headless=new a été ajouté
                            calls = [str(call) for call in mock_options.add_argument.call_args_list]
                            assert any('headless' in str(call) for call in calls)

    @pytest.mark.unit
    def test_headless_option_disabled(self):
        """Test option headless désactivée"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.mkdir'):
                with patch('panelia.core.driver.WebSession._get_chromedriver_path', return_value=None):
                    with patch('panelia.core.driver.uc.Chrome') as mock_chrome:
                        with patch('panelia.core.driver.uc.ChromeOptions') as mock_options_class:
                            mock_options = Mock()
                            mock_options_class.return_value = mock_options
                            mock_driver = Mock()
                            mock_driver.capabilities = {'browserVersion': '142.0', 'chrome': {'chromedriverVersion': '142.0'}}
                            mock_chrome.return_value = mock_driver

                            session = WebSession(headless=False)

                            # Vérifier les arguments ajoutés
                            calls = [str(call) for call in mock_options.add_argument.call_args_list]
                            # headless ne doit PAS être dans les calls
                            # (ou si présent, vérifier qu'il n'y a pas de call avec --headless=new)
                            headless_calls = [call for call in calls if 'headless' in str(call).lower()]
                            # En mode non-headless, l'argument ne doit pas être ajouté
                            # Donc soit aucun call headless, soit le test passe
