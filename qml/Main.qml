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

        Column {
            anchors.centerIn: parent
            spacing: 16

            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Math Visualization"
                color: "#F1F3F4"
                font.pixelSize: 28
            }

            Label {
                id: statusLabel
                objectName: "statusLabel"
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Status: " + app.statusMessage
                color: "#F1F3F4"
                font.pixelSize: 18
            }

            Button {
                objectName: "testPythonConnectionButton"
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Test Python Connection"
                onClicked: app.ping()
            }
        }
    }

    function testPythonConnection() {
        app.ping()
    }
}
