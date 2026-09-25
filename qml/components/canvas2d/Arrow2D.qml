import QtQuick
import QtQuick.Shapes

// An arrow from (x1, y1) to (x2, y2) in screen coordinates. The head keeps a
// constant on-screen size; a zero-length arrow draws nothing.
Shape {
    id: root
    property real x1: 0
    property real y1: 0
    property real x2: 0
    property real y2: 0
    property color strokeColor: "white"
    property real lineWidth: 2
    property real headLength: 12
    property real headHalfWidth: 5

    readonly property real length: Math.hypot(x2 - x1, y2 - y1)
    readonly property real unitX: length > 0 ? (x2 - x1) / length : 0
    readonly property real unitY: length > 0 ? (y2 - y1) / length : 0
    readonly property real effectiveHeadLength: Math.min(headLength, length)
    readonly property real baseX: x2 - unitX * effectiveHeadLength
    readonly property real baseY: y2 - unitY * effectiveHeadLength

    anchors.fill: parent
    visible: length > 0
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        strokeColor: root.strokeColor
        strokeWidth: root.lineWidth
        fillColor: "transparent"
        capStyle: ShapePath.RoundCap
        startX: root.x1
        startY: root.y1

        PathLine {
            x: root.baseX
            y: root.baseY
        }
    }

    ShapePath {
        strokeColor: "transparent"
        fillColor: root.strokeColor
        startX: root.x2
        startY: root.y2

        PathLine {
            x: root.baseX - root.unitY * root.headHalfWidth
            y: root.baseY + root.unitX * root.headHalfWidth
        }
        PathLine {
            x: root.baseX + root.unitY * root.headHalfWidth
            y: root.baseY - root.unitX * root.headHalfWidth
        }
        PathLine {
            x: root.x2
            y: root.y2
        }
    }
}
