import QtQuick
import QtQuick.Shapes

// A straight segment between two screen-space points.
Shape {
    id: root
    property real x1: 0
    property real y1: 0
    property real x2: 0
    property real y2: 0
    property color strokeColor: "white"
    property real lineWidth: 2

    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        strokeColor: root.strokeColor
        strokeWidth: root.lineWidth
        fillColor: "transparent"
        capStyle: ShapePath.RoundCap
        startX: root.x1
        startY: root.y1

        PathLine {
            x: root.x2
            y: root.y2
        }
    }
}
