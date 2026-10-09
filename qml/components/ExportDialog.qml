import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../theme" as AppTheme

// Video export with ManimGL. All work happens in app.exporter; the render
// runs in a separate process, so this dialog can be closed while it runs.
Dialog {
    id: root
    objectName: "exportDialog"
    readonly property var exporter: app.exporter

    title: "Export video"
    modal: true
    width: Math.min(560, parent ? parent.width - 40 : 560)
    standardButtons: Dialog.Close

    onOpened: {
        if (exporter.environmentState === "unknown")
            exporter.checkEnvironment()
    }

    component FieldLabel: Label {
        color: AppTheme.Theme.secondaryText
        font.pixelSize: 12
        Layout.alignment: Qt.AlignTop
    }

    FileDialog {
        id: pythonDialog
        title: "Python of the ManimGL environment"
        fileMode: FileDialog.OpenFile
        onAccepted: {
            root.exporter.setPythonPath(selectedFile.toString())
            root.exporter.checkEnvironment()
        }
    }

    FolderDialog {
        id: folderDialog
        title: "Folder for exported videos"
        currentFolder: root.exporter.outputFolderUrl
        onAccepted: root.exporter.setOutputFolder(selectedFolder.toString())
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: AppTheme.Theme.spacingMedium

        // ManimGL environment ---------------------------------------------
        Rectangle {
            objectName: "environmentStatus"
            readonly property color tone: root.exporter.environmentState === "ready" ? AppTheme.Theme.successColor
                : root.exporter.environmentState === "missing" ? AppTheme.Theme.flippedSquareColor
                : AppTheme.Theme.secondaryText
            Layout.fillWidth: true
            implicitHeight: environmentRow.implicitHeight + 2 * AppTheme.Theme.spacingSmall
            radius: 4
            color: Qt.alpha(tone, 0.14)
            border.color: tone

            RowLayout {
                id: environmentRow
                anchors.fill: parent
                anchors.margins: AppTheme.Theme.spacingSmall
                spacing: AppTheme.Theme.spacingSmall

                Label {
                    objectName: "environmentMessage"
                    Layout.fillWidth: true
                    text: root.exporter.environmentMessage
                    color: AppTheme.Theme.primaryText
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Button {
                    text: "Check again"
                    implicitHeight: AppTheme.Theme.compactControlHeight
                    enabled: root.exporter.environmentState !== "checking"
                    onClicked: root.exporter.checkEnvironment()
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 3
            columnSpacing: AppTheme.Theme.spacingMedium
            rowSpacing: AppTheme.Theme.spacingSmall

            FieldLabel { text: "ManimGL Python" }
            Label {
                objectName: "pythonPathLabel"
                Layout.fillWidth: true
                text: root.exporter.pythonPath || "not chosen"
                color: AppTheme.Theme.primaryText
                font.pixelSize: 12
                elide: Text.ElideMiddle
            }
            Button {
                text: "Choose…"
                implicitHeight: AppTheme.Theme.compactControlHeight
                onClicked: pythonDialog.open()
            }

            FieldLabel { text: "Quality" }
            RowLayout {
                Layout.columnSpan: 2
                spacing: AppTheme.Theme.spacingMedium

                Repeater {
                    model: root.exporter.qualityOptions
                    delegate: RadioButton {
                        required property var modelData
                        objectName: "quality_" + modelData.key
                        text: modelData.label
                        font.pixelSize: 12
                        checked: root.exporter.quality === modelData.key
                        onToggled: root.exporter.setQuality(modelData.key)
                    }
                }
            }

            FieldLabel { text: "Folder" }
            Label {
                objectName: "outputFolderLabel"
                Layout.fillWidth: true
                text: root.exporter.outputFolder
                color: AppTheme.Theme.primaryText
                font.pixelSize: 12
                elide: Text.ElideMiddle
            }
            Button {
                text: "Choose…"
                implicitHeight: AppTheme.Theme.compactControlHeight
                onClicked: folderDialog.open()
            }

            FieldLabel { text: "File" }
            Label {
                objectName: "exportFileName"
                Layout.columnSpan: 2
                Layout.fillWidth: true
                text: root.exporter.fileName
                color: AppTheme.Theme.primaryText
                font.pixelSize: 12
                elide: Text.ElideMiddle
            }
        }

        // Progress and result ------------------------------------------------
        ProgressBar {
            objectName: "exportProgress"
            Layout.fillWidth: true
            visible: root.exporter.running || root.exporter.statusText !== ""
            value: root.exporter.progress
        }

        Label {
            objectName: "exportStatus"
            Layout.fillWidth: true
            visible: text !== ""
            text: root.exporter.statusText
            color: AppTheme.Theme.primaryText
            font.pixelSize: 12
            elide: Text.ElideRight
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: AppTheme.Theme.spacingSmall

            Button {
                objectName: "startExportButton"
                text: "Export"
                highlighted: true
                visible: !root.exporter.running
                enabled: root.exporter.canExport
                onClicked: root.exporter.startExport()
            }
            Button {
                objectName: "cancelExportButton"
                text: "Cancel export"
                visible: root.exporter.running
                onClicked: root.exporter.cancelExport()
            }
            Button {
                objectName: "openVideoButton"
                text: "Open video"
                visible: root.exporter.resultPath !== "" && !root.exporter.running
                onClicked: root.exporter.openVideo()
            }
            Button {
                text: "Show folder"
                visible: root.exporter.resultPath !== "" && !root.exporter.running
                onClicked: root.exporter.openFolder()
            }
            Item { Layout.fillWidth: true }
        }

        // The end of ManimGL's output, for diagnosing a failed render.
        ScrollView {
            objectName: "exportLog"
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            visible: root.exporter.logTail !== "" && !root.exporter.running && root.exporter.resultPath === ""
            clip: true

            TextArea {
                readOnly: true
                text: root.exporter.logTail
                font.family: "monospace"
                font.pixelSize: 11
                wrapMode: TextEdit.NoWrap
                color: AppTheme.Theme.secondaryText
            }
        }
    }
}
