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

        // Matrix A of the transformation -------------------------------------
        SectionTitle {
            text: "MATRIX  A"
        }

        GridLayout {
            objectName: "matrixEditor"
            Layout.fillWidth: true
            columns: 2
            columnSpacing: AppTheme.Theme.spacingSmall
            rowSpacing: AppTheme.Theme.spacingSmall

            Repeater {
                model: ["a", "b", "c", "d"]
                delegate: ValueField {
                    required property int index
                    required property string modelData
                    objectName: "matrixEntry" + modelData.toUpperCase()
                    horizontalAlignment: TextInput.AlignHCenter
                    value: app.transformation.entryTexts[index]
                    commit: function (text) { app.transformation.setEntryText(index, text) }
                    ToolTip.visible: hovered
                    ToolTip.text: "Entry " + modelData + (index % 2 === 0
                        ? " (first column: where î goes)" : " (second column: where ĵ goes)")
                }
            }
        }

        Flow {
            objectName: "matrixPresets"
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

            FieldLabel { text: "det A" }
            Label {
                objectName: "determinantValue"
                text: root.matrixProperties.determinantText
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
            }

            FieldLabel { text: "Area" }
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

            FieldLabel { text: "A⁻¹" ; Layout.alignment: Qt.AlignTop }
            Item {
                Layout.fillWidth: true
                implicitHeight: root.matrixProperties.invertible ? inverseGrid.implicitHeight : noInverse.implicitHeight

                GridLayout {
                    id: inverseGrid
                    objectName: "inverseMatrix"
                    visible: root.matrixProperties.invertible
                    columns: 2
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
                    text: "none (det A = 0)"
                    color: AppTheme.Theme.secondaryText
                    font.pixelSize: 13
                }
            }
        }

        Button {
            objectName: "applyInverseButton"
            text: "Apply A⁻¹"
            implicitHeight: AppTheme.Theme.compactControlHeight
            font.pixelSize: 12
            enabled: root.matrixProperties.invertible
            onClicked: root.matrixProperties.applyInverse()
            ToolTip.visible: hovered
            ToolTip.text: "Replace A by its inverse (undoable)"
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
