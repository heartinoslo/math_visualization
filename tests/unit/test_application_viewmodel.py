from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel



def test_application_viewmodel() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)

    assert view_model.statusMessage == "Ready"
def test_ping_updates_status_message() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)

    view_model.ping()

    assert view_model.statusMessage == "Python connection OK"