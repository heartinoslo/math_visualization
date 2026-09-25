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

        // 2D viewport readout: camera state and the pointer's mathematical position.
        Label {
            objectName: "camera2DSummary"
            visible: app.workspace.workspaceMode === "2d"
            text: app.viewport2D.cameraSummary
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
        }

        Label {
            objectName: "cursorCoordinates"
            visible: app.workspace.workspaceMode === "2d" && text !== ""
            text: app.viewport2D.cursorText
            color: AppTheme.Theme.primaryText
            font.pixelSize: 12
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
