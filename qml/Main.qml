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

    WorkspacePage {
        id: workspacePage
        anchors.fill: parent
    }

    // These test hooks retain the Stage 0 bridge coverage without putting
    // application state into QML. The workspace selection is presentation-only.
    function testPythonConnection() {
        workspacePage.testPythonConnection()
    }

    function toggleExpressionDock() {
        workspacePage.toggleExpressionDock()
    }

    function setPresentationWorkspace(index) {
        workspacePage.setPresentationWorkspace(index)
    }
}
