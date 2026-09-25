import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    objectName: "workspace2D"
    color: AppTheme.Theme.workspaceBackground

    ColumnLayout {
        anchors.centerIn: parent
        spacing: AppTheme.Theme.spacingSmall

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "2D Workspace"
            color: AppTheme.Theme.primaryText
            font.pixelSize: 20
            font.weight: Font.DemiBold
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "Visualization placeholder"
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 13
        }

        Label {
            objectName: "camera2DSummary"
            Layout.alignment: Qt.AlignHCenter
            text: "Camera: center (" + app.workspace.camera2D.centerX.toFixed(2) + ", "
                + app.workspace.camera2D.centerY.toFixed(2) + "), zoom "
                + app.workspace.camera2D.zoom.toFixed(2)
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
        }
    }
}
