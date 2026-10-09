import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

// Offered at startup when the previous session ended with unsaved work.
Rectangle {
    id: root
    signal restoreRequested()
    signal discardRequested()

    color: Qt.alpha(AppTheme.Theme.warningColor, 0.14)
    border.color: AppTheme.Theme.warningColor
    radius: AppTheme.Theme.panelRadius

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: AppTheme.Theme.spacingMedium
        anchors.rightMargin: AppTheme.Theme.spacingSmall
        spacing: AppTheme.Theme.spacingMedium

        Label {
            Layout.fillWidth: true
            text: "The last session ended with unsaved work. Restore it?"
            color: AppTheme.Theme.primaryText
            font.pixelSize: 12
            elide: Text.ElideRight
        }

        Button {
            objectName: "restoreRecoveryButton"
            text: "Restore"
            implicitHeight: AppTheme.Theme.compactControlHeight
            onClicked: root.restoreRequested()
        }

        ToolButton {
            objectName: "discardRecoveryButton"
            text: "Discard"
            implicitHeight: AppTheme.Theme.compactControlHeight
            onClicked: root.discardRequested()
        }
    }
}
