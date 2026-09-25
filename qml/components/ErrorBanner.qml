import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    id: root
    property string message: ""
    signal dismissed()

    color: AppTheme.Theme.errorBackground
    border.color: AppTheme.Theme.errorBorder
    radius: AppTheme.Theme.panelRadius

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: AppTheme.Theme.spacingMedium
        anchors.rightMargin: AppTheme.Theme.spacingSmall
        spacing: AppTheme.Theme.spacingMedium

        Label {
            objectName: "errorMessageLabel"
            Layout.fillWidth: true
            text: root.message
            color: AppTheme.Theme.errorText
            font.pixelSize: 12
            elide: Text.ElideRight
        }

        ToolButton {
            objectName: "errorDismissButton"
            text: "Dismiss"
            implicitHeight: AppTheme.Theme.compactControlHeight
            onClicked: root.dismissed()
        }
    }
}
