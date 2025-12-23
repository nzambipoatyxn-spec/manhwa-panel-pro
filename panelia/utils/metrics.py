# metrics.py
"""
Module de monitoring des performances PANELia

Collecte et analyse des métriques :
- Temps de scraping par chapitre
- Vitesse de téléchargement
- Taux de succès/échec
- Nombre d'images traitées
- Utilisation CPU/Mémoire (optionnel)

Auteur: PANELia Team
Date: 2025-12-08
"""

import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict

from loguru import logger


@dataclass
class ChapterMetrics:
    """Métriques pour un chapitre individuel."""
    chapter_num: float
    url: str
    start_time: float
    end_time: Optional[float] = None
    images_found: int = 0
    images_downloaded: int = 0
    images_processed: int = 0
    download_errors: int = 0
    total_bytes: int = 0
    success: bool = False
    error_message: Optional[str] = None

    @property
    def duration(self) -> float:
        """Durée totale en secondes."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def download_speed_mbps(self) -> float:
        """Vitesse de téléchargement en MB/s."""
        if self.duration > 0 and self.total_bytes > 0:
            return (self.total_bytes / 1024 / 1024) / self.duration
        return 0.0

    @property
    def success_rate(self) -> float:
        """Taux de succès des téléchargements (%)."""
        if self.images_found > 0:
            return (self.images_downloaded / self.images_found) * 100
        return 0.0

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire avec métriques calculées."""
        data = asdict(self)
        data['duration'] = self.duration
        data['download_speed_mbps'] = round(self.download_speed_mbps, 2)
        data['success_rate'] = round(self.success_rate, 2)
        return data


class MetricsCollector:
    """
    Collecteur central de métriques pour PANELia.

    Usage:
        collector = MetricsCollector()

        # Démarrer tracking d'un chapitre
        collector.start_chapter(1.0, "https://example.com/chapter/1")

        # Mettre à jour les métriques
        collector.update_chapter(1.0, images_found=10)
        collector.add_download(1.0, bytes_downloaded=1024000, success=True)

        # Terminer le tracking
        collector.end_chapter(1.0, success=True)

        # Obtenir les statistiques
        stats = collector.get_stats()
    """

    def __init__(self):
        """Initialise le collecteur de métriques."""
        self.chapters: Dict[float, ChapterMetrics] = {}
        self.session_start = time.time()
        self.total_chapters_attempted = 0
        self.total_chapters_succeeded = 0
        self.total_images_downloaded = 0
        self.total_bytes_downloaded = 0

        logger.info("MetricsCollector initialisé")

    def start_chapter(self, chapter_num: float, url: str) -> None:
        """
        Démarre le tracking d'un chapitre.

        Args:
            chapter_num: Numéro du chapitre
            url: URL du chapitre
        """
        self.chapters[chapter_num] = ChapterMetrics(
            chapter_num=chapter_num,
            url=url,
            start_time=time.time()
        )
        self.total_chapters_attempted += 1
        logger.debug(f"[METRICS] Démarrage tracking chapitre {chapter_num}")

    def update_chapter(
        self,
        chapter_num: float,
        images_found: Optional[int] = None,
        images_downloaded: Optional[int] = None,
        images_processed: Optional[int] = None
    ) -> None:
        """
        Met à jour les métriques d'un chapitre.

        Args:
            chapter_num: Numéro du chapitre
            images_found: Nombre d'images trouvées
            images_downloaded: Nombre d'images téléchargées
            images_processed: Nombre d'images traitées
        """
        if chapter_num not in self.chapters:
            logger.warning(f"[METRICS] Chapitre {chapter_num} non trouvé")
            return

        metrics = self.chapters[chapter_num]
        if images_found is not None:
            metrics.images_found = images_found
        if images_downloaded is not None:
            metrics.images_downloaded = images_downloaded
        if images_processed is not None:
            metrics.images_processed = images_processed

    def add_download(
        self,
        chapter_num: float,
        bytes_downloaded: int,
        success: bool = True
    ) -> None:
        """
        Enregistre un téléchargement d'image.

        Args:
            chapter_num: Numéro du chapitre
            bytes_downloaded: Taille en octets
            success: Succès ou échec
        """
        if chapter_num not in self.chapters:
            return

        metrics = self.chapters[chapter_num]
        metrics.total_bytes += bytes_downloaded

        if success:
            metrics.images_downloaded += 1
            self.total_images_downloaded += 1
            self.total_bytes_downloaded += bytes_downloaded
        else:
            metrics.download_errors += 1

    def end_chapter(
        self,
        chapter_num: float,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """
        Termine le tracking d'un chapitre.

        Args:
            chapter_num: Numéro du chapitre
            success: Succès ou échec du scraping
            error_message: Message d'erreur si échec
        """
        if chapter_num not in self.chapters:
            logger.warning(f"[METRICS] Chapitre {chapter_num} non trouvé pour end")
            return

        metrics = self.chapters[chapter_num]
        metrics.end_time = time.time()
        metrics.success = success
        metrics.error_message = error_message

        if success:
            self.total_chapters_succeeded += 1

        logger.info(
            f"[METRICS] Chapitre {chapter_num} terminé - "
            f"Durée: {metrics.duration:.2f}s, "
            f"Images: {metrics.images_downloaded}/{metrics.images_found}, "
            f"Vitesse: {metrics.download_speed_mbps:.2f} MB/s"
        )

    def get_chapter_metrics(self, chapter_num: float) -> Optional[Dict]:
        """
        Récupère les métriques d'un chapitre spécifique.

        Args:
            chapter_num: Numéro du chapitre

        Returns:
            Dict avec les métriques ou None
        """
        if chapter_num in self.chapters:
            return self.chapters[chapter_num].to_dict()
        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Calcule et retourne les statistiques globales.

        Returns:
            Dict avec les statistiques complètes
        """
        session_duration = time.time() - self.session_start

        # Métriques par chapitre
        chapter_metrics = [m.to_dict() for m in self.chapters.values()]

        # Calculs agrégés
        total_duration = sum(m.duration for m in self.chapters.values() if m.end_time)
        avg_duration = total_duration / len(self.chapters) if self.chapters else 0

        total_images_found = sum(m.images_found for m in self.chapters.values())
        total_images_processed = sum(m.images_processed for m in self.chapters.values())

        global_success_rate = (
            (self.total_chapters_succeeded / self.total_chapters_attempted * 100)
            if self.total_chapters_attempted > 0 else 0
        )

        avg_speed_mbps = (
            (self.total_bytes_downloaded / 1024 / 1024) / total_duration
            if total_duration > 0 else 0
        )

        stats = {
            'session': {
                'start_time': datetime.fromtimestamp(self.session_start).isoformat(),
                'duration_seconds': round(session_duration, 2),
                'duration_human': self._format_duration(session_duration)
            },
            'chapters': {
                'attempted': self.total_chapters_attempted,
                'succeeded': self.total_chapters_succeeded,
                'failed': self.total_chapters_attempted - self.total_chapters_succeeded,
                'success_rate': round(global_success_rate, 2),
                'avg_duration_seconds': round(avg_duration, 2)
            },
            'images': {
                'found': total_images_found,
                'downloaded': self.total_images_downloaded,
                'processed': total_images_processed,
                'errors': sum(m.download_errors for m in self.chapters.values())
            },
            'performance': {
                'total_bytes_downloaded': self.total_bytes_downloaded,
                'total_mb_downloaded': round(self.total_bytes_downloaded / 1024 / 1024, 2),
                'avg_speed_mbps': round(avg_speed_mbps, 2),
                'total_scraping_time': round(total_duration, 2)
            },
            'chapter_details': chapter_metrics
        }

        return stats

    def _format_duration(self, seconds: float) -> str:
        """Formate une durée en format lisible."""
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def export_json(self, filepath: str) -> None:
        """
        Exporte les métriques en JSON.

        Args:
            filepath: Chemin du fichier de sortie
        """
        stats = self.get_stats()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        logger.info(f"[METRICS] Métriques exportées vers {filepath}")

    def export_csv(self, filepath: str) -> None:
        """
        Exporte les métriques des chapitres en CSV.

        Args:
            filepath: Chemin du fichier de sortie
        """
        import csv

        if not self.chapters:
            logger.warning("[METRICS] Aucune métrique à exporter")
            return

        # Headers
        headers = [
            'chapter_num', 'url', 'duration', 'images_found',
            'images_downloaded', 'images_processed', 'download_errors',
            'total_bytes', 'download_speed_mbps', 'success_rate', 'success'
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for metrics in self.chapters.values():
                data = metrics.to_dict()
                row = {k: data.get(k, '') for k in headers}
                writer.writerow(row)

        logger.info(f"[METRICS] Métriques exportées vers {filepath} (CSV)")

    def print_summary(self) -> None:
        """Affiche un résumé des métriques dans la console."""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES MÉTRIQUES")
        print("=" * 60)

        print(f"\n⏱️  Session:")
        print(f"  Durée: {stats['session']['duration_human']}")

        print(f"\n📚 Chapitres:")
        print(f"  Tentatives: {stats['chapters']['attempted']}")
        print(f"  Succès: {stats['chapters']['succeeded']}")
        print(f"  Échecs: {stats['chapters']['failed']}")
        print(f"  Taux de succès: {stats['chapters']['success_rate']}%")
        print(f"  Durée moyenne: {stats['chapters']['avg_duration_seconds']}s")

        print(f"\n🖼️  Images:")
        print(f"  Trouvées: {stats['images']['found']}")
        print(f"  Téléchargées: {stats['images']['downloaded']}")
        print(f"  Traitées: {stats['images']['processed']}")
        print(f"  Erreurs: {stats['images']['errors']}")

        print(f"\n⚡ Performance:")
        print(f"  Données téléchargées: {stats['performance']['total_mb_downloaded']} MB")
        print(f"  Vitesse moyenne: {stats['performance']['avg_speed_mbps']} MB/s")
        print(f"  Temps de scraping: {stats['performance']['total_scraping_time']}s")

        print("=" * 60 + "\n")

    def reset(self) -> None:
        """Réinitialise toutes les métriques."""
        self.chapters.clear()
        self.session_start = time.time()
        self.total_chapters_attempted = 0
        self.total_chapters_succeeded = 0
        self.total_images_downloaded = 0
        self.total_bytes_downloaded = 0
        logger.info("[METRICS] Métriques réinitialisées")


# Instance globale (singleton)
_global_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """
    Retourne l'instance globale du collecteur de métriques.

    Returns:
        MetricsCollector: Instance singleton
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def reset_collector() -> None:
    """Réinitialise le collecteur global."""
    global _global_collector
    if _global_collector:
        _global_collector.reset()
    else:
        _global_collector = MetricsCollector()
