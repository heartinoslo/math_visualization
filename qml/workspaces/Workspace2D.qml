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
    }
}
