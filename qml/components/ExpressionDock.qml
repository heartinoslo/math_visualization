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

        // The transformation as formulas. All text is produced in Python.
        ColumnLayout {
            objectName: "expressionContent"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: AppTheme.Theme.spacingLarge
            Layout.rightMargin: AppTheme.Theme.spacingLarge
            Layout.bottomMargin: AppTheme.Theme.spacingMedium
            visible: root.expanded
            spacing: 4

            component FormulaLabel: Label {
                Layout.fillWidth: true
                color: AppTheme.Theme.primaryText
                font.family: "monospace"
                font.pixelSize: 13
                elide: Text.ElideRight
            }

            FormulaLabel {
                objectName: "targetMatrixText"
                text: app.transformation.targetText
            }

            FormulaLabel {
                objectName: "parameterText"
                text: app.transformation.parameterText
            }

            FormulaLabel {
                objectName: "currentMatrixText"
                text: app.transformation.currentText
            }

            FormulaLabel {
                objectName: "selectedMappingText"
                visible: text !== ""
                text: app.transformation.selectedMappingText
            }

            Label {
                Layout.fillWidth: true
                Layout.topMargin: 2
                text: "Interpolation path: every point moves on a straight line from p to A·p, "
                    + "as in Manim's ApplyMatrix. This is the first path offered, not the only "
                    + "way to read the transformation."
                color: AppTheme.Theme.secondaryText
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }

            Item {
                Layout.fillHeight: true
            }
        }
    }
}
