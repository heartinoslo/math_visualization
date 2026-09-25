import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: AppTheme.Theme.spacingLarge
        spacing: AppTheme.Theme.spacingSmall

        Label {
            text: "RIGHT PANEL"
            color: AppTheme.Theme.primaryText
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }

        Label {
            Layout.fillWidth: true
            text: "Content will be defined later"
            color: AppTheme.Theme.secondaryText
            wrapMode: Text.WordWrap
            font.pixelSize: 12
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
