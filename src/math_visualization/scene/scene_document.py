"""Domain model for one mathematical visualization document."""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class SceneDocument:
    """Minimal, renderer-independent document state for Stage 0."""

    title: str = "Untitled"
    schema_version: int = 1
    document_id: str = field(default_factory=lambda: uuid4().hex)
