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

        Slider {
            id: progressSlider
            objectName: "animationProgressSlider"
            Layout.fillWidth: true
            from: 0.0
            to: 1.0
            value: app.animation.progress
            onMoved: app.animation.setProgress(value)

            background: Rectangle {
                x: progressSlider.leftPadding
                y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                width: progressSlider.availableWidth
                height: AppTheme.Theme.timelineTrackHeight
                radius: AppTheme.Theme.timelineTrackRadius
                color: AppTheme.Theme.surfaceLevelTwo

                Rectangle {
                    width: progressSlider.visualPosition * parent.width
                    height: parent.height
                    radius: parent.radius
                    color: AppTheme.Theme.accentColor
                }
            }

            handle: Rectangle {
                x: progressSlider.leftPadding + progressSlider.visualPosition * (progressSlider.availableWidth - width)
                y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                width: AppTheme.Theme.timelineHandleSize
                height: AppTheme.Theme.timelineHandleSize
                radius: AppTheme.Theme.timelineHandleRadius
                color: AppTheme.Theme.primaryText
            }
        }

        Label {
            objectName: "animationProgressLabel"
            text: Math.round(app.animation.progress * 100) + "%"
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
        }
    }
}
