import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    objectName: "workspace3D"
    color: AppTheme.Theme.workspaceBackground

    ColumnLayout {
        anchors.centerIn: parent
        spacing: AppTheme.Theme.spacingSmall

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "3D Workspace"
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
            objectName: "camera3DSummary"
            Layout.alignment: Qt.AlignHCenter
            text: "Camera: azimuth " + app.workspace.camera3D.azimuth.toFixed(1)
                + "°, elevation " + app.workspace.camera3D.elevation.toFixed(1)
                + "°, distance " + app.workspace.camera3D.distance.toFixed(2)
                + ", " + app.workspace.camera3D.projectionMode
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
        }
    }
}
