import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: root

    width: 960
    height: 640
    visible: true
    title: "Math Visualization"

    Rectangle {
        anchors.fill: parent
        color: "#202124"

        Label {
            anchors.centerIn: parent
            text: "Math Visualization"
            color: "#F1F3F4"
            font.pixelSize: 28
        }
    }
}