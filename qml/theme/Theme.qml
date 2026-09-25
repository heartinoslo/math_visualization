pragma Singleton

import QtQuick

QtObject {
    readonly property color windowBackground: "#181B20"
    readonly property color panelBackground: "#22262D"
    readonly property color workspaceBackground: "#12161C"
    readonly property color surfaceLevelTwo: "#343A43"
    readonly property color borderColor: "#3B424D"
    readonly property color primaryText: "#F1F3F5"
    readonly property color secondaryText: "#AEB7C2"
    readonly property color accentColor: "#5B8CFF"

    readonly property int spacingSmall: 6
    readonly property int spacingMedium: 12
    readonly property int spacingLarge: 18
    readonly property int panelRadius: 6

    readonly property int minimumWindowWidth: 1000
    readonly property int minimumWindowHeight: 650
    readonly property int statusBarHeight: 28
    readonly property int animationBarHeight: 42
    readonly property int visualizationHeaderHeight: 44
    readonly property int controlHeight: 30
    readonly property int compactControlHeight: 24
    readonly property int timelineTrackHeight: 4
    readonly property int timelineTrackRadius: 2
    readonly property int timelineHandleSize: 10
    readonly property int timelineHandleRadius: 5
    readonly property int visualizationMinimumHeight: 260
    readonly property int expressionDockHeaderHeight: 34
    readonly property int expressionDockHeight: 190
    readonly property int expressionDockCollapsedHeight: 34
    readonly property int leftPanelWidth: 235
    readonly property int leftPanelMinimumWidth: 180
    readonly property int centerAreaMinimumWidth: 540
    readonly property int rightPanelWidth: 300
    readonly property int rightPanelMinimumWidth: 240
}
