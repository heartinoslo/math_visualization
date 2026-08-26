"""Tests for the reserved Stage 0 exporter boundary."""

import pytest

from math_visualization.exporters import SceneExporter


def test_scene_exporter_is_an_abstract_boundary() -> None:
    with pytest.raises(TypeError):
        SceneExporter()
