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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: AppTheme.Theme.spacingLarge
        spacing: AppTheme.Theme.spacingMedium

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

        Item {
            Layout.fillHeight: true
        }
    }
}
