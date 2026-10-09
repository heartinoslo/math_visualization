import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

// Matrix algebra: the focused operation laid out as matrices and operators,
// derived one step per playback segment. Everything shown comes from
// app.operations.algebraView; this file only draws it.
Rectangle {
    id: root
    objectName: "workspaceAlgebra"
    color: AppTheme.Theme.workspaceBackground
    clip: true

    readonly property var view: app.operations.algebraView
    readonly property bool hasOperation: app.operations.hasFocus

    function roleColor(role) {
        return role === "right" ? AppTheme.Theme.rightOperandColor
            : role === "result" ? AppTheme.Theme.resultColor
            : AppTheme.Theme.leftOperandColor
    }

    // One matrix in brackets; each cell is coloured by its state in the current step.
    component MatrixGrid: Item {
        id: grid
        property var term
        readonly property int size: term.size
        readonly property real cellWidth: 58
        readonly property real cellHeight: 40
        implicitWidth: cellGrid.implicitWidth + 24
        implicitHeight: cellGrid.implicitHeight + nameLabel.implicitHeight + 6

        Grid {
            id: cellGrid
            x: 12
            columns: grid.size
            spacing: 2

            Repeater {
                model: grid.term.cells
                delegate: Rectangle {
                    required property var modelData
                    readonly property string state: modelData.state
                    readonly property color tone: state === "minor" ? AppTheme.Theme.rightOperandColor
                        : state === "pivot" ? AppTheme.Theme.leftOperandColor
                        : root.roleColor(grid.term.role)
                    readonly property bool lit: state === "active" || state === "pivot" || state === "minor"
                    width: grid.cellWidth
                    height: grid.cellHeight
                    radius: 4
                    color: lit ? Qt.alpha(tone, 0.28) : "transparent"
                    border.color: lit ? tone : "transparent"
                    border.width: state === "pivot" ? 2 : 1

                    Label {
                        anchors.centerIn: parent
                        text: parent.modelData.text
                        font.pixelSize: 18
                        font.family: "monospace"
                        color: parent.state === "hidden" ? AppTheme.Theme.secondaryText : AppTheme.Theme.primaryText
                        opacity: parent.state === "dim" ? 0.3 : 1.0
                    }
                }
            }
        }

        // Square brackets.
        Repeater {
            model: 2
            delegate: Rectangle {
                required property int index
                x: index === 0 ? 2 : grid.width - 10
                y: -2
                width: 8
                height: cellGrid.height + 4
                color: "transparent"
                border.color: AppTheme.Theme.primaryText
                border.width: 2
                // Hide the inner side so each bracket is open towards the entries.
                Rectangle {
                    x: parent.index === 0 ? 4 : -1
                    y: 2
                    width: 6
                    height: parent.height - 4
                    color: root.color
                }
            }
        }

        Label {
            id: nameLabel
            anchors.top: cellGrid.bottom
            anchors.topMargin: 6
            anchors.horizontalCenter: cellGrid.horizontalCenter
            text: grid.term.name + (grid.term.superscript ? "ᵀ" : "")
            color: root.roleColor(grid.term.role)
            font.pixelSize: 15
            font.bold: true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: AppTheme.Theme.spacingLarge
        spacing: AppTheme.Theme.spacingLarge

        Label {
            objectName: "algebraTitle"
            Layout.alignment: Qt.AlignHCenter
            text: root.view.title || ""
            color: AppTheme.Theme.primaryText
            font.pixelSize: 20
            font.bold: true
        }

        Item { Layout.fillHeight: true }

        // The operation: matrices, operators and numbers in a row.
        Row {
            objectName: "algebraTerms"
            Layout.alignment: Qt.AlignHCenter
            spacing: 14

            Repeater {
                model: root.view.terms || []
                delegate: Loader {
                    required property var modelData
                    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                    sourceComponent: modelData.type === "matrix" ? matrixTerm : textTerm

                    Component {
                        id: matrixTerm
                        MatrixGrid { term: modelData }
                    }

                    Component {
                        id: textTerm
                        Label {
                            text: modelData.text
                            color: modelData.type === "number" ? AppTheme.Theme.resultColor : AppTheme.Theme.primaryText
                            font.pixelSize: modelData.type === "number" ? 26 : 24
                            font.bold: modelData.type === "number"
                            bottomPadding: 22
                        }
                    }
                }
            }
        }

        // The arithmetic of the current step.
        Label {
            objectName: "algebraFormula"
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: root.width - 2 * AppTheme.Theme.spacingLarge
            visible: text !== ""
            text: root.view.formula || ""
            color: AppTheme.Theme.primaryText
            font.pixelSize: 18
            font.family: "monospace"
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            visible: root.hasOperation
            spacing: AppTheme.Theme.spacingMedium

            Button {
                objectName: "previousStepButton"
                text: "◀ Previous"
                implicitHeight: AppTheme.Theme.compactControlHeight
                onClicked: app.operations.previousStep()
            }
            Label {
                objectName: "algebraStep"
                text: "Step " + root.view.step + " / " + root.view.stepCount
                color: AppTheme.Theme.secondaryText
                font.pixelSize: 13
            }
            Button {
                objectName: "nextStepButton"
                text: "Next ▶"
                implicitHeight: AppTheme.Theme.compactControlHeight
                onClicked: app.operations.nextStep()
            }
        }

        // Steps already done, faded, newest last.
        Column {
            objectName: "algebraHistory"
            Layout.alignment: Qt.AlignHCenter
            spacing: 2

            Repeater {
                model: root.view.history || []
                delegate: Label {
                    required property string modelData
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: modelData
                    color: AppTheme.Theme.secondaryText
                    font.pixelSize: 13
                    font.family: "monospace"
                }
            }
        }

        Label {
            objectName: "algebraHint"
            Layout.alignment: Qt.AlignHCenter
            visible: !root.hasOperation
            text: "Compute an operation in the right panel (OPERATIONS) to see it worked out step by step."
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 13
        }

        Item { Layout.fillHeight: true }
    }
}
