from dataclasses import dataclass, field
from uuid import uuid4

@dataclass
#Complete state container for mathematical experiments
class SceneDocument:
    title: str = "Untitled"
    schema_version: int = 1
    document_id: str = field(default_factory=lambda: uuid4().hex)