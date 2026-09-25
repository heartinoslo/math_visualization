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

    Binding {
        target: AppTheme.Theme
        property: "darkMode"
        value: app.themeMode === "dark"
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
