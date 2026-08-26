from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel



def test_application_viewmodel() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)

    assert view_model.statusMessage == "Ready"
    assert view_model.document is document


def test_ping_updates_status_message_and_emits_signal() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    notifications: list[str] = []
    view_model.statusMessageChanged.connect(
        lambda: notifications.append(view_model.statusMessage)
    )

    view_model.ping()

    assert view_model.statusMessage == "Python connection OK"
    assert notifications == ["Python connection OK"]
