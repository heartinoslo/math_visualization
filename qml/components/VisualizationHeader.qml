import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    id: root
    property int workspaceIndex: 0
    signal workspaceSelected(int index)

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

        TabBar {
            id: workspaceTabs
            currentIndex: root.workspaceIndex
            implicitHeight: AppTheme.Theme.controlHeight
            onCurrentIndexChanged: root.workspaceSelected(currentIndex)

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
