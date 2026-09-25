import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

Rectangle {
    id: root
    property bool expanded: true

    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor
    radius: AppTheme.Theme.panelRadius
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: AppTheme.Theme.expressionDockHeaderHeight
            Layout.leftMargin: AppTheme.Theme.spacingMedium
            Layout.rightMargin: AppTheme.Theme.spacingSmall
            spacing: AppTheme.Theme.spacingMedium

            Label {
                text: "Expression / Derivation"
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
                font.weight: Font.DemiBold
            }

            Item {
                Layout.fillWidth: true
            }

            ToolButton {
                id: expressionDockToggle
                objectName: "expressionDockToggle"
                text: root.expanded ? "Collapse" : "Expand"
                onClicked: root.expanded = !root.expanded
            }
        }

        Label {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: AppTheme.Theme.spacingLarge
            visible: root.expanded
            text: "Mathematical expressions and derivation steps will appear here."
            color: AppTheme.Theme.secondaryText
            wrapMode: Text.WordWrap
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 13
        }
    }
}
