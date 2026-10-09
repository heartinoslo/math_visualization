import QtQuick
import QtQuick.Controls
import "pages"
import "theme" as AppTheme

ApplicationWindow {
    id: root
    objectName: "applicationWindow"

    width: 1440
    height: 900
    minimumWidth: AppTheme.Theme.minimumWindowWidth
    minimumHeight: AppTheme.Theme.minimumWindowHeight
    visible: true
    title: "Math Visualization"
    color: AppTheme.Theme.windowBackground

    // Keep stock Qt Quick Controls legible in both themes.
    palette.window: AppTheme.Theme.windowBackground
    palette.windowText: AppTheme.Theme.primaryText
    palette.base: AppTheme.Theme.panelBackground
    palette.text: AppTheme.Theme.primaryText
    palette.button: AppTheme.Theme.surfaceLevelTwo
    palette.buttonText: AppTheme.Theme.primaryText
    palette.highlight: AppTheme.Theme.accentColor
    palette.highlightedText: "#FFFFFF"
    palette.placeholderText: AppTheme.Theme.secondaryText
    palette.toolTipBase: AppTheme.Theme.panelBackground
    palette.toolTipText: AppTheme.Theme.primaryText
    // Bevel shades used by the Fusion style.
    palette.light: Qt.lighter(AppTheme.Theme.surfaceLevelTwo, 1.25)
    palette.midlight: Qt.lighter(AppTheme.Theme.surfaceLevelTwo, 1.1)
    palette.mid: AppTheme.Theme.borderColor
    palette.dark: Qt.darker(AppTheme.Theme.surfaceLevelTwo, 1.4)
    palette.shadow: Qt.darker(AppTheme.Theme.windowBackground, 1.6)

    // Disabled controls fade towards the background so they read as inactive.
    // These bindings are installed after creation: declared inline, the style
    // resolves its own palette afterwards and the disabled group is lost until
    // the theme next changes.
    readonly property color disabledText: Qt.alpha(AppTheme.Theme.secondaryText, 0.45)
    Component.onCompleted: {
        palette.disabled.buttonText = Qt.binding(function () { return root.disabledText })
        palette.disabled.windowText = Qt.binding(function () { return root.disabledText })
        palette.disabled.text = Qt.binding(function () { return root.disabledText })
        palette.disabled.button = Qt.binding(function () { return AppTheme.Theme.panelBackground })
    }

    Binding {
        target: AppTheme.Theme
        property: "darkMode"
        value: app.themeMode === "dark"
    }

    // Delete removes the selected object. Text fields consume Delete
    // themselves while editing, so this never fires during typing.
    Shortcut {
        objectName: "deleteShortcut"
        sequences: [StandardKey.Delete]
        onActivated: app.scene.removeSelected()
    }

    // Frame clock for the transformation: one advance per rendered frame keeps
    // playback in step with the display.
    FrameAnimation {
        objectName: "playbackClock"
        running: app.animation.playing
        onTriggered: app.animation.advance(frameTime)
    }

    WorkspacePage {
        id: workspacePage
        anchors.fill: parent
    }

    // Test hooks for presentation-only behaviour; application state such as the
    // workspace mode lives in the Python view models and is driven through `app`.
    function testPythonConnection() {
        workspacePage.testPythonConnection()
    }

    function toggleExpressionDock() {
        workspacePage.toggleExpressionDock()
    }
}
