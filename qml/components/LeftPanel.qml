import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as AppTheme

// Scene objects: the vector list with add, duplicate and delete actions.
Rectangle {
    id: root
    color: AppTheme.Theme.panelBackground
    border.color: AppTheme.Theme.borderColor
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: AppTheme.Theme.spacingLarge
        spacing: AppTheme.Theme.spacingSmall

        RowLayout {
            Layout.fillWidth: true
            spacing: AppTheme.Theme.spacingSmall

            Label {
                Layout.fillWidth: true
                text: "OBJECTS"
                color: AppTheme.Theme.primaryText
                font.pixelSize: 13
                font.weight: Font.DemiBold
            }

            ToolButton {
                objectName: "addVectorButton"
                text: "+ Vector"
                implicitHeight: AppTheme.Theme.compactControlHeight
                font.pixelSize: 12
                ToolTip.visible: hovered
                ToolTip.text: "Add a vector at (1, 1)"
                onClicked: app.scene.addVector()
            }
        }

        ListView {
            id: vectorList
            objectName: "vectorList"
            Layout.fillWidth: true
            Layout.fillHeight: true
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
                text: "No objects yet.\nUse “+ Vector” to add one."
                color: AppTheme.Theme.secondaryText
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: AppTheme.Theme.spacingSmall

            Button {
                objectName: "duplicateVectorButton"
                Layout.fillWidth: true
                text: "Duplicate"
                enabled: app.scene.selectedId !== ""
                implicitHeight: AppTheme.Theme.compactControlHeight
                font.pixelSize: 11
                onClicked: app.scene.duplicateSelected()
            }

            Button {
                objectName: "deleteVectorButton"
                Layout.fillWidth: true
                text: "Delete"
                enabled: app.scene.selectedId !== ""
                implicitHeight: AppTheme.Theme.compactControlHeight
                font.pixelSize: 11
                onClicked: app.scene.removeSelected()
            }
        }
    }
}
