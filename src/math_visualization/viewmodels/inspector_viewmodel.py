"""Inspector view model: properties of the selected vector for the right panel."""

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.scene.vector_object import VECTOR_PALETTE, VectorObject
from math_visualization.viewmodels.formatting import format_number, parse_number
from math_visualization.viewmodels.scene_objects_viewmodel import SceneObjectsViewModel


class InspectorViewModel(QObject):
    """Expose the selected vector as display text and accept edits as text.

    Text input is parsed here, so QML never converts or validates numbers.
    Invalid input is reported through ``errorOccurred`` and leaves the vector
    unchanged.
    """

    changed = Signal()
    errorOccurred = Signal(str)

    def __init__(self, scene: SceneObjectsViewModel, parent: QObject | None = None):
        super().__init__(parent)
        self._scene = scene
        scene.vectorsChanged.connect(self.changed)
        scene.selectionChanged.connect(self.changed)

    @property
    def _selected(self) -> VectorObject | None:
        return self._scene.selected_vector

    @Property(bool, notify=changed)
    def hasSelection(self) -> bool:
        return self._selected is not None

    @Property(str, notify=changed)
    def name(self) -> str:
        return self._selected.name if self._selected else ""

    @Property(str, notify=changed)
    def color(self) -> str:
        return self._selected.color if self._selected else ""

    @Property(str, notify=changed)
    def xText(self) -> str:
        return format_number(self._selected.vector.x) if self._selected else ""

    @Property(str, notify=changed)
    def yText(self) -> str:
        return format_number(self._selected.vector.y) if self._selected else ""

    @Property(str, notify=changed)
    def lengthText(self) -> str:
        return format_number(self._selected.vector.length) if self._selected else ""

    @Property(str, notify=changed)
    def angleText(self) -> str:
        if self._selected is None:
            return ""
        if self._selected.vector.is_zero():
            return "undefined (zero vector)"
        return f"{format_number(self._selected.vector.angle_degrees, 2)}°"

    @Property(bool, notify=changed)
    def isZero(self) -> bool:
        return bool(self._selected and self._selected.vector.is_zero())

    @Property("QStringList", constant=True)
    def palette(self) -> list[str]:
        return list(VECTOR_PALETTE)

    @Slot(str, result=bool)
    def setName(self, name: str) -> bool:
        return bool(self._selected) and self._scene.rename(self._selected.object_id, name)

    @Slot(str, result=bool)
    def setColor(self, color: str) -> bool:
        return bool(self._selected) and self._scene.setColor(self._selected.object_id, color)

    @Slot(str, result=bool)
    def setXText(self, text: str) -> bool:
        return self._set_component(text, "x")

    @Slot(str, result=bool)
    def setYText(self, text: str) -> bool:
        return self._set_component(text, "y")

    def _set_component(self, text: str, component: str) -> bool:
        selected = self._selected
        if selected is None:
            return False
        try:
            value = parse_number(text)
        except ValueError as error:
            self.errorOccurred.emit(f"{component} of {selected.name}: {error}")
            return False
        x = value if component == "x" else selected.vector.x
        y = value if component == "y" else selected.vector.y
        return self._scene.setComponents(selected.object_id, x, y)
