"""
Tests unitaires pour http_utils.py

Teste les fonctions de téléchargement HTTP avec retry, backoff et rotation User-Agent.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from http_utils import download_image_smart, download_all_images, USER_AGENTS


class TestDownloadImageSmart:
    """Tests pour download_image_smart()"""

    @pytest.mark.unit
    def test_download_success_first_attempt(self):
        """Test téléchargement réussi du premier coup"""
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status = Mock()

        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = download_image_smart("http://example.com/image.jpg", timeout=10)

            assert result == b"fake_image_data"
            assert mock_client.get.call_count == 1

    @pytest.mark.unit
    def test_download_returns_none_on_max_retries(self):
        """Test échec après épuisement des tentatives"""
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client_class.return_value = mock_client

            with patch('time.sleep'):  # Mock sleep pour accélérer
                result = download_image_smart("http://example.com/image.jpg", timeout=10)

            assert result is None
            assert mock_client.get.call_count == 4  # max_retries = 4

    @pytest.mark.unit
    def test_download_with_referer(self):
        """Test que le referer est bien passé"""
        mock_response = Mock()
        mock_response.content = b"image_data"
        mock_response.raise_for_status = Mock()

        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = download_image_smart(
                "http://example.com/image.jpg",
                referer="http://example.com/chapter/1",
                timeout=10
            )

            assert result == b"image_data"
            # Vérifier headers Referer
            call_kwargs = mock_client_class.call_args[1]
            assert 'Referer' in call_kwargs['headers']

    @pytest.mark.unit
    def test_user_agent_in_headers(self):
        """Test que User-Agent est utilisé"""
        mock_response = Mock()
        mock_response.content = b"data"
        mock_response.raise_for_status = Mock()

        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            download_image_smart("http://example.com/image.jpg", timeout=10)

            call_kwargs = mock_client_class.call_args[1]
            used_ua = call_kwargs['headers']['User-Agent']
            assert used_ua in USER_AGENTS


class TestDownloadAllImages:
    """Tests pour download_all_images()"""

    @pytest.mark.unit
    def test_download_multiple_images_success(self):
        """Test téléchargement de plusieurs images en parallèle"""
        urls = [
            "http://example.com/img1.jpg",
            "http://example.com/img2.jpg",
            "http://example.com/img3.jpg"
        ]

        with patch('http_utils.download_image_smart') as mock_download:
            mock_download.side_effect = [b"img1", b"img2", b"img3"]

            results = download_all_images(urls, chapter_num=1, timeout=10, max_workers=2)

            assert len(results) == 3
            assert mock_download.call_count == 3

    @pytest.mark.unit
    def test_download_filters_failed_images(self):
        """Test que les images échouées (None) sont filtrées"""
        urls = ["http://example.com/img1.jpg", "http://example.com/img2.jpg"]

        with patch('http_utils.download_image_smart') as mock_download:
            mock_download.side_effect = [b"img1", None]  # img2 échoue

            results = download_all_images(urls, timeout=10)

            assert len(results) == 1
            assert b"img1" in results

    @pytest.mark.unit
    def test_download_empty_urls_list(self):
        """Test avec liste vide"""
        results = download_all_images([], timeout=10)
        assert results == []


@pytest.mark.unit
def test_user_agents_list_not_empty():
    """Test que USER_AGENTS contient des agents"""
    assert len(USER_AGENTS) > 0
    assert all(isinstance(ua, str) for ua in USER_AGENTS)
    assert all("Mozilla" in ua for ua in USER_AGENTS)
