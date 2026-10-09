"""Matrix properties view model: determinant, rank, invertibility and their explanation."""

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.math_core.matrix_analysis import (
    MatrixAnalysis,
    MatrixStatus,
    Orientation,
    analyze,
)
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.formatting import format_number, format_quantity
from math_visualization.viewmodels.transformation_viewmodel import TransformationViewModel


ORIENTATION_TEXT = {
    Orientation.PRESERVED: "Preserved",
    Orientation.REVERSED: "Reversed (flipped)",
    Orientation.COLLAPSED: "Collapsed",
}


def _factor(value: float) -> str:
    """A matrix entry inside a product, parenthesised when negative: ``(−2)``."""
    text = format_number(value)
    return f"({text})" if value < 0 else text


class MatrixPropertiesViewModel(QObject):
    """Publishes what the target matrix A does to the plane, and what A(t) does now.

    Every value comes from one :func:`analyze` call, so rank, invertibility,
    orientation and status always agree.
    """

    propertiesChanged = Signal()
    currentChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(
        self,
        document: SceneDocument,
        transformation: TransformationViewModel,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._transformation = transformation
        self._analysis = analyze(document.matrix)
        transformation.matrixChanged.connect(self._on_matrix_changed)
        transformation.currentMatrixChanged.connect(self.currentChanged)

    def analysis(self) -> MatrixAnalysis:
        return self._analysis

    def _on_matrix_changed(self) -> None:
        self._analysis = analyze(self._document.matrix)
        self.propertiesChanged.emit()

    # Target matrix A ------------------------------------------------------------------

    @Property(str, notify=propertiesChanged)
    def determinantText(self) -> str:
        return format_quantity(self._analysis.determinant)

    @Property(str, notify=propertiesChanged)
    def areaScaleText(self) -> str:
        return "×" + format_quantity(self._analysis.area_scale)

    @Property(str, notify=propertiesChanged)
    def orientation(self) -> str:
        return self._analysis.orientation.value

    @Property(str, notify=propertiesChanged)
    def orientationText(self) -> str:
        return ORIENTATION_TEXT[self._analysis.orientation]

    @Property(int, notify=propertiesChanged)
    def rank(self) -> int:
        return self._analysis.rank

    @Property(bool, notify=propertiesChanged)
    def invertible(self) -> bool:
        return self._analysis.is_invertible

    @Property(str, notify=propertiesChanged)
    def conditionText(self) -> str:
        return format_quantity(self._analysis.condition_number, 3)

    @Property(str, notify=propertiesChanged)
    def status(self) -> str:
        return self._analysis.status.value

    @Property(str, notify=propertiesChanged)
    def statusText(self) -> str:
        analysis = self._analysis
        if analysis.status is MatrixStatus.REGULAR:
            return "Invertible"
        if analysis.status is MatrixStatus.NEAR_SINGULAR:
            return "Near-singular"
        return "Singular"

    @Property(str, notify=propertiesChanged)
    def statusDetail(self) -> str:
        """One sentence explaining the status, shown under the badge."""
        analysis = self._analysis
        if analysis.status is MatrixStatus.REGULAR:
            return "Every output comes from exactly one input; A⁻¹ undoes A."
        if analysis.status is MatrixStatus.NEAR_SINGULAR:
            return (
                f"Invertible, but the plane is squashed almost flat (κ ≈ "
                f"{format_quantity(analysis.condition_number, 3)}). A⁻¹ amplifies small "
                "errors enormously."
            )
        if analysis.rank == 1:
            return "The plane collapses onto a line: a whole line of inputs lands on the origin."
        return "Every input collapses onto the origin."

    @Property("QStringList", notify=propertiesChanged)
    def inverseEntryTexts(self) -> list[str]:
        inverse = self._analysis.inverse
        return [] if inverse is None else [format_quantity(value) for value in inverse.entries]

    @Property(str, notify=propertiesChanged)
    def determinantFormula(self) -> str:
        a, b, c, d = self._document.matrix.entries
        return (
            f"det A = ad − bc = {_factor(a)}·{_factor(d)} − {_factor(b)}·{_factor(c)} = "
            f"{format_quantity(self._analysis.determinant)}"
        )

    @Property(str, notify=propertiesChanged)
    def rankFormula(self) -> str:
        analysis = self._analysis
        verdict = "invertible" if analysis.is_invertible else "not invertible"
        return f"rank A = {analysis.rank}  ({verdict}; σ_min/σ_max = {self._ratio_text()})"

    def _ratio_text(self) -> str:
        largest, smallest = self._analysis.singular_values
        return "0" if largest == 0.0 else format_quantity(smallest / largest, 3)

    @Slot(result=bool)
    def applyInverse(self) -> bool:
        """Replace A by A⁻¹ (undoable)."""
        inverse = self._analysis.inverse
        if inverse is None:
            self.errorOccurred.emit("A is singular, so it has no inverse")
            return False
        return self._transformation.set_matrix(inverse)

    # Current matrix A(t) ---------------------------------------------------------------

    @Property(str, notify=currentChanged)
    def currentDeterminantText(self) -> str:
        """det A(t), shown on the unit square while the transformation plays.

        It reads 0 exactly when A(t) is singular under the shared tolerance, so
        rounding noise never shows, while a near-singular value is not rounded away.
        """
        live = analyze(self._transformation.current_matrix())
        return "det = " + (format_quantity(live.determinant, 2) if live.is_invertible else "0")
