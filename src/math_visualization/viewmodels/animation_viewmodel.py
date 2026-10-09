"""Animation view model: playback of the transformation shared by every workspace."""

from __future__ import annotations

import math
from dataclasses import replace

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.math_core.transformations import ease
from math_visualization.scene.animation_state import PLAYBACK_SPEEDS
from math_visualization.scene.scene_document import SceneDocument


class AnimationViewModel(QObject):
    """Owns playback; the elapsed fraction τ lives in the document.

    QML drives time by calling :meth:`advance` once per rendered frame (from a
    ``FrameAnimation``), so playback is in step with the display. Reaching the
    end pauses; playing again from the end restarts from the beginning.
    """

    progressChanged = Signal()
    playingChanged = Signal()
    settingsChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, document: SceneDocument, parent: QObject | None = None):
        super().__init__(parent)
        self._document = document
        self._playing = False

    @property
    def _state(self):
        return self._document.animation_state

    def _update_state(self, **changes) -> bool:
        try:
            state = replace(self._state, **changes)
        except (TypeError, ValueError) as error:
            self.errorOccurred.emit(f"Invalid animation setting: {error}")
            return False
        if state == self._state:
            return True
        progress_changed = state.progress != self._state.progress or state.rate_function != self._state.rate_function
        self._document.animation_state = state
        if progress_changed:
            self.progressChanged.emit()
        self.settingsChanged.emit()
        return True

    def reload(self) -> None:
        """The document was replaced (a project was opened): stop and publish its state."""
        self.pause()
        self.progressChanged.emit()
        self.settingsChanged.emit()

    # Progress ------------------------------------------------------------------

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        """Elapsed fraction τ of the animation, in [0, 1]."""
        return self._state.progress

    @Property(float, notify=progressChanged)
    def easedProgress(self) -> float:
        """Transformation parameter ``t = rate_function(τ)``."""
        return ease(self._state.progress, self._state.rate_function)

    @Slot(float)
    def setProgress(self, progress: float) -> None:
        if not math.isfinite(progress) or not 0.0 <= progress <= 1.0:
            self.errorOccurred.emit(f"Invalid animation progress: progress must be within [0, 1], got {progress!r}")
            return
        self._update_state(progress=progress)

    @Slot(float)
    def scrub(self, progress: float) -> None:
        """Move the playhead by hand; this pauses playback."""
        self.pause()
        self.setProgress(min(max(progress, 0.0), 1.0))

    # Playback ------------------------------------------------------------------

    @Property(bool, notify=playingChanged)
    def playing(self) -> bool:
        return self._playing

    def _set_playing(self, playing: bool) -> None:
        if playing != self._playing:
            self._playing = playing
            self.playingChanged.emit()

    @Slot()
    def play(self) -> None:
        if self._state.progress >= 1.0:
            self._update_state(progress=0.0)
        self._set_playing(True)

    @Slot()
    def pause(self) -> None:
        self._set_playing(False)

    @Slot()
    def togglePlaying(self) -> None:
        self.pause() if self._playing else self.play()

    @Slot()
    def reset(self) -> None:
        self.pause()
        self._update_state(progress=0.0)

    @Slot(float)
    def advance(self, seconds: float) -> None:
        """Advance playback by ``seconds`` of wall-clock time."""
        if not self._playing or not math.isfinite(seconds) or seconds <= 0.0:
            return
        state = self._state
        progress = min(1.0, state.progress + seconds * state.playback_speed / state.duration)
        self._update_state(progress=progress)
        if progress >= 1.0:
            self._set_playing(False)

    # Settings ------------------------------------------------------------------

    @Property(float, notify=settingsChanged)
    def duration(self) -> float:
        return self._state.duration

    @Property(float, notify=settingsChanged)
    def playbackSpeed(self) -> float:
        return self._state.playback_speed

    @Property("QVariantList", constant=True)
    def playbackSpeeds(self) -> list[float]:
        return list(PLAYBACK_SPEEDS)

    @Slot(float)
    def setPlaybackSpeed(self, speed: float) -> None:
        self._update_state(playback_speed=speed)

    @Property(str, notify=settingsChanged)
    def rateFunction(self) -> str:
        return self._state.rate_function

    @Slot(str)
    def setRateFunction(self, name: str) -> None:
        self._update_state(rate_function=name)
