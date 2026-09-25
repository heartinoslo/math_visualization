import QtQuick

// A filled point centred on (centerX, centerY) in screen coordinates.
Rectangle {
    property real centerX: 0
    property real centerY: 0
    property real radius2D: 4

    x: centerX - radius2D
    y: centerY - radius2D
    width: radius2D * 2
    height: radius2D * 2
    radius: radius2D
    antialiasing: true
}
