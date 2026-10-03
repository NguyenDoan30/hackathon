"""Learning / Quiz / Flashcard module owned by Person 5."""

from .backend_adapter import BackendLearningProvider
from .progress import calculate_progress
from .schemas import LearningError, LearningSettings
from .service import LearningService

__all__ = [
    "BackendLearningProvider",
    "LearningError",
    "LearningService",
    "LearningSettings",
    "calculate_progress",
]
