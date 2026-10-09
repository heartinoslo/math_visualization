import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

// Scene objects: vectors (selected for editing) and matrices (the active one
// is edited in the right panel and played by the animation).
Rectangle {
    id: root
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor
    clip: true

    component SectionHeader: RowLayout {
        id: header
        property string title: ""
        property alias addText: addButton.text
        property alias addObjectName: addButton.objectName
        property alias addTip: addButton.tipText
        signal addClicked()
        Layout.fillWidth: true
        spacing: AppTheme.Theme.spacingSmall

        Label {
            Layout.fillWidth: true
            text: header.title
            color: AppTheme.Theme.secondaryText
            font.pixelSize: 11
            font.weight: Font.DemiBold
            font.letterSpacing: 0.5
        }

        ToolButton {
            id: addButton
            property string tipText: ""
            implicitHeight: AppTheme.Theme.compactControlHeight
            font.pixelSize: 12
            ToolTip.visible: hovered
            ToolTip.text: tipText
            onClicked: header.addClicked()
        }
    }

    component ActionRow: RowLayout {
        id: actions
        property bool actionsEnabled: false
        property alias duplicateName: duplicateButton.objectName
        property alias deleteName: deleteButton.objectName
        signal duplicateClicked()
        signal deleteClicked()
        Layout.fillWidth: true
        spacing: AppTheme.Theme.spacingSmall

        Button {
            id: duplicateButton
            Layout.fillWidth: true
            text: "Duplicate"
            enabled: actions.actionsEnabled
            implicitHeight: AppTheme.Theme.compactControlHeight
            font.pixelSize: 11
            onClicked: actions.duplicateClicked()
        }

        Button {
            id: deleteButton
            Layout.fillWidth: true
            text: "Delete"
            enabled: actions.actionsEnabled
            implicitHeight: AppTheme.Theme.compactControlHeight
            font.pixelSize: 11
            onClicked: actions.deleteClicked()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: AppTheme.Theme.spacingLarge
        spacing: AppTheme.Theme.spacingSmall

        Label {
            text: "OBJECTS"
            color: AppTheme.Theme.primaryText
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }

        // Vectors ------------------------------------------------------------
        SectionHeader {
            title: "VECTORS"
            addText: "+ Vector"
            addObjectName: "addVectorButton"
            addTip: "Add a vector at (1, 1)"
            onAddClicked: app.scene.addVector()
        }

        ListView {
            id: vectorList
            objectName: "vectorList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 64
            clip: true
            spacing: 2
            model: app.scene.vectorModel
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: row
                required property string objectId
                required property string name
                required property string vectorColor
                required property string componentsText
                required property bool selected

                width: ListView.view.width
                height: 30
                radius: AppTheme.Theme.panelRadius
                color: selected ? AppTheme.Theme.surfaceLevelTwo
                    : rowMouse.containsMouse ? Qt.rgba(0.5, 0.5, 0.5, 0.08) : "transparent"
                border.color: selected ? row.vectorColor : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: AppTheme.Theme.spacingSmall
                    anchors.rightMargin: AppTheme.Theme.spacingSmall
                    spacing: AppTheme.Theme.spacingSmall

                    Rectangle {
                        width: 10
                        height: 10
                        radius: 5
                        color: row.vectorColor
                    }

                    Label {
                        text: row.name
                        color: AppTheme.Theme.primaryText
                        font.pixelSize: 13
                        font.italic: true
                        font.bold: row.selected
                    }

                    Label {
                        Layout.fillWidth: true
                        text: row.componentsText
                        color: AppTheme.Theme.secondaryText
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: app.scene.select(row.objectId)
                }
            }

            Label {
                objectName: "emptyObjectsHint"
                anchors.fill: parent
                visible: vectorList.count === 0
                text: "No vectors yet.\nUse “+ Vector” to add one."
                color: AppTheme.Theme.secondaryText
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        ActionRow {
            duplicateName: "duplicateVectorButton"
            deleteName: "deleteVectorButton"
            actionsEnabled: app.scene.selectedId !== ""
            onDuplicateClicked: app.scene.duplicateSelected()
            onDeleteClicked: app.scene.removeSelected()
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: AppTheme.Theme.spacingSmall
            Layout.bottomMargin: AppTheme.Theme.spacingSmall
            height: 1
            color: AppTheme.Theme.borderColor
        }

        // Matrices -----------------------------------------------------------
        SectionHeader {
            title: "MATRICES"
            addText: "+ Matrix"
            addObjectName: "addMatrixButton"
            addTip: "Add a matrix (the identity) and make it active"
            onAddClicked: app.matrices.addMatrix()
        }

        ListView {
            id: matrixList
            objectName: "matrixList"
            Layout.fillWidth: true
            // Grows with its rows up to five, then scrolls.
            Layout.preferredHeight: Math.max(1, Math.min(count, 5)) * 32
            clip: true
            spacing: 2
            model: app.matrices.matrixModel
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: matrixRow
                required property string objectId
                required property string name
                required property string entriesText
                required property bool active

                width: ListView.view.width
                height: 30
                radius: AppTheme.Theme.panelRadius
                color: active ? AppTheme.Theme.surfaceLevelTwo
                    : matrixMouse.containsMouse ? Qt.rgba(0.5, 0.5, 0.5, 0.08) : "transparent"
                border.color: active ? AppTheme.Theme.transformedGridColor : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: AppTheme.Theme.spacingSmall
                    anchors.rightMargin: AppTheme.Theme.spacingSmall
                    spacing: AppTheme.Theme.spacingSmall

                    // A small bracket glyph marks matrices.
                    Label {
                        text: "[ ]"
                        color: AppTheme.Theme.transformedGridColor
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Label {
                        text: matrixRow.name
                        color: AppTheme.Theme.primaryText
                        font.pixelSize: 13
                        font.bold: matrixRow.active
                    }

                    Label {
                        Layout.fillWidth: true
                        text: matrixRow.entriesText
                        color: AppTheme.Theme.secondaryText
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: matrixMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: app.matrices.activate(matrixRow.objectId)
                }
            }

            Label {
                objectName: "noMatricesHint"
                anchors.fill: parent
                visible: matrixList.count === 0
                text: "No matrices. Use “+ Matrix”."
                color: AppTheme.Theme.secondaryText
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        ActionRow {
            duplicateName: "duplicateMatrixButton"
            deleteName: "deleteMatrixButton"
            actionsEnabled: app.matrices.activeId !== ""
            onDuplicateClicked: app.matrices.duplicateActive()
            onDeleteClicked: app.matrices.removeActive()
        }
    }
}
