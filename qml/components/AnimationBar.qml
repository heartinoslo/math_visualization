import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: AppTheme.Theme.spacingLarge
        anchors.rightMargin: AppTheme.Theme.spacingLarge
        spacing: AppTheme.Theme.spacingMedium

        Label {
            text: "▶"
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 16
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: AppTheme.Theme.timelineTrackHeight
            radius: AppTheme.Theme.timelineTrackRadius
            color: AppTheme.Theme.surfaceLevelTwo

            Rectangle {
                width: parent.width * 0.35
                height: parent.height
                radius: parent.radius
                color: AppTheme.Theme.accentColor
            }

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                x: parent.width * 0.35 - width / 2
                width: AppTheme.Theme.timelineHandleSize
                height: AppTheme.Theme.timelineHandleSize
                radius: AppTheme.Theme.timelineHandleRadius
                color: AppTheme.Theme.primaryText
            }
        }

        Label {
            text: "0%"
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
        }
    }
}
