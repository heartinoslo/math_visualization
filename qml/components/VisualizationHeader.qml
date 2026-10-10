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
    signal resetViewRequested()

    // The selected workspace is marked with the accent colour so the choice
    // stays unambiguous regardless of the platform control style.
    component WorkspaceTab: TabButton {
        id: tab
        implicitWidth: 44
        implicitHeight: AppTheme.Theme.controlHeight

        contentItem: Text {
            text: tab.text
            font: tab.font
            color: tab.checked ? "#FFFFFF" : AppTheme.Theme.secondaryText
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: AppTheme.Theme.panelRadius
            color: tab.checked
                ? AppTheme.Theme.accentColor
                : (tab.hovered ? AppTheme.Theme.surfaceLevelTwo : "transparent")
        }
    }

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

        Button {
            objectName: "resetViewButton"
            text: "Reset view"
            implicitHeight: AppTheme.Theme.controlHeight
            onClicked: root.resetViewRequested()
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
            currentIndex: root.workspaceMode === "3d" ? 1 : root.workspaceMode === "algebra" ? 2 : 0
            implicitHeight: AppTheme.Theme.controlHeight
            spacing: 2
            background: Rectangle {
                radius: AppTheme.Theme.panelRadius
                color: AppTheme.Theme.windowBackground
                border.color: AppTheme.Theme.borderColor
            }
            onCurrentIndexChanged: root.workspaceModeRequested(["2d", "3d", "algebra"][currentIndex])

            WorkspaceTab {
                objectName: "workspace2DTab"
                text: "2D"
            }

            WorkspaceTab {
                objectName: "workspace3DTab"
                text: "3D"
            }

            WorkspaceTab {
                objectName: "workspaceAlgebraTab"
                text: "Algebra"
                implicitWidth: 70
            }
        }
    }
}
