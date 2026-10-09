import QtQml
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "pages"
import "theme" as AppTheme

ApplicationWindow {
    id: root
    objectName: "applicationWindow"

    width: 1440
    height: 900
    minimumWidth: AppTheme.Theme.minimumWindowWidth
    minimumHeight: AppTheme.Theme.minimumWindowHeight
    visible: true
    title: app.project.windowTitle
    color: AppTheme.Theme.windowBackground

    // Keep stock Qt Quick Controls legible in both themes.
    palette.window: AppTheme.Theme.windowBackground
    palette.windowText: AppTheme.Theme.primaryText
    palette.base: AppTheme.Theme.panelBackground
    palette.text: AppTheme.Theme.primaryText
    palette.button: AppTheme.Theme.surfaceLevelTwo
    palette.buttonText: AppTheme.Theme.primaryText
    palette.highlight: AppTheme.Theme.accentColor
    palette.highlightedText: "#FFFFFF"
    palette.placeholderText: AppTheme.Theme.secondaryText
    palette.toolTipBase: AppTheme.Theme.panelBackground
    palette.toolTipText: AppTheme.Theme.primaryText
    // Bevel shades used by the Fusion style.
    palette.light: Qt.lighter(AppTheme.Theme.surfaceLevelTwo, 1.25)
    palette.midlight: Qt.lighter(AppTheme.Theme.surfaceLevelTwo, 1.1)
    palette.mid: AppTheme.Theme.borderColor
    palette.dark: Qt.darker(AppTheme.Theme.surfaceLevelTwo, 1.4)
    palette.shadow: Qt.darker(AppTheme.Theme.windowBackground, 1.6)

    // Disabled controls fade towards the background so they read as inactive.
    // These bindings are installed after creation: declared inline, the style
    // resolves its own palette afterwards and the disabled group is lost until
    // the theme next changes.
    readonly property color disabledText: Qt.alpha(AppTheme.Theme.secondaryText, 0.45)
    Component.onCompleted: {
        palette.disabled.buttonText = Qt.binding(function () { return root.disabledText })
        palette.disabled.windowText = Qt.binding(function () { return root.disabledText })
        palette.disabled.text = Qt.binding(function () { return root.disabledText })
        palette.disabled.button = Qt.binding(function () { return AppTheme.Theme.panelBackground })
    }

    Binding {
        target: AppTheme.Theme
        property: "darkMode"
        value: app.themeMode === "dark"
    }

    // Delete removes the selected object. Text fields consume Delete
    // themselves while editing, so this never fires during typing.
    Shortcut {
        objectName: "deleteShortcut"
        sequences: [StandardKey.Delete]
        onActivated: app.scene.removeSelected()
    }

    // Frame clock for the transformation: one advance per rendered frame keeps
    // playback in step with the display.
    FrameAnimation {
        objectName: "playbackClock"
        running: app.animation.playing
        onTriggered: app.animation.advance(frameTime)
    }

    WorkspacePage {
        id: workspacePage
        anchors.fill: parent
        onRestoreRecoveryRequested: root.guard("restore")
    }

    // Project files ---------------------------------------------------------
    //
    // Actions that replace the document (new, open, restore, quit) go through
    // guard(): with unsaved changes it first asks Save / Discard / Cancel and
    // runs the action afterwards. Every file operation itself is in Python
    // (app.project); this file only sequences dialogs.

    property bool closeConfirmed: false

    function guard(action) {
        if (app.project.dirty) {
            unsavedDialog.pendingAction = action
            unsavedDialog.open()
        } else {
            perform(action)
        }
    }

    function perform(action) {
        if (action === "new") {
            app.project.newProject()
        } else if (action === "open") {
            openDialog.open()
        } else if (action === "restore") {
            app.project.restoreRecovery()
        } else if (action === "quit") {
            closeConfirmed = true
            app.project.prepareToQuit()
            root.close()
        } else if (action.startsWith("recent:")) {
            app.project.openProject(action.substring(7))
        }
    }

    // Save, then continue with `after` ("" for none) once the file is written.
    function save(after) {
        if (app.project.hasFilePath) {
            if (app.project.saveProject())
                perform(after)
        } else {
            saveAs(after)
        }
    }

    function saveAs(after) {
        saveDialog.pendingAction = after
        saveDialog.selectedFile = app.project.folder !== ""
            ? app.project.folder + "/" + app.project.suggestedFileName
            : app.project.suggestedFileName
        saveDialog.open()
    }

    function finishSaveAs(location, after) {
        if (app.project.saveProjectAs(location))
            perform(after)
    }

    onClosing: function (close) {
        if (!closeConfirmed && app.project.dirty) {
            close.accepted = false
            guard("quit")
        } else if (!closeConfirmed) {
            app.project.prepareToQuit()
        }
    }

    FileDialog {
        id: openDialog
        objectName: "openDialog"
        title: "Open scene"
        fileMode: FileDialog.OpenFile
        nameFilters: app.project.nameFilters
        currentFolder: app.project.folder
        onAccepted: app.project.openProject(selectedFile.toString())
    }

    FileDialog {
        id: saveDialog
        objectName: "saveDialog"
        property string pendingAction: ""
        title: "Save scene as"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "mvscene"
        nameFilters: app.project.nameFilters
        onAccepted: root.finishSaveAs(selectedFile.toString(), pendingAction)
    }

    Dialog {
        id: unsavedDialog
        objectName: "unsavedChangesDialog"
        property string pendingAction: ""
        anchors.centerIn: parent
        modal: true
        title: "Unsaved changes"
        standardButtons: Dialog.Save | Dialog.Discard | Dialog.Cancel

        Label {
            text: "Save the changes to “" + app.project.displayName + "” first?\n"
                + "If you don't, your changes will be lost."
            color: AppTheme.Theme.primaryText
        }

        onAccepted: root.save(pendingAction)
        onDiscarded: {
            close()
            root.perform(pendingAction)
        }
    }

    menuBar: MenuBar {
        objectName: "menuBar"

        Menu {
            title: "&File"

            Action {
                objectName: "newAction"
                text: "&New"
                shortcut: StandardKey.New
                onTriggered: root.guard("new")
            }
            Action {
                objectName: "openAction"
                text: "&Open…"
                shortcut: StandardKey.Open
                onTriggered: root.guard("open")
            }

            Menu {
                id: recentMenu
                objectName: "recentMenu"
                title: "Open &Recent"
                enabled: app.project.recentProjects.length > 0

                Instantiator {
                    model: app.project.recentProjects
                    delegate: MenuItem {
                        required property var modelData
                        text: modelData.name + "   —   " + modelData.folder
                        onTriggered: root.guard("recent:" + modelData.path)
                    }
                    onObjectAdded: function (index, object) { recentMenu.insertItem(index, object) }
                    onObjectRemoved: function (index, object) { recentMenu.removeItem(object) }
                }

                MenuSeparator {}

                Action {
                    text: "Clear list"
                    onTriggered: app.project.clearRecentProjects()
                }
            }

            MenuSeparator {}

            Action {
                objectName: "saveAction"
                text: "&Save"
                shortcut: StandardKey.Save
                onTriggered: root.save("")
            }
            Action {
                objectName: "saveAsAction"
                text: "Save &As…"
                shortcut: StandardKey.SaveAs
                onTriggered: root.saveAs("")
            }

            MenuSeparator {}

            Action {
                objectName: "quitAction"
                text: "&Quit"
                shortcut: StandardKey.Quit
                onTriggered: root.close()
            }
        }

        Menu {
            title: "&Edit"

            // While a text field has focus, it handles Ctrl+Z itself (text undo).
            Action {
                objectName: "undoAction"
                text: app.project.undoText
                shortcut: StandardKey.Undo
                enabled: app.project.canUndo
                onTriggered: app.project.undo()
            }
            Action {
                objectName: "redoAction"
                text: app.project.redoText
                shortcut: StandardKey.Redo
                enabled: app.project.canRedo
                onTriggered: app.project.redo()
            }
        }
    }

    // Test hooks for presentation-only behaviour; application state such as the
    // workspace mode lives in the Python view models and is driven through `app`.
    function testPythonConnection() {
        workspacePage.testPythonConnection()
    }

    function toggleExpressionDock() {
        workspacePage.toggleExpressionDock()
    }
}
