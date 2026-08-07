from math_visualization.scene.scene_document import SceneDocument


def test_default_title() -> None:
    doc = SceneDocument()

    assert doc.title == "Untitled"

def test_document_ids_are_unique() -> None:
    first = SceneDocument()
    second = SceneDocument()

    assert first.document_id != second.document_id

def test_custom_title() -> None:
    document = SceneDocument(title="My Scene")

    assert document.title == "My Scene"