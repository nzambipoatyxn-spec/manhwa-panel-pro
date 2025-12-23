# validation.py
"""
Module de validation des entrées utilisateur PANELia

Valide toutes les entrées utilisateur pour éviter :
- Injections malveillantes
- Valeurs invalides
- Erreurs silencieuses
- Path traversal
- XSS (si applicable)

Auteur: PANELia Team
Date: 2025-12-08
"""

import re
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
from urllib.parse import urlparse
from loguru import logger


class ValidationError(Exception):
    """Exception levée lors d'une validation échouée."""
    pass


class InputValidator:
    """
    Validateur central pour toutes les entrées utilisateur.

    Usage:
        validator = InputValidator()
        url = validator.validate_url("https://example.com")
        chapter_num = validator.validate_chapter_number(1.5)
    """

    # Domaines supportés (whitelist)
    SUPPORTED_DOMAINS = [
        "mangadex.org",
        "flamecomics.com",
        "asuracomic.net",
        "asura.gg",
        "asuratoon.com",
        "raijin-scans.fr",
        "arenascan.com",
        "mangas-origines.fr",
        "reaperscans.com",
        "zeroscans.com",
        "luminousscans.com",
        "flamecomics.xyz"
    ]

    # Patterns dangereux pour path traversal
    DANGEROUS_PATH_PATTERNS = [
        r"\.\.",  # Path traversal
        r"~",     # Home directory
        r"\$",    # Variables
        r";",     # Command injection
        r"\|",    # Pipe
        r"&",     # Background execution
        r"`",     # Command substitution
        r"\n",    # Newline injection
        r"\r",    # Carriage return
    ]

    def __init__(self):
        """Initialise le validateur."""
        logger.debug("InputValidator initialisé")

    def validate_url(self, url: str, allow_any_domain: bool = False) -> str:
        """
        Valide une URL de manhwa/manga.

        Args:
            url: URL à valider
            allow_any_domain: Si True, accepte tous les domaines (fallback mode)

        Returns:
            URL validée et nettoyée

        Raises:
            ValidationError: Si l'URL est invalide
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL vide ou invalide")

        # Nettoyer les espaces
        url = url.strip()

        # Vérifier longueur (éviter DoS)
        if len(url) > 2048:
            raise ValidationError("URL trop longue (max 2048 caractères)")

        # Parser l'URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValidationError(f"URL malformée : {e}")

        # Vérifier schéma
        if parsed.scheme not in ["http", "https"]:
            raise ValidationError(f"Schéma invalide : {parsed.scheme}. Utilisez http ou https")

        # Vérifier domaine
        if not parsed.netloc:
            raise ValidationError("Domaine manquant dans l'URL")

        # Whitelist domaines (sauf si allow_any_domain)
        if not allow_any_domain:
            domain_valid = False
            for supported_domain in self.SUPPORTED_DOMAINS:
                if supported_domain in parsed.netloc:
                    domain_valid = True
                    break

            if not domain_valid:
                logger.warning(f"Domaine non supporté : {parsed.netloc}")
                # Ne pas lever d'exception, juste logger
                # Permet le fallback mode

        # Reconstruire URL propre
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean_url += f"?{parsed.query}"

        logger.debug(f"URL validée : {clean_url}")
        return clean_url

    def validate_chapter_number(self, chapter_num: Any) -> float:
        """
        Valide un numéro de chapitre.

        Args:
            chapter_num: Numéro de chapitre (int, float, ou str)

        Returns:
            Numéro de chapitre validé (float)

        Raises:
            ValidationError: Si le numéro est invalide
        """
        # Convertir en float
        try:
            num = float(chapter_num)
        except (ValueError, TypeError):
            raise ValidationError(f"Numéro de chapitre invalide : {chapter_num}")

        # Vérifier plage raisonnable
        if num < 0:
            raise ValidationError(f"Numéro de chapitre négatif : {num}")

        if num > 10000:
            raise ValidationError(f"Numéro de chapitre trop élevé : {num} (max 10000)")

        logger.debug(f"Numéro de chapitre validé : {num}")
        return num

    def validate_chapter_range(self, start: Any, end: Any) -> Tuple[float, float]:
        """
        Valide une plage de chapitres.

        Args:
            start: Chapitre de début
            end: Chapitre de fin

        Returns:
            Tuple (start, end) validé

        Raises:
            ValidationError: Si la plage est invalide
        """
        start_num = self.validate_chapter_number(start)
        end_num = self.validate_chapter_number(end)

        if start_num > end_num:
            raise ValidationError(
                f"Plage invalide : début ({start_num}) > fin ({end_num})"
            )

        # Vérifier taille de la plage (éviter surcharge)
        range_size = end_num - start_num + 1
        if range_size > 1000:
            logger.warning(f"Plage très large : {range_size} chapitres")
            # Ne pas bloquer, juste avertir

        logger.debug(f"Plage validée : {start_num} à {end_num} ({range_size} chapitres)")
        return start_num, end_num

    def validate_quality(self, quality: Any) -> int:
        """
        Valide un paramètre de qualité JPEG.

        Args:
            quality: Qualité JPEG (70-100)

        Returns:
            Qualité validée (int)

        Raises:
            ValidationError: Si la qualité est invalide
        """
        try:
            qual = int(quality)
        except (ValueError, TypeError):
            raise ValidationError(f"Qualité invalide : {quality}")

        if qual < 1 or qual > 100:
            raise ValidationError(f"Qualité hors plage : {qual} (doit être 1-100)")

        if qual < 70:
            logger.warning(f"Qualité basse : {qual}%")

        logger.debug(f"Qualité validée : {qual}%")
        return qual

    def validate_min_width(self, width: Any) -> int:
        """
        Valide une largeur minimale d'image.

        Args:
            width: Largeur en pixels

        Returns:
            Largeur validée (int)

        Raises:
            ValidationError: Si la largeur est invalide
        """
        try:
            w = int(width)
        except (ValueError, TypeError):
            raise ValidationError(f"Largeur invalide : {width}")

        if w < 50:
            raise ValidationError(f"Largeur trop petite : {w}px (min 50px)")

        if w > 5000:
            raise ValidationError(f"Largeur trop grande : {w}px (max 5000px)")

        logger.debug(f"Largeur minimale validée : {w}px")
        return w

    def validate_timeout(self, timeout: Any) -> int:
        """
        Valide un timeout en secondes.

        Args:
            timeout: Timeout en secondes

        Returns:
            Timeout validé (int)

        Raises:
            ValidationError: Si le timeout est invalide
        """
        try:
            t = int(timeout)
        except (ValueError, TypeError):
            raise ValidationError(f"Timeout invalide : {timeout}")

        if t < 1:
            raise ValidationError(f"Timeout trop court : {t}s (min 1s)")

        if t > 300:
            raise ValidationError(f"Timeout trop long : {t}s (max 300s)")

        logger.debug(f"Timeout validé : {t}s")
        return t

    def validate_filename(self, filename: str, allow_path: bool = False) -> str:
        """
        Valide un nom de fichier.

        Args:
            filename: Nom de fichier à valider
            allow_path: Si True, accepte les chemins (avec /)

        Returns:
            Nom de fichier validé et nettoyé

        Raises:
            ValidationError: Si le nom est invalide ou dangereux
        """
        if not filename or not isinstance(filename, str):
            raise ValidationError("Nom de fichier vide")

        # Nettoyer
        filename = filename.strip()

        # Vérifier longueur
        if len(filename) > 255:
            raise ValidationError(f"Nom de fichier trop long : {len(filename)} (max 255)")

        # Détecter patterns dangereux
        for pattern in self.DANGEROUS_PATH_PATTERNS:
            if re.search(pattern, filename):
                raise ValidationError(f"Pattern dangereux détecté dans : {filename}")

        # Si paths non autorisés, vérifier absence de /
        if not allow_path and ("/" in filename or "\\" in filename):
            raise ValidationError(f"Chemin non autorisé : {filename}")

        # Nettoyer caractères dangereux
        # Garder uniquement alphanum, -, _, ., espaces, et / si allow_path
        if allow_path:
            safe_chars = r'[\w\-\.\s/]'
        else:
            safe_chars = r'[\w\-\.\s]'

        cleaned = re.sub(f'[^{safe_chars}]', '', filename)

        if not cleaned:
            raise ValidationError("Nom de fichier invalide après nettoyage")

        logger.debug(f"Nom de fichier validé : {cleaned}")
        return cleaned

    def validate_output_directory(self, directory: str) -> Path:
        """
        Valide un répertoire de sortie.

        Args:
            directory: Chemin du répertoire

        Returns:
            Path validé et résolu

        Raises:
            ValidationError: Si le chemin est dangereux
        """
        if not directory or not isinstance(directory, str):
            raise ValidationError("Répertoire vide")

        # Détecter patterns dangereux
        for pattern in self.DANGEROUS_PATH_PATTERNS:
            if re.search(pattern, directory):
                raise ValidationError(f"Pattern dangereux dans le chemin : {directory}")

        # Convertir en Path
        try:
            path = Path(directory)
        except Exception as e:
            raise ValidationError(f"Chemin invalide : {e}")

        # Résoudre le chemin absolu (détecte ..)
        try:
            resolved_path = path.resolve()
        except Exception as e:
            raise ValidationError(f"Impossible de résoudre le chemin : {e}")

        # Vérifier que le chemin résolu est bien dans output/
        cwd = Path.cwd()
        expected_base = cwd / "output"

        try:
            # relative_to lève ValueError si pas sous expected_base
            resolved_path.relative_to(expected_base)
        except ValueError:
            raise ValidationError(
                f"Chemin de sortie hors de output/ : {resolved_path}"
            )

        logger.debug(f"Répertoire de sortie validé : {resolved_path}")
        return resolved_path

    def validate_num_drivers(self, num_drivers: Any) -> int:
        """
        Valide le nombre de drivers Selenium.

        Args:
            num_drivers: Nombre de drivers

        Returns:
            Nombre validé (int)

        Raises:
            ValidationError: Si invalide
        """
        try:
            n = int(num_drivers)
        except (ValueError, TypeError):
            raise ValidationError(f"Nombre de drivers invalide : {num_drivers}")

        if n < 1:
            raise ValidationError(f"Au moins 1 driver requis : {n}")

        if n > 10:
            logger.warning(f"Nombre de drivers élevé : {n}")
            # Pas de blocage, juste avertissement

        logger.debug(f"Nombre de drivers validé : {n}")
        return n

    def validate_max_workers(self, workers: Any) -> int:
        """
        Valide le nombre de workers (threads).

        Args:
            workers: Nombre de workers

        Returns:
            Nombre validé (int)

        Raises:
            ValidationError: Si invalide
        """
        try:
            w = int(workers)
        except (ValueError, TypeError):
            raise ValidationError(f"Nombre de workers invalide : {workers}")

        if w < 1:
            raise ValidationError(f"Au moins 1 worker requis : {w}")

        if w > 20:
            logger.warning(f"Nombre de workers élevé : {w}")

        logger.debug(f"Nombre de workers validé : {w}")
        return w

    def validate_params_dict(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide un dictionnaire de paramètres complet.

        Args:
            params: Dictionnaire de paramètres

        Returns:
            Dictionnaire validé avec valeurs nettoyées

        Raises:
            ValidationError: Si un paramètre est invalide
        """
        if not isinstance(params, dict):
            raise ValidationError("Paramètres doivent être un dictionnaire")

        validated = {}

        # Validation conditionnelle selon les clés présentes
        if "min_image_width_value" in params:
            validated["min_image_width_value"] = self.validate_min_width(
                params["min_image_width_value"]
            )

        if "quality_value" in params:
            validated["quality_value"] = self.validate_quality(
                params["quality_value"]
            )

        if "timeout_value" in params:
            validated["timeout_value"] = self.validate_timeout(
                params["timeout_value"]
            )

        if "final_manhwa_name" in params:
            validated["final_manhwa_name"] = self.validate_filename(
                params["final_manhwa_name"],
                allow_path=False
            )

        # Copier les autres paramètres non validés (logs, etc.)
        for key, value in params.items():
            if key not in validated:
                validated[key] = value

        logger.debug(f"Paramètres validés : {len(validated)} clés")
        return validated


# Instance globale (singleton)
_global_validator: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """
    Retourne l'instance globale du validateur.

    Returns:
        InputValidator: Instance singleton
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = InputValidator()
    return _global_validator


# Fonctions utilitaires pour validation rapide

def validate_url(url: str, allow_any_domain: bool = False) -> str:
    """Valide une URL (fonction utilitaire)."""
    return get_validator().validate_url(url, allow_any_domain)


def validate_chapter_number(chapter_num: Any) -> float:
    """Valide un numéro de chapitre (fonction utilitaire)."""
    return get_validator().validate_chapter_number(chapter_num)


def validate_chapter_range(start: Any, end: Any) -> Tuple[float, float]:
    """Valide une plage de chapitres (fonction utilitaire)."""
    return get_validator().validate_chapter_range(start, end)


def validate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Valide un dictionnaire de paramètres (fonction utilitaire)."""
    return get_validator().validate_params_dict(params)
