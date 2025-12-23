# error_handler.py
"""
Module de gestion centralisée des erreurs PANELia

Fournit :
- Classification des erreurs par type
- Retry logic avec backoff exponentiel
- Circuit breaker pattern
- Gestion gracieuse des erreurs
- Logging structuré
- Recovery automatique

Auteur: PANELia Team
Date: 2025-12-08
"""

import time
import functools
from typing import Optional, Callable, Any, Type, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from loguru import logger


class ErrorSeverity(Enum):
    """Niveau de sévérité des erreurs."""
    INFO = "info"           # Erreur mineure, récupérable
    WARNING = "warning"     # Erreur moyenne, nécessite attention
    ERROR = "error"         # Erreur grave, affecte fonctionnalité
    CRITICAL = "critical"   # Erreur critique, arrêt nécessaire


class ErrorCategory(Enum):
    """Catégorie d'erreur pour classification."""
    NETWORK = "network"             # Erreurs réseau (timeout, connexion)
    VALIDATION = "validation"       # Erreurs de validation
    SCRAPING = "scraping"          # Erreurs de scraping (parsing, extraction)
    FILE_IO = "file_io"            # Erreurs I/O fichiers
    DRIVER = "driver"              # Erreurs Selenium/WebDriver
    PROCESSING = "processing"      # Erreurs traitement images
    UNKNOWN = "unknown"            # Erreur non catégorisée


@dataclass
class ErrorContext:
    """Contexte enrichi d'une erreur."""
    exception: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    chapter_num: Optional[float] = None
    url: Optional[str] = None
    retry_count: int = 0
    recoverable: bool = True
    user_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour logging."""
        return {
            "error_type": type(self.exception).__name__,
            "error_message": str(self.exception),
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "chapter_num": self.chapter_num,
            "url": self.url,
            "retry_count": self.retry_count,
            "recoverable": self.recoverable,
            "user_message": self.user_message
        }


class CircuitBreaker:
    """
    Circuit breaker pattern pour prévenir cascades d'erreurs.

    États:
    - CLOSED: Normal, requêtes passent
    - OPEN: Trop d'erreurs, requêtes bloquées
    - HALF_OPEN: Test de récupération

    Usage:
        breaker = CircuitBreaker(threshold=5, timeout=60)
        if breaker.can_execute():
            try:
                result = operation()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
    """

    def __init__(self, threshold: int = 5, timeout: int = 60):
        """
        Args:
            threshold: Nombre d'échecs avant ouverture
            timeout: Secondes avant tentative de récupération
        """
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Vérifie si l'opération peut être exécutée."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Vérifier si timeout écoulé pour passer en HALF_OPEN
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).total_seconds() >= self.timeout:
                self.state = "HALF_OPEN"
                logger.info(f"Circuit breaker passage en HALF_OPEN (test récupération)")
                return True
            return False

        # HALF_OPEN : autoriser une tentative
        return True

    def record_success(self):
        """Enregistre un succès."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failures = 0
            logger.info("Circuit breaker FERMÉ (récupération réussie)")

    def record_failure(self):
        """Enregistre un échec."""
        self.failures += 1
        self.last_failure_time = datetime.now()

        if self.state == "HALF_OPEN":
            self.state = "OPEN"
            logger.warning("Circuit breaker réouvert (récupération échouée)")
        elif self.failures >= self.threshold:
            self.state = "OPEN"
            logger.error(
                f"Circuit breaker OUVERT ({self.failures} échecs, "
                f"timeout {self.timeout}s)"
            )

    def reset(self):
        """Réinitialise le circuit breaker."""
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        logger.info("Circuit breaker réinitialisé")


class ErrorHandler:
    """
    Gestionnaire centralisé d'erreurs avec retry logic et circuit breaker.

    Usage:
        handler = ErrorHandler()

        # Retry automatique
        @handler.retry(max_attempts=3, backoff=2.0)
        def risky_operation():
            # ...

        # Classification d'erreur
        try:
            operation()
        except Exception as e:
            context = handler.classify_error(e, chapter_num=1.5)
            handler.handle_error(context)
    """

    def __init__(self):
        """Initialise le gestionnaire d'erreurs."""
        self.circuit_breakers = {}  # Par catégorie
        logger.info("ErrorHandler initialisé")

    def classify_error(
        self,
        exception: Exception,
        chapter_num: Optional[float] = None,
        url: Optional[str] = None
    ) -> ErrorContext:
        """
        Classifie une erreur et crée un contexte enrichi.

        Args:
            exception: Exception levée
            chapter_num: Numéro de chapitre (optionnel)
            url: URL concernée (optionnelle)

        Returns:
            ErrorContext avec classification
        """
        error_type = type(exception).__name__
        error_msg = str(exception).lower()

        # Classification par type d'exception
        if "timeout" in error_type.lower() or "timeout" in error_msg:
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.WARNING
            recoverable = True
            user_msg = "Délai d'attente dépassé. Nouvelle tentative..."

        elif "connection" in error_type.lower() or "connection" in error_msg:
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.ERROR
            recoverable = True
            user_msg = "Erreur de connexion. Vérifiez votre connexion internet."

        elif "validation" in error_type.lower():
            category = ErrorCategory.VALIDATION
            severity = ErrorSeverity.ERROR
            recoverable = False
            user_msg = f"Validation échouée : {exception}"

        elif "selenium" in error_type.lower() or "webdriver" in error_type.lower():
            category = ErrorCategory.DRIVER
            severity = ErrorSeverity.ERROR
            recoverable = True
            user_msg = "Erreur navigateur. Redémarrage en cours..."

        elif "permission" in error_msg or "access" in error_msg:
            category = ErrorCategory.FILE_IO
            severity = ErrorSeverity.CRITICAL
            recoverable = False
            user_msg = "Erreur de permissions. Vérifiez les droits d'accès."

        elif "disk" in error_msg or "space" in error_msg:
            category = ErrorCategory.FILE_IO
            severity = ErrorSeverity.CRITICAL
            recoverable = False
            user_msg = "Espace disque insuffisant."

        elif "parse" in error_msg or "decode" in error_msg:
            category = ErrorCategory.SCRAPING
            severity = ErrorSeverity.WARNING
            recoverable = True
            user_msg = "Erreur d'extraction. Chapitre peut-être vide."

        elif "image" in error_msg or "PIL" in error_type:
            category = ErrorCategory.PROCESSING
            severity = ErrorSeverity.WARNING
            recoverable = True
            user_msg = "Erreur traitement image. Image ignorée."

        else:
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.ERROR
            recoverable = True
            user_msg = f"Erreur inattendue : {error_type}"

        return ErrorContext(
            exception=exception,
            category=category,
            severity=severity,
            chapter_num=chapter_num,
            url=url,
            recoverable=recoverable,
            user_message=user_msg
        )

    def handle_error(self, context: ErrorContext) -> bool:
        """
        Gère une erreur de manière appropriée.

        Args:
            context: Contexte d'erreur

        Returns:
            bool: True si l'erreur est récupérable, False sinon
        """
        # Logger selon sévérité
        log_data = context.to_dict()

        if context.severity == ErrorSeverity.INFO:
            logger.info(f"[ERROR] {context.user_message}", extra=log_data)
        elif context.severity == ErrorSeverity.WARNING:
            logger.warning(f"[ERROR] {context.user_message}", extra=log_data)
        elif context.severity == ErrorSeverity.ERROR:
            logger.error(f"[ERROR] {context.user_message}", extra=log_data)
        else:  # CRITICAL
            logger.critical(f"[ERROR] {context.user_message}", extra=log_data)

        # Mettre à jour circuit breaker si applicable
        if context.category != ErrorCategory.VALIDATION:
            breaker = self.get_circuit_breaker(context.category)
            breaker.record_failure()

        return context.recoverable

    def get_circuit_breaker(self, category: ErrorCategory) -> CircuitBreaker:
        """
        Récupère ou crée un circuit breaker pour une catégorie.

        Args:
            category: Catégorie d'erreur

        Returns:
            CircuitBreaker pour cette catégorie
        """
        if category not in self.circuit_breakers:
            # Paramètres par catégorie
            if category == ErrorCategory.NETWORK:
                threshold, timeout = 3, 30
            elif category == ErrorCategory.DRIVER:
                threshold, timeout = 2, 60
            else:
                threshold, timeout = 5, 60

            self.circuit_breakers[category] = CircuitBreaker(threshold, timeout)

        return self.circuit_breakers[category]

    def retry(
        self,
        max_attempts: int = 3,
        backoff: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        on_retry: Optional[Callable] = None
    ):
        """
        Décorateur pour retry automatique avec backoff exponentiel.

        Args:
            max_attempts: Nombre maximum de tentatives
            backoff: Facteur de backoff (secondes doublées à chaque tentative)
            exceptions: Tuple d'exceptions à intercepter
            on_retry: Callback optionnel appelé avant chaque retry

        Usage:
            @handler.retry(max_attempts=3, backoff=2.0)
            def download_image(url):
                # ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        # Dernier essai ?
                        if attempt == max_attempts - 1:
                            break

                        # Calculer temps d'attente
                        wait_time = backoff * (2 ** attempt)

                        # Classifier l'erreur
                        context = self.classify_error(e)
                        context.retry_count = attempt + 1

                        logger.warning(
                            f"Tentative {attempt + 1}/{max_attempts} échouée. "
                            f"Nouvelle tentative dans {wait_time:.1f}s. "
                            f"Erreur: {context.user_message}"
                        )

                        # Callback optionnel
                        if on_retry:
                            on_retry(attempt, wait_time, e)

                        time.sleep(wait_time)

                # Toutes les tentatives ont échoué
                context = self.classify_error(last_exception)
                context.retry_count = max_attempts
                self.handle_error(context)

                raise last_exception

            return wrapper
        return decorator

    def safe_execute(
        self,
        func: Callable,
        *args,
        default: Any = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        **kwargs
    ) -> Any:
        """
        Exécute une fonction de manière sécurisée.

        Args:
            func: Fonction à exécuter
            *args: Arguments positionnels
            default: Valeur par défaut si erreur
            category: Catégorie d'erreur
            **kwargs: Arguments nommés

        Returns:
            Résultat de la fonction ou valeur par défaut
        """
        breaker = self.get_circuit_breaker(category)

        if not breaker.can_execute():
            logger.warning(
                f"Circuit breaker ouvert pour {category.value}. "
                "Opération annulée."
            )
            return default

        try:
            result = func(*args, **kwargs)
            breaker.record_success()
            return result
        except Exception as e:
            context = self.classify_error(e)
            context.category = category
            self.handle_error(context)
            return default

    def reset_circuit_breakers(self):
        """Réinitialise tous les circuit breakers."""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        logger.info("Tous les circuit breakers réinitialisés")


# Instance globale (singleton)
_global_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """
    Retourne l'instance globale du gestionnaire d'erreurs.

    Returns:
        ErrorHandler: Instance singleton
    """
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler


def reset_error_handler():
    """Réinitialise le gestionnaire global."""
    global _global_handler
    if _global_handler:
        _global_handler.reset_circuit_breakers()
    else:
        _global_handler = ErrorHandler()


# Fonctions utilitaires

def retry_on_error(max_attempts: int = 3, backoff: float = 2.0):
    """Décorateur de retry (fonction utilitaire)."""
    return get_error_handler().retry(max_attempts=max_attempts, backoff=backoff)


def safe_execute(func: Callable, *args, default: Any = None, **kwargs) -> Any:
    """Exécution sécurisée (fonction utilitaire)."""
    return get_error_handler().safe_execute(func, *args, default=default, **kwargs)


def classify_and_log_error(
    exception: Exception,
    chapter_num: Optional[float] = None,
    url: Optional[str] = None
) -> ErrorContext:
    """Classifie et log une erreur (fonction utilitaire)."""
    handler = get_error_handler()
    context = handler.classify_error(exception, chapter_num, url)
    handler.handle_error(context)
    return context
