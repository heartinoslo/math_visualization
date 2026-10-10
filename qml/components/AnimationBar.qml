import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

// Playback of the transformation. Time lives in app.animation; the frame
// clock that advances it is in Main.qml.
Rectangle {
    id: root
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor

    readonly property var animation: app.animation

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: AppTheme.Theme.spacingMedium
        anchors.rightMargin: AppTheme.Theme.spacingLarge
        spacing: AppTheme.Theme.spacingSmall

        ToolButton {
            objectName: "playPauseButton"
            text: root.animation.playing ? "❚❚" : "▶"
            font.pixelSize: 14
            implicitWidth: 34
            implicitHeight: AppTheme.Theme.compactControlHeight
            ToolTip.visible: hovered
            ToolTip.text: root.animation.playing ? "Pause" : "Play the transformation"
            onClicked: root.animation.togglePlaying()
        }

        ToolButton {
            objectName: "resetAnimationButton"
            text: "⏮"
            font.pixelSize: 14
            implicitWidth: 34
            implicitHeight: AppTheme.Theme.compactControlHeight
            ToolTip.visible: hovered
            ToolTip.text: "Back to the start (identity)"
            onClicked: root.animation.reset()
        }

        Slider {
            id: progressSlider
            objectName: "animationProgressSlider"
            Layout.fillWidth: true
            // The custom track and handle have no implicit height of their own;
            // without this the slider is 0 px tall and cannot be clicked or dragged.
            implicitHeight: AppTheme.Theme.compactControlHeight
            from: 0.0
            to: 1.0
            value: root.animation.progress
            onMoved: root.animation.scrub(value)

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
            Layout.preferredWidth: 38
            horizontalAlignment: Text.AlignRight
            text: Math.round(root.animation.progress * 100) + "%"
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
        }

        // Seconds per segment: the whole transformation, or each step of an operation.
        TextField {
            id: durationField
            objectName: "durationField"
            implicitHeight: AppTheme.Theme.compactControlHeight
            implicitWidth: 52
            font.pixelSize: 11
            horizontalAlignment: TextInput.AlignHCenter
            text: Number(root.animation.duration.toFixed(2)).toString()
            validator: DoubleValidator { bottom: 0.1; top: 60; decimals: 2 }
            onEditingFinished: {
                const seconds = parseFloat(text.replace(",", "."))
                if (seconds > 0)
                    root.animation.setDuration(seconds)
                text = Qt.binding(function () { return Number(root.animation.duration.toFixed(2)).toString() })
            }
            ToolTip.visible: hovered
            ToolTip.text: root.animation.segments > 1
                ? "Seconds per step (" + root.animation.segments + " steps, "
                    + root.animation.totalDuration.toFixed(1) + " s in all)"
                : "Seconds for the transformation"
        }

        Label {
            text: root.animation.segments > 1 ? "s / step" : "s"
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 11
        }

        ComboBox {
            objectName: "rateFunctionBox"
            implicitHeight: AppTheme.Theme.compactControlHeight
            implicitWidth: 92
            font.pixelSize: 11
            model: ["smooth", "linear"]
            currentIndex: Math.max(0, model.indexOf(root.animation.rateFunction))
            onActivated: function (index) { root.animation.setRateFunction(model[index]) }
            ToolTip.visible: hovered
            ToolTip.text: "Easing (Manim rate_func)"
        }

        ComboBox {
            objectName: "playbackSpeedBox"
            implicitHeight: AppTheme.Theme.compactControlHeight
            implicitWidth: 72
            font.pixelSize: 11
            model: root.animation.playbackSpeeds.map(function (speed) { return speed + "×" })
            currentIndex: Math.max(0, root.animation.playbackSpeeds.indexOf(root.animation.playbackSpeed))
            onActivated: function (index) { root.animation.setPlaybackSpeed(root.animation.playbackSpeeds[index]) }
        }
    }
}
