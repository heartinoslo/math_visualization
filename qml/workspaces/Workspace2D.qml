import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "../components/canvas2d"
import "../theme" as AppTheme

// 2D coordinate canvas. Every position drawn here is computed by
// app.viewport2D; this file only draws layers and forwards pointer input.
Rectangle {
    id: root
    objectName: "workspace2D"
    color: AppTheme.Theme.workspaceBackground
    clip: true

    readonly property var viewport: app.viewport2D
    readonly property real devicePixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    // One device pixel (rounded) keeps grid lines crisp at fractional scaling.
    readonly property real hairline: Math.max(1, Math.round(devicePixelRatio)) / devicePixelRatio
    readonly property real axisWidth: 2 * hairline

    // Read each list once per change; delegates then index plain JS arrays.
    readonly property var minorX: viewport.minorX
    readonly property var minorY: viewport.minorY
    readonly property var majorX: viewport.majorX
    readonly property var majorY: viewport.majorY
    readonly property var xLabels: viewport.xLabels
    readonly property var yLabels: viewport.yLabels
    readonly property real originX: viewport.originX
    readonly property real originY: viewport.originY

    function snap(value) {
        return Math.round(value * devicePixelRatio) / devicePixelRatio
    }

    function clamp(value, low, high) {
        return Math.max(low, Math.min(value, high))
    }

    function updateViewportSize() {
        viewport.setViewportSize(width, height)
    }

    onWidthChanged: updateViewportSize()
    onHeightChanged: updateViewportSize()
    Component.onCompleted: updateViewportSize()

    component VerticalLine: Rectangle {
        required property real position
        x: root.snap(position) - width / 2
        width: root.hairline
        height: root.height
    }

    component HorizontalLine: Rectangle {
        required property real position
        y: root.snap(position) - height / 2
        width: root.width
        height: root.hairline
    }

    component AxisLabel: Label {
        color: AppTheme.Theme.secondaryText
        font.pixelSize: AppTheme.Theme.axisLabelPixelSize
    }

    FontMetrics {
        id: labelMetrics
        font.pixelSize: AppTheme.Theme.axisLabelPixelSize
    }

    // Row of x-axis labels: below the x axis, pinned to the nearest edge
    // when the axis leaves the view.
    readonly property real xLabelRowY: clamp(originY + AppTheme.Theme.axisLabelMargin,
                                             AppTheme.Theme.axisLabelMargin,
                                             height - labelMetrics.height - AppTheme.Theme.axisLabelMargin)

    // Layer 1: minor grid.
    Item {
        objectName: "minorGridLayer"
        anchors.fill: parent

        Repeater {
            objectName: "minorVerticalLines"
            model: root.minorX.length
            delegate: VerticalLine {
                required property int index
                position: root.minorX[index]
                color: AppTheme.Theme.gridMinor
            }
        }

        Repeater {
            objectName: "minorHorizontalLines"
            model: root.minorY.length
            delegate: HorizontalLine {
                required property int index
                position: root.minorY[index]
                color: AppTheme.Theme.gridMinor
            }
        }
    }

    // Layer 2: major grid.
    Item {
        objectName: "majorGridLayer"
        anchors.fill: parent

        Repeater {
            objectName: "majorVerticalLines"
            model: root.majorX.length
            delegate: VerticalLine {
                required property int index
                position: root.majorX[index]
                color: AppTheme.Theme.gridMajor
            }
        }

        Repeater {
            objectName: "majorHorizontalLines"
            model: root.majorY.length
            delegate: HorizontalLine {
                required property int index
                position: root.majorY[index]
                color: AppTheme.Theme.gridMajor
            }
        }
    }

    // Layer 3: axes.
    Item {
        objectName: "axisLayer"
        anchors.fill: parent

        Rectangle {
            objectName: "yAxis"
            visible: root.originX >= 0 && root.originX <= root.width
            x: root.snap(root.originX) - width / 2
            width: root.axisWidth
            height: root.height
            color: AppTheme.Theme.axisColor
        }

        Rectangle {
            objectName: "xAxis"
            visible: root.originY >= 0 && root.originY <= root.height
            y: root.snap(root.originY) - height / 2
            width: root.width
            height: root.axisWidth
            color: AppTheme.Theme.axisColor
        }
    }

    // Layer 4: tick labels. When an axis leaves the view its labels stay
    // pinned to the nearest edge so the scale remains readable.
    Item {
        objectName: "labelLayer"
        anchors.fill: parent

        Repeater {
            objectName: "xAxisLabels"
            model: root.xLabels.length
            delegate: AxisLabel {
                required property int index
                text: root.xLabels[index].text
                x: root.snap(root.xLabels[index].position) + AppTheme.Theme.axisLabelMargin
                y: root.xLabelRowY
                visible: x + width <= root.width - AppTheme.Theme.axisLabelMargin
            }
        }

        Repeater {
            objectName: "yAxisLabels"
            model: root.yLabels.length
            delegate: AxisLabel {
                required property int index
                text: root.yLabels[index].text
                x: root.clamp(root.originX + AppTheme.Theme.axisLabelMargin,
                              AppTheme.Theme.axisLabelMargin,
                              root.width - width - AppTheme.Theme.axisLabelMargin)
                y: root.snap(root.yLabels[index].position) + 1
                // Give way to the x-axis label row and never spill past the edge.
                visible: y + height <= root.height - AppTheme.Theme.axisLabelMargin
                    && (y + height < root.xLabelRowY || y > root.xLabelRowY + labelMetrics.height)
            }
        }

        AxisLabel {
            objectName: "originLabel"
            visible: root.originX >= 0 && root.originX <= root.width
                && root.originY >= 0 && root.originY <= root.height
            text: "0"
            x: root.originX + AppTheme.Theme.axisLabelMargin
            y: root.originY + AppTheme.Theme.axisLabelMargin
        }
    }

    // Layer 5: mathematical objects. Vectors are drawn from screen positions
    // published by app.viewport2D; the selected one shows dashed component
    // lines to both axes and a drag handle at its tip.
    readonly property var vectorShapes: viewport.vectorShapes
    readonly property var selectedShape: {
        for (let i = 0; i < vectorShapes.length; ++i)
            if (vectorShapes[i].selected)
                return vectorShapes[i]
        return null
    }

    Item {
        id: objectLayer
        objectName: "objectLayer"
        anchors.fill: parent

        Point2D {
            objectName: "originPoint"
            centerX: root.originX
            centerY: root.originY
            radius2D: AppTheme.Theme.originPointRadius
            color: AppTheme.Theme.axisColor
        }

        Segment2D {
            objectName: "componentLineX"
            visible: root.selectedShape !== null && !root.selectedShape.isZero
            dashed: true
            lineWidth: 1
            strokeColor: root.selectedShape ? root.selectedShape.color : "transparent"
            x1: root.selectedShape ? root.selectedShape.tipX : 0
            y1: root.selectedShape ? root.selectedShape.tipY : 0
            x2: root.selectedShape ? root.selectedShape.tipX : 0
            y2: root.originY
        }

        Segment2D {
            objectName: "componentLineY"
            visible: root.selectedShape !== null && !root.selectedShape.isZero
            dashed: true
            lineWidth: 1
            strokeColor: root.selectedShape ? root.selectedShape.color : "transparent"
            x1: root.selectedShape ? root.selectedShape.tipX : 0
            y1: root.selectedShape ? root.selectedShape.tipY : 0
            x2: root.originX
            y2: root.selectedShape ? root.selectedShape.tipY : 0
        }

        Repeater {
            objectName: "vectorArrows2D"
            model: root.vectorShapes.length

            delegate: Item {
                id: vectorItem
                required property int index
                readonly property var shape: root.vectorShapes[index]
                readonly property real dx: shape.tipX - root.originX
                readonly property real dy: shape.tipY - root.originY
                readonly property real screenLength: Math.hypot(dx, dy)
                anchors.fill: parent

                Arrow2D {
                    visible: !vectorItem.shape.isZero
                    x1: root.originX
                    y1: root.originY
                    x2: vectorItem.shape.tipX
                    y2: vectorItem.shape.tipY
                    strokeColor: vectorItem.shape.color
                    lineWidth: vectorItem.shape.selected
                        ? AppTheme.Theme.selectedVectorLineWidth : AppTheme.Theme.vectorLineWidth
                    headLength: AppTheme.Theme.vectorHeadLength
                    headHalfWidth: AppTheme.Theme.vectorHeadHalfWidth
                }

                // The zero vector has no direction, so it is shown as a ring.
                Rectangle {
                    visible: vectorItem.shape.isZero
                    x: root.originX - width / 2
                    y: root.originY - height / 2
                    width: AppTheme.Theme.zeroVectorRadius * 2
                    height: width
                    radius: width / 2
                    color: "transparent"
                    border.width: 2
                    border.color: vectorItem.shape.color
                }

                Point2D {
                    visible: vectorItem.shape.selected
                    centerX: vectorItem.shape.tipX
                    centerY: vectorItem.shape.tipY
                    radius2D: AppTheme.Theme.tipHandleRadius
                    color: AppTheme.Theme.workspaceBackground
                    border.width: 2
                    border.color: vectorItem.shape.color
                }

                // Names sit just beyond the tip, away from the origin.
                Label {
                    readonly property real offset: 14
                    readonly property real unitX: vectorItem.screenLength > 0 ? vectorItem.dx / vectorItem.screenLength : 0.7
                    readonly property real unitY: vectorItem.screenLength > 0 ? vectorItem.dy / vectorItem.screenLength : -0.7
                    text: vectorItem.shape.name
                    x: vectorItem.shape.tipX + unitX * offset - width / 2
                    y: vectorItem.shape.tipY + unitY * offset - height / 2
                    color: vectorItem.shape.color
                    font.pixelSize: AppTheme.Theme.vectorLabelPixelSize
                    font.italic: true
                    font.bold: vectorItem.shape.selected
                }
            }
        }
    }

    // Pointer input. A press on a vector tip drags it (Shift snaps to the
    // minor grid), on a shaft selects it, and on empty space pans the view;
    // a click on empty space clears the selection. The wheel zooms around the
    // cursor and a double-click on empty space resets the view.
    MouseArea {
        id: pointerArea
        objectName: "viewportPointerArea"
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        cursorShape: mode === "pan" ? Qt.ClosedHandCursor
            : (mode === "drag" || hoverPart === "tip") ? Qt.SizeAllCursor
            : hoverPart === "shaft" ? Qt.PointingHandCursor
            : Qt.CrossCursor

        property real lastX: 0
        property real lastY: 0
        property string mode: ""
        property string hoverPart: ""
        property bool moved: false

        onPressed: function (mouse) {
            root.forceActiveFocus()
            lastX = mouse.x
            lastY = mouse.y
            moved = false
            const part = root.viewport.beginVectorDrag(mouse.x, mouse.y)
            mode = part === "tip" ? "drag" : part === "shaft" ? "select" : "pan"
        }
        onPositionChanged: function (mouse) {
            if (pressed) {
                moved = moved || Math.abs(mouse.x - lastX) + Math.abs(mouse.y - lastY) > 0
                if (mode === "drag")
                    root.viewport.dragVector(mouse.x, mouse.y, (mouse.modifiers & Qt.ShiftModifier) !== 0)
                else if (mode === "pan")
                    root.viewport.panBy(mouse.x - lastX, mouse.y - lastY)
                lastX = mouse.x
                lastY = mouse.y
            } else {
                hoverPart = root.viewport.hitTest(mouse.x, mouse.y).part
            }
            root.viewport.setCursor(mouse.x, mouse.y)
        }
        onReleased: {
            if (mode === "drag")
                root.viewport.endVectorDrag()
            else if (mode === "pan" && !moved)
                app.scene.clearSelection()
            mode = ""
        }
        onCanceled: {
            if (mode === "drag")
                root.viewport.endVectorDrag()
            mode = ""
        }
        onWheel: function (wheel) {
            root.viewport.zoomAt(wheel.x, wheel.y, wheel.angleDelta.y)
        }
        onDoubleClicked: function (mouse) {
            if (root.viewport.hitTest(mouse.x, mouse.y).part === "")
                root.viewport.resetView()
        }
        onExited: {
            hoverPart = ""
            root.viewport.clearCursor()
        }
    }
}
