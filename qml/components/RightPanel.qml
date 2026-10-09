import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

// Properties of the selected vector. Every value is text from
// app.inspector; edits are sent back as text and validated in Python.
Rectangle {
    id: root
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor
    clip: true

    readonly property var inspector: app.inspector
    readonly property var matrixProperties: app.matrixProperties

    component FieldLabel: Label {
        color: AppTheme.Theme.secondaryText
        font.pixelSize: 12
    }

    // A text field showing a Python-formatted value. After editing, the
    // binding is restored so a rejected value snaps back to the real one.
    component ValueField: TextField {
        id: field
        property string value: ""
        property var commit: function (text) {}
        Layout.fillWidth: true
        text: value
        selectByMouse: true
        font.pixelSize: 13
        onEditingFinished: {
            commit(text)
            text = Qt.binding(function () { return field.value })
        }
    }

    component SectionTitle: Label {
        color: AppTheme.Theme.primaryText
        font.pixelSize: 13
        font.weight: Font.DemiBold
    }

    ScrollView {
        id: scroller
        anchors.fill: parent
        anchors.margins: AppTheme.Theme.spacingLarge
        contentWidth: availableWidth
        clip: true

    ColumnLayout {
        width: scroller.availableWidth
        spacing: AppTheme.Theme.spacingMedium

        // The active matrix ----------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: AppTheme.Theme.spacingMedium

            SectionTitle {
                text: "MATRIX"
            }

            ValueField {
                objectName: "matrixNameField"
                visible: app.transformation.hasMatrix
                Layout.maximumWidth: 120
                value: app.transformation.matrixName
                maximumLength: 24
                font.bold: true
                commit: function (text) { app.matrices.rename(app.matrices.activeId, text) }
                ToolTip.visible: hovered
                ToolTip.text: "Name of the active matrix"
            }

            Item { Layout.fillWidth: true }
        }

        Label {
            objectName: "noMatrixHint"
            Layout.fillWidth: true
            visible: !app.transformation.hasMatrix
            text: "No matrix. Add one with “+ Matrix” on the left."
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        GridLayout {
            objectName: "matrixEditor"
            enabled: app.transformation.hasMatrix
            Layout.fillWidth: true
            columns: app.transformation.matrixSize
            columnSpacing: AppTheme.Theme.spacingSmall
            rowSpacing: AppTheme.Theme.spacingSmall

            // Entries row by row; objectNames run matrixEntryA, B, C, … in that order.
            Repeater {
                model: app.transformation.entryTexts.length
                delegate: ValueField {
                    required property int index
                    readonly property int size: app.transformation.matrixSize
                    objectName: "matrixEntry" + "ABCDEFGHI"[index]
                    horizontalAlignment: TextInput.AlignHCenter
                    value: app.transformation.entryTexts[index] || ""
                    commit: function (text) { app.transformation.setEntryText(index, text) }
                    ToolTip.visible: hovered
                    ToolTip.text: "Row " + (Math.floor(index / size) + 1) + ", column " + (index % size + 1)
                        + " (column " + (index % size + 1) + " is where basis vector " + ["î", "ĵ", "k̂"][index % size] + " goes)"
                }
            }
        }

        Flow {
            objectName: "matrixPresets"
            enabled: app.transformation.hasMatrix
            Layout.fillWidth: true
            spacing: 4

            Repeater {
                model: app.transformation.presets
                delegate: Button {
                    required property var modelData
                    objectName: "preset_" + modelData.key
                    text: modelData.label
                    implicitHeight: AppTheme.Theme.compactControlHeight
                    font.pixelSize: 11
                    onClicked: app.transformation.applyPreset(modelData.key)
                }
            }
        }

        GridLayout {
            objectName: "visualToggles"
            // These options belong to the plane transformation of a 2×2 matrix.
            enabled: app.transformation.showsTransformation
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 0
            rowSpacing: 0

            Repeater {
                model: [
                    { key: "show_transformed_grid", label: "Grid", tip: "Transformed grid" },
                    { key: "show_unit_square", label: "Square", tip: "Unit square A·[0,1]²" },
                    { key: "show_basis_vectors", label: "î, ĵ", tip: "Transformed basis vectors (the columns of A)" },
                    { key: "show_ghosts", label: "Ghosts", tip: "Faint input vectors; drag them to edit" },
                    { key: "show_orientation_arc", label: "Turn î→ĵ", tip: "Arc from î to ĵ: it turns the other way when det < 0" },
                    { key: "show_flip_tint", label: "Flip tint", tip: "Tint the unit square when det < 0 (orientation reversed)" },
                    { key: "show_kernel", label: "Kernel", tip: "Null space of a singular A: the inputs sent to the origin" }
                ]
                delegate: CheckBox {
                    required property var modelData
                    objectName: "toggle_" + modelData.key
                    Layout.fillWidth: true
                    text: modelData.label
                    font.pixelSize: 12
                    checked: app.transformation.visualState[modelData.key]
                    onToggled: app.transformation.setVisualFlag(modelData.key, checked)
                    ToolTip.visible: hovered
                    ToolTip.text: modelData.tip
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: AppTheme.Theme.spacingSmall
            height: 1
            color: AppTheme.Theme.borderColor
        }

        // Matrix operations -------------------------------------------------------
        SectionTitle {
            text: "OPERATIONS"
        }

        ColumnLayout {
            objectName: "operationForm"
            Layout.fillWidth: true
            spacing: AppTheme.Theme.spacingSmall
            readonly property var kind: app.operations.kinds[kindBox.currentIndex]
            readonly property var choices: app.operations.operandChoices

            ComboBox {
                id: kindBox
                objectName: "operationKind"
                Layout.fillWidth: true
                model: app.operations.kinds
                textRole: "label"
                font.pixelSize: 12
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: AppTheme.Theme.spacingSmall

                TextField {
                    id: scalarField
                    objectName: "operationScalar"
                    visible: parent.parent.kind.needsScalar
                    Layout.preferredWidth: 56
                    placeholderText: "k"
                    text: "2"
                    horizontalAlignment: TextInput.AlignHCenter
                    font.pixelSize: 12
                }
                ComboBox {
                    id: leftBox
                    objectName: "operandLeft"
                    Layout.fillWidth: true
                    model: parent.parent.choices
                    textRole: "label"
                    font.pixelSize: 12
                }
                ComboBox {
                    id: rightBox
                    objectName: "operandRight"
                    visible: parent.parent.kind.operands === 2
                    Layout.fillWidth: true
                    model: parent.parent.choices
                    textRole: "label"
                    currentIndex: Math.min(1, count - 1)
                    font.pixelSize: 12
                }
            }

            Button {
                objectName: "computeButton"
                Layout.fillWidth: true
                text: "Compute"
                highlighted: true
                enabled: parent.choices.length > 0
                implicitHeight: AppTheme.Theme.compactControlHeight
                font.pixelSize: 12
                onClicked: {
                    const choices = parent.choices
                    const left = leftBox.currentIndex >= 0 ? choices[leftBox.currentIndex].id : ""
                    const right = rightBox.currentIndex >= 0 ? choices[rightBox.currentIndex].id : ""
                    app.operations.compute(parent.kind.key, left, right, scalarField.text)
                }
                ToolTip.visible: hovered
                ToolTip.text: "The result becomes a new matrix; open the Algebra tab to see each step."
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: AppTheme.Theme.spacingSmall
            height: 1
            color: AppTheme.Theme.borderColor
        }

        // Determinant, rank and invertibility of A ---------------------------
        SectionTitle {
            text: "DETERMINANT & RANK"
        }

        Rectangle {
            objectName: "matrixStatusBadge"
            readonly property color tone: root.matrixProperties.status === "regular" ? AppTheme.Theme.successColor
                : root.matrixProperties.status === "near_singular" ? AppTheme.Theme.warningColor
                : AppTheme.Theme.flippedSquareColor
            Layout.fillWidth: true
            implicitHeight: statusColumn.implicitHeight + 2 * AppTheme.Theme.spacingSmall
            radius: 4
            color: Qt.alpha(tone, 0.14)
            border.color: tone

            ColumnLayout {
                id: statusColumn
                anchors.fill: parent
                anchors.margins: AppTheme.Theme.spacingSmall
                spacing: 2

                Label {
                    objectName: "matrixStatusText"
                    text: root.matrixProperties.statusText
                    color: parent.parent.tone
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }

                Label {
                    objectName: "matrixStatusDetail"
                    Layout.fillWidth: true
                    text: root.matrixProperties.statusDetail
                    color: AppTheme.Theme.primaryText
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
        }

        GridLayout {
            objectName: "matrixProperties"
            Layout.fillWidth: true
            columns: 2
            columnSpacing: AppTheme.Theme.spacingMedium
            rowSpacing: 3

            FieldLabel { text: "det " + app.transformation.matrixName }
            Label {
                objectName: "determinantValue"
                text: root.matrixProperties.determinantText
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
            }

            FieldLabel { text: root.matrixProperties.size === 3 ? "Volume" : "Area" }
            Label {
                objectName: "areaScaleValue"
                text: root.matrixProperties.areaScaleText
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
            }

            FieldLabel { text: "Orientation" }
            Label {
                objectName: "orientationValue"
                text: root.matrixProperties.orientationText
                color: root.matrixProperties.orientation === "reversed"
                    ? AppTheme.Theme.flippedSquareColor : AppTheme.Theme.primaryText
                font.pixelSize: 13
            }

            FieldLabel { text: "Rank" }
            Label {
                objectName: "rankValue"
                text: root.matrixProperties.rank + (root.matrixProperties.invertible ? "  (invertible)" : "  (not invertible)")
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
            }

            FieldLabel {
                text: "κ"
                ToolTip.visible: conditionArea.containsMouse
                ToolTip.text: "Condition number σ_max / σ_min: how much A⁻¹ can amplify errors"
                MouseArea {
                    id: conditionArea
                    anchors.fill: parent
                    hoverEnabled: true
                }
            }
            Label {
                objectName: "conditionValue"
                text: root.matrixProperties.conditionText
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
            }

            FieldLabel { text: app.transformation.matrixName + "⁻¹" ; Layout.alignment: Qt.AlignTop }
            Item {
                Layout.fillWidth: true
                implicitHeight: root.matrixProperties.invertible ? inverseGrid.implicitHeight : noInverse.implicitHeight

                GridLayout {
                    id: inverseGrid
                    objectName: "inverseMatrix"
                    visible: root.matrixProperties.invertible
                    columns: root.matrixProperties.size
                    columnSpacing: AppTheme.Theme.spacingMedium
                    rowSpacing: 0

                    Repeater {
                        model: root.matrixProperties.inverseEntryTexts
                        delegate: Label {
                            required property string modelData
                            text: modelData
                            color: AppTheme.Theme.primaryText
                            font.pixelSize: 13
                            font.family: "monospace"
                        }
                    }
                }

                Label {
                    id: noInverse
                    objectName: "noInverseText"
                    visible: !root.matrixProperties.invertible
                    text: "none (det " + app.transformation.matrixName + " = 0)"
                    color: AppTheme.Theme.secondaryText
                    font.pixelSize: 13
                }
            }
        }

        Button {
            objectName: "applyInverseButton"
            text: "Apply " + app.transformation.matrixName + "⁻¹"
            implicitHeight: AppTheme.Theme.compactControlHeight
            font.pixelSize: 12
            enabled: root.matrixProperties.invertible
            onClicked: root.matrixProperties.applyInverse()
            ToolTip.visible: hovered
            ToolTip.text: "Replace " + app.transformation.matrixName + " by its inverse (undoable)"
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: AppTheme.Theme.spacingSmall
            height: 1
            color: AppTheme.Theme.borderColor
        }

        // Selected vector ---------------------------------------------------
        Label {
            text: "PROPERTIES"
            color: AppTheme.Theme.primaryText
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }

        Label {
            objectName: "noSelectionHint"
            Layout.fillWidth: true
            visible: !root.inspector.hasSelection
            text: "Select a vector to edit its properties."
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        GridLayout {
            objectName: "vectorInspector"
            Layout.fillWidth: true
            visible: root.inspector.hasSelection
            columns: 2
            columnSpacing: AppTheme.Theme.spacingMedium
            rowSpacing: AppTheme.Theme.spacingSmall

            FieldLabel { text: "Name" }
            ValueField {
                objectName: "nameField"
                value: root.inspector.name
                commit: function (text) { root.inspector.setName(text) }
                maximumLength: 24
            }

            FieldLabel { text: "Color" }
            Flow {
                objectName: "colorSwatches"
                Layout.fillWidth: true
                spacing: 4

                Repeater {
                    model: root.inspector.palette
                    delegate: Rectangle {
                        required property string modelData
                        width: 18
                        height: 18
                        radius: 9
                        color: modelData
                        border.width: modelData === root.inspector.color ? 2 : 0
                        border.color: AppTheme.Theme.primaryText

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.inspector.setColor(parent.modelData)
                        }
                    }
                }
            }

            FieldLabel { text: "x" ; font.italic: true }
            ValueField {
                objectName: "xField"
                value: root.inspector.xText
                commit: function (text) { root.inspector.setXText(text) }
            }

            FieldLabel { text: "y" ; font.italic: true }
            ValueField {
                objectName: "yField"
                value: root.inspector.yText
                commit: function (text) { root.inspector.setYText(text) }
            }

            FieldLabel { text: "Length" }
            Label {
                objectName: "lengthValue"
                text: root.inspector.lengthText
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
            }

            FieldLabel { text: "Direction" }
            Label {
                objectName: "angleValue"
                Layout.fillWidth: true
                text: root.inspector.angleText
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
                wrapMode: Text.WordWrap
            }
        }

    }
    }
}
