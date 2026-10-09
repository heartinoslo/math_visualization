import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick3D
import MathVisualization.Rendering
import "../theme" as AppTheme

// 3D observation workspace. The camera transform, grid geometry and label
// positions all come from app.viewport3D; this file only assembles the scene
// and forwards pointer and keyboard input.
Rectangle {
    id: root
    objectName: "workspace3D"
    color: AppTheme.Theme.workspaceBackground
    clip: true
    focus: true

    readonly property var viewport: app.viewport3D
    readonly property var labels: viewport.labels
    readonly property var vectorArrows: viewport.vectorArrows
    readonly property var ghostArrows: viewport.ghostArrows
    readonly property var basisArrows: viewport.basisArrows
    readonly property var visualState: app.transformation.visualState
    readonly property var vectorLabels: viewport.vectorLabels

    function updateViewportSize() {
        viewport.setViewportSize(width, height)
    }

    onWidthChanged: updateViewportSize()
    onHeightChanged: updateViewportSize()
    Component.onCompleted: updateViewportSize()

    Keys.onPressed: function (event) {
        const presets = { "1": "front", "2": "top", "3": "oblique" }
        if (presets[event.text] !== undefined) {
            viewport.applyPreset(presets[event.text])
            event.accepted = true
        } else if (event.key === Qt.Key_Home) {
            viewport.resetView()
            event.accepted = true
        }
    }

    component FlatMaterial: PrincipledMaterial {
        lighting: PrincipledMaterial.NoLighting
        cullMode: Material.NoCulling
    }

    // An arrow from the origin whose local +Y points along the vector; Python
    // supplies the rotation and sizes. A zero vector is shown as a small sphere.
    component Arrow3D: Node {
        id: arrowNode
        property var arrow
        property color color: "white"
        rotation: arrow.rotation

        Model {
            visible: !arrowNode.arrow.isZero
            source: "#Cylinder"
            position: Qt.vector3d(0, arrowNode.arrow.shaftLength / 2, 0)
            scale: Qt.vector3d(arrowNode.arrow.radius / 50,
                               arrowNode.arrow.shaftLength / 100,
                               arrowNode.arrow.radius / 50)
            materials: FlatMaterial { baseColor: arrowNode.color }
        }

        Model {
            visible: !arrowNode.arrow.isZero
            source: "#Cone"
            position: Qt.vector3d(0, arrowNode.arrow.shaftLength, 0)
            scale: Qt.vector3d(arrowNode.arrow.headRadius / 50,
                               arrowNode.arrow.headLength / 100,
                               arrowNode.arrow.headRadius / 50)
            materials: FlatMaterial { baseColor: arrowNode.color }
        }

        Model {
            visible: arrowNode.arrow.isZero
            source: "#Sphere"
            scale: Qt.vector3d(arrowNode.arrow.radius * 3 / 50,
                               arrowNode.arrow.radius * 3 / 50,
                               arrowNode.arrow.radius * 3 / 50)
            materials: FlatMaterial { baseColor: arrowNode.color }
        }
    }

    // A mathematical axis along the node's local +Y, centred on the origin,
    // with an arrowhead at the positive end.
    component Axis3D: Node {
        id: axis
        property real halfLength: 100
        property real radius: 1
        property color color: "white"

        Model {
            source: "#Cylinder"
            scale: Qt.vector3d(axis.radius / 50, axis.halfLength / 50, axis.radius / 50)
            materials: FlatMaterial { baseColor: axis.color }
        }

        Model {
            source: "#Cone"
            position: Qt.vector3d(0, axis.halfLength, 0)
            scale: Qt.vector3d(axis.radius * 3 / 50, axis.radius * 8 / 100, axis.radius * 3 / 50)
            materials: FlatMaterial { baseColor: axis.color }
        }
    }

    View3D {
        id: view
        objectName: "view3D"
        anchors.fill: parent
        camera: root.viewport.projectionMode === "orthographic" ? orthographicCamera : perspectiveCamera
        readonly property string activeCameraName: camera ? camera.objectName : ""

        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Color
            clearColor: AppTheme.Theme.workspaceBackground
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
        }

        PerspectiveCamera {
            id: perspectiveCamera
            objectName: "perspectiveCamera"
            position: root.viewport.cameraPosition
            rotation: root.viewport.cameraRotation
            fieldOfView: root.viewport.fieldOfView
            fieldOfViewOrientation: PerspectiveCamera.Vertical
            clipNear: root.viewport.clipNear
            clipFar: root.viewport.clipFar
        }

        OrthographicCamera {
            id: orthographicCamera
            objectName: "orthographicCamera"
            position: root.viewport.cameraPosition
            rotation: root.viewport.cameraRotation
            horizontalMagnification: root.viewport.orthographicMagnification
            verticalMagnification: root.viewport.orthographicMagnification
            clipNear: root.viewport.clipNear
            clipFar: root.viewport.clipFar
        }

        // Active XY plane: minor and major grid plus a faint accent fill.
        Model {
            objectName: "minorGrid"
            geometry: LineSetGeometry { vertices: root.viewport.minorGridVertices }
            materials: FlatMaterial { baseColor: AppTheme.Theme.grid3DMinor }
        }

        Model {
            objectName: "majorGrid"
            geometry: LineSetGeometry { vertices: root.viewport.majorGridVertices }
            materials: FlatMaterial { baseColor: AppTheme.Theme.grid3DMajor }
        }

        Model {
            objectName: "activePlaneFill"
            source: "#Rectangle"
            position: root.viewport.gridCenter
            eulerRotation.x: -90
            scale: Qt.vector3d(root.viewport.gridHalfExtent / 50, root.viewport.gridHalfExtent / 50, 1)
            opacity: AppTheme.Theme.activePlaneOpacity
            materials: FlatMaterial { baseColor: AppTheme.Theme.accentColor }
        }

        // Auxiliary XZ and YZ reference planes: sparse lines only, so they
        // never hide the active plane.
        Model {
            objectName: "auxiliaryGrid"
            visible: root.viewport.auxiliaryPlanesVisible
            geometry: LineSetGeometry { vertices: root.viewport.auxiliaryGridVertices }
            opacity: AppTheme.Theme.auxiliaryPlaneOpacity
            materials: FlatMaterial { baseColor: AppTheme.Theme.grid3DMajor }
        }

        // Axes: mathematical x -> scene +X, y -> scene -Z, z -> scene +Y.
        Axis3D {
            objectName: "xAxis3D"
            eulerRotation.z: -90
            halfLength: root.viewport.axisHalfLength
            radius: root.viewport.axisRadius
            color: AppTheme.Theme.axisXColor
        }

        Axis3D {
            objectName: "yAxis3D"
            eulerRotation.x: -90
            halfLength: root.viewport.axisHalfLength
            radius: root.viewport.axisRadius
            color: AppTheme.Theme.axisYColor
        }

        Axis3D {
            objectName: "zAxis3D"
            halfLength: root.viewport.axisHalfLength
            radius: root.viewport.axisRadius
            color: AppTheme.Theme.axisZColor
        }

        Model {
            objectName: "origin3D"
            source: "#Sphere"
            scale: Qt.vector3d(root.viewport.axisRadius * 2.5 / 50,
                               root.viewport.axisRadius * 2.5 / 50,
                               root.viewport.axisRadius * 2.5 / 50)
            materials: FlatMaterial { baseColor: AppTheme.Theme.primaryText }
        }

        // Vectors embedded in the XY plane as (x, y, 0). Each node points its
        // local +Y along the vector; Python supplies the rotation and sizes.
        // Transformation layer: the unit square, the transformed grid in blue
        // and the images of the axes, rebuilt by Python for each A(t).
        Model {
            objectName: "unitSquare3D"
            visible: root.visualState.show_unit_square
            geometry: TriangleGeometry { vertices: root.viewport.unitSquareVertices }
            opacity: AppTheme.Theme.unitSquareOpacity
            materials: FlatMaterial { baseColor: AppTheme.Theme.unitSquareColor }
        }

        Model {
            objectName: "transformedGrid3D"
            visible: root.visualState.show_transformed_grid
            geometry: LineSetGeometry { vertices: root.viewport.transformedGridVertices }
            materials: FlatMaterial { baseColor: AppTheme.Theme.transformedGridColor }
        }

        Model {
            objectName: "transformedAxes3D"
            visible: root.visualState.show_transformed_grid
            geometry: LineSetGeometry { vertices: root.viewport.transformedAxisVertices }
            materials: FlatMaterial { baseColor: AppTheme.Theme.transformedAxisColor }
        }

        // Faint input vectors while transformed; their tips are the drag handles.
        Repeater3D {
            objectName: "ghostArrows3D"
            model: root.ghostArrows.length
            delegate: Arrow3D {
                required property int index
                arrow: root.ghostArrows[index]
                color: arrow.color
                opacity: AppTheme.Theme.ghostOpacity
            }
        }

        // A(t)·v for every vector, embedded in the XY plane as (x, y, 0).
        Repeater3D {
            objectName: "vectorArrows3D"
            model: root.vectorArrows.length
            delegate: Arrow3D {
                required property int index
                arrow: root.vectorArrows[index]
                color: arrow.color
            }
        }

        // î and ĵ after A(t): the columns of the current matrix.
        Repeater3D {
            objectName: "basisArrows3D"
            model: root.basisArrows.length
            delegate: Arrow3D {
                required property int index
                arrow: root.basisArrows[index]
                color: index === 0 ? AppTheme.Theme.iHatColor : AppTheme.Theme.jHatColor
            }
        }

        Model {
            objectName: "componentLines3D"
            visible: root.viewport.componentLinesVisible
            geometry: LineSetGeometry { vertices: root.viewport.componentLineVertices }
            materials: FlatMaterial { baseColor: AppTheme.Theme.secondaryText }
        }
    }

    // Axis names and tick labels, projected to screen space by Python.
    Item {
        objectName: "labelLayer3D"
        anchors.fill: parent

        Repeater {
            objectName: "labels3D"
            model: root.labels.length
            delegate: Label {
                required property int index
                readonly property var entry: root.labels[index]
                readonly property bool isAxis: entry.kind === "axis"
                text: entry.text
                x: entry.x + (isAxis ? 8 : 4)
                y: entry.y - (isAxis ? height : 0)
                font.pixelSize: isAxis ? 15 : AppTheme.Theme.axisLabelPixelSize
                font.bold: isAxis
                font.italic: isAxis
                color: !isAxis ? AppTheme.Theme.secondaryText
                    : entry.axis === "x" ? AppTheme.Theme.axisXColor
                    : entry.axis === "y" ? AppTheme.Theme.axisYColor
                    : AppTheme.Theme.axisZColor
            }
        }
    }

    Item {
        objectName: "vectorLabelLayer3D"
        anchors.fill: parent

        Repeater {
            objectName: "vectorLabels3D"
            model: root.vectorLabels.length
            delegate: Label {
                required property int index
                readonly property var entry: root.vectorLabels[index]
                text: entry.name
                x: entry.x + 8
                y: entry.y - height - 2
                color: entry.color
                font.pixelSize: AppTheme.Theme.vectorLabelPixelSize
                font.italic: true
                font.bold: entry.selected
            }
        }
    }

    // Left button: drag a vector tip in the XY plane (Shift snaps to the
    // grid), select by its shaft, or click empty space to clear the selection.
    // Right-drag orbits, middle-drag or Shift+right-drag pans, the wheel
    // dollies and double-click on empty space resets the camera.
    MouseArea {
        objectName: "viewport3DPointerArea"
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        cursorShape: (gesture === "pan" || gesture === "orbit") ? Qt.ClosedHandCursor
            : (gesture === "drag" || hoverPart === "tip") ? Qt.SizeAllCursor
            : hoverPart === "shaft" ? Qt.PointingHandCursor
            : Qt.CrossCursor

        property real lastX: 0
        property real lastY: 0
        // Decided once per gesture, so releasing Shift mid-drag does not
        // switch between panning and orbiting.
        property string gesture: ""

        property bool moved: false
        property string hoverPart: ""

        onPressed: function (mouse) {
            root.forceActiveFocus()
            lastX = mouse.x
            lastY = mouse.y
            moved = false
            if (mouse.button === Qt.MiddleButton
                    || (mouse.button === Qt.RightButton && (mouse.modifiers & Qt.ShiftModifier)))
                gesture = "pan"
            else if (mouse.button === Qt.RightButton)
                gesture = "orbit"
            else {
                const part = root.viewport.beginVectorDrag(mouse.x, mouse.y)
                gesture = part === "tip" ? "drag" : part === "shaft" ? "select" : "empty"
            }
        }
        onReleased: {
            if (gesture === "drag")
                root.viewport.endVectorDrag()
            else if (gesture === "empty" && !moved)
                app.scene.clearSelection()
            gesture = ""
        }
        onCanceled: {
            if (gesture === "drag")
                root.viewport.endVectorDrag()
            gesture = ""
        }
        onPositionChanged: function (mouse) {
            const deltaX = mouse.x - lastX
            const deltaY = mouse.y - lastY
            lastX = mouse.x
            lastY = mouse.y
            moved = moved || deltaX !== 0 || deltaY !== 0
            if (gesture === "pan")
                root.viewport.panBy(deltaX, deltaY)
            else if (gesture === "orbit")
                root.viewport.orbitBy(deltaX, deltaY)
            else if (gesture === "drag")
                root.viewport.dragVector(mouse.x, mouse.y, (mouse.modifiers & Qt.ShiftModifier) !== 0)
            else if (!pressed)
                hoverPart = root.viewport.hitTest(mouse.x, mouse.y).part
            root.viewport.setCursor(mouse.x, mouse.y)
        }
        onWheel: function (wheel) {
            root.viewport.zoomBy(wheel.angleDelta.y)
        }
        onDoubleClicked: function (mouse) {
            if (mouse.button === Qt.LeftButton && root.viewport.hitTest(mouse.x, mouse.y).part === "")
                root.viewport.resetView()
        }
        onExited: {
            hoverPart = ""
            root.viewport.clearCursor()
        }
    }

    // Plan 12.4: make clear that the mathematics is 2D even though the view is 3D.
    Rectangle {
        objectName: "dimensionHint"
        readonly property real maximumWidth: root.width - 2 * AppTheme.Theme.spacingMedium
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: AppTheme.Theme.spacingMedium
        width: Math.min(hintColumn.implicitWidth, maximumWidth - 2 * AppTheme.Theme.spacingMedium)
            + 2 * AppTheme.Theme.spacingMedium
        height: hintColumn.implicitHeight + 2 * AppTheme.Theme.spacingSmall
        radius: AppTheme.Theme.panelRadius
        color: AppTheme.Theme.overlayBackground
        border.color: AppTheme.Theme.borderColor

        ColumnLayout {
            id: hintColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: AppTheme.Theme.spacingMedium
            anchors.rightMargin: AppTheme.Theme.spacingMedium
            spacing: 2

            Label {
                objectName: "dimensionHintLabel"
                Layout.fillWidth: true
                text: "Mathematical dimension: 2D · Display workspace: 3D · Active plane: XY"
                color: AppTheme.Theme.primaryText
                font.pixelSize: 12
                elide: Text.ElideRight
            }

            Label {
                Layout.fillWidth: true
                text: "Left-drag tip: move · Right-drag: orbit · Middle/Shift+right-drag: pan · Wheel: zoom · 1/2/3: views"
                color: AppTheme.Theme.secondaryText
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
        }
    }

    // A narrow column at the right edge keeps the centre, where the z axis
    // usually points, free.
    Column {
        objectName: "cameraToolbar"
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: AppTheme.Theme.spacingMedium
        spacing: AppTheme.Theme.spacingSmall

        component ToolbarButton: Button {
            width: projectionButton.implicitWidth
            implicitHeight: AppTheme.Theme.compactControlHeight
            font.pixelSize: 11
        }

        ToolbarButton {
            objectName: "frontViewButton"
            text: "Front"
            onClicked: root.viewport.applyPreset("front")
        }

        ToolbarButton {
            objectName: "topViewButton"
            text: "Top"
            onClicked: root.viewport.applyPreset("top")
        }

        ToolbarButton {
            objectName: "obliqueViewButton"
            text: "Oblique"
            onClicked: root.viewport.applyPreset("oblique")
        }

        ToolbarButton {
            id: projectionButton
            objectName: "projectionButton"
            text: root.viewport.projectionMode === "perspective" ? "Perspective" : "Orthographic"
            onClicked: root.viewport.toggleProjectionMode()
        }

        ToolbarButton {
            objectName: "auxiliaryPlanesButton"
            text: root.viewport.auxiliaryPlanesVisible ? "Hide XZ/YZ" : "Show XZ/YZ"
            onClicked: root.viewport.toggleAuxiliaryPlanes()
        }
    }
}
