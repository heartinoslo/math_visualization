import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as AppTheme

Item {
    id: root
    objectName: "workspacePage"

    function testPythonConnection() {
        statusBar.testPythonConnection()
    }

    function toggleExpressionDock() {
        expressionDock.expanded = !expressionDock.expanded
    }

    function setPresentationWorkspace(index) {
        visualizationArea.presentationWorkspaceIndex = index
    }

    Rectangle {
        anchors.fill: parent
        color: AppTheme.Theme.windowBackground
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        SplitView {
            id: mainArea
            objectName: "mainArea"
            orientation: Qt.Horizontal
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 0
            clip: true

            LeftPanel {
                objectName: "leftPanel"
                SplitView.preferredWidth: AppTheme.Theme.leftPanelWidth
                SplitView.minimumWidth: AppTheme.Theme.leftPanelMinimumWidth
            }

            Item {
                id: centerArea
                objectName: "centerArea"
                SplitView.fillWidth: true
                SplitView.minimumWidth: AppTheme.Theme.centerAreaMinimumWidth

                ColumnLayout {
                    anchors.fill: parent
                    spacing: AppTheme.Theme.spacingMedium

                    Rectangle {
                        id: visualizationArea
                        objectName: "visualizationArea"
                        property int presentationWorkspaceIndex: 0

                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: AppTheme.Theme.visualizationMinimumHeight
                        color: AppTheme.Theme.workspaceBackground
                        border.color: AppTheme.Theme.borderColor
                        radius: AppTheme.Theme.panelRadius
                        clip: true

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            VisualizationHeader {
                                id: visualizationHeader
                                objectName: "visualizationHeader"
                                Layout.fillWidth: true
                                workspaceIndex: visualizationArea.presentationWorkspaceIndex
                                onWorkspaceSelected: function (index){
                                    root.setPresentationWorkspace(index)
                                }
                            }

                            Loader {
                                id: workspaceLoader
                                objectName: "workspaceLoader"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                source: visualizationArea.presentationWorkspaceIndex === 0
                                    ? "../workspaces/Workspace2D.qml"
                                    : "../workspaces/Workspace3D.qml"
                            }
                        }
                    }

                    ExpressionDock {
                        id: expressionDock
                        objectName: "expressionDock"
                        Layout.fillWidth: true
                        Layout.preferredHeight: expanded
                            ? AppTheme.Theme.expressionDockHeight
                            : AppTheme.Theme.expressionDockCollapsedHeight
                        Layout.minimumHeight: AppTheme.Theme.expressionDockCollapsedHeight
                        Layout.maximumHeight: expanded
                            ? AppTheme.Theme.expressionDockHeight
                            : AppTheme.Theme.expressionDockCollapsedHeight
                    }
                }
            }

            RightPanel {
                objectName: "rightPanel"
                SplitView.preferredWidth: AppTheme.Theme.rightPanelWidth
                SplitView.minimumWidth: AppTheme.Theme.rightPanelMinimumWidth
            }
        }

        AnimationBar {
            objectName: "animationBar"
            Layout.fillWidth: true
            Layout.preferredHeight: AppTheme.Theme.animationBarHeight
            Layout.minimumHeight: AppTheme.Theme.animationBarHeight
            Layout.maximumHeight: AppTheme.Theme.animationBarHeight
        }

        StatusBar {
            id: statusBar
            objectName: "statusBar"
            Layout.fillWidth: true
            Layout.preferredHeight: AppTheme.Theme.statusBarHeight
            Layout.minimumHeight: AppTheme.Theme.statusBarHeight
            Layout.maximumHeight: AppTheme.Theme.statusBarHeight
        }
    }
}
