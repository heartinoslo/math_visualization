import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    id: root
    property string workspaceMode: "2d"
    property string themeMode: "dark"
    signal workspaceModeRequested(string mode)
    signal themeToggleRequested()

    implicitHeight: AppTheme.Theme.visualizationHeaderHeight
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: AppTheme.Theme.spacingMedium
        anchors.rightMargin: AppTheme.Theme.spacingMedium
        spacing: AppTheme.Theme.spacingMedium

        Label {
            text: "Visualization"
            color: AppTheme.Theme.primaryText
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }

        Item {
            Layout.fillWidth: true
        }

        ToolButton {
            objectName: "themeToggleButton"
            text: root.themeMode === "dark" ? "Light theme" : "Dark theme"
            implicitHeight: AppTheme.Theme.controlHeight
            onClicked: root.themeToggleRequested()
        }

        TabBar {
            id: workspaceTabs
            objectName: "workspaceTabs"
            currentIndex: root.workspaceMode === "3d" ? 1 : 0
            implicitHeight: AppTheme.Theme.controlHeight
            onCurrentIndexChanged: root.workspaceModeRequested(currentIndex === 1 ? "3d" : "2d")

            TabButton {
                objectName: "workspace2DTab"
                text: "2D"
            }

            TabButton {
                objectName: "workspace3DTab"
                text: "3D"
            }
        }
    }
}
