"""Learning module owned by Person 5.

This package implements the backend LearningProvider contract without
modifying FastAPI routes, database models, frontend, or AI Smart Context.
"""

from .service import LearningService
from .schemas import LearningError

__all__ = ["LearningService", "LearningError"]
