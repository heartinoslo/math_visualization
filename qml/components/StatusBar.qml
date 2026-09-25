import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    id: root
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor

    function testPythonConnection() {
        app.ping()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: AppTheme.Theme.spacingMedium
        anchors.rightMargin: AppTheme.Theme.spacingMedium
        spacing: AppTheme.Theme.spacingMedium

        Label {
            id: statusLabel
            objectName: "statusLabel"
            Layout.fillWidth: true
            text: "Status: " + app.statusMessage
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
            elide: Text.ElideRight
        }

        Button {
            objectName: "testPythonConnectionButton"
            text: "Test Python Connection"
            implicitHeight: AppTheme.Theme.compactControlHeight
            font.pixelSize: 11
            onClicked: root.testPythonConnection()
        }
    }
}
