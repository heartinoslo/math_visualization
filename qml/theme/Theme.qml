pragma Singleton

import QtQuick

QtObject {
    // Driven from app.themeMode by Main.qml; the theme itself owns no state.
    property bool darkMode: true

    readonly property color windowBackground: darkMode ? "#181B20" : "#EEF1F5"
    readonly property color panelBackground: darkMode ? "#22262D" : "#FFFFFF"
    readonly property color workspaceBackground: darkMode ? "#12161C" : "#F8F9FB"
    readonly property color surfaceLevelTwo: darkMode ? "#343A43" : "#DDE2E9"
    readonly property color borderColor: darkMode ? "#3B424D" : "#C9D0DA"
    readonly property color primaryText: darkMode ? "#F1F3F5" : "#1B1F24"
    readonly property color secondaryText: darkMode ? "#AEB7C2" : "#586271"
    readonly property color accentColor: darkMode ? "#5B8CFF" : "#2F66E0"
    readonly property color errorBackground: darkMode ? "#4A2226" : "#FDE7E9"
    readonly property color errorBorder: darkMode ? "#8C3A42" : "#E3A1A8"
    readonly property color errorText: darkMode ? "#FFD7DB" : "#8A1C27"
    readonly property color gridMinor: darkMode ? "#1B212A" : "#E9EDF2"
    readonly property color gridMajor: darkMode ? "#2A323E" : "#D2D9E2"
    readonly property color axisColor: darkMode ? "#7D8898" : "#6E7988"
    readonly property color grid3DMinor: darkMode ? "#262D38" : "#DCE2EA"
    readonly property color grid3DMajor: darkMode ? "#3A4453" : "#B9C3D0"
    readonly property color axisXColor: darkMode ? "#F2555A" : "#D93036"
    readonly property color axisYColor: darkMode ? "#4CC38A" : "#218358"
    readonly property color axisZColor: darkMode ? "#6E9BFF" : "#2F5FD0"
    readonly property real activePlaneOpacity: 0.07
    readonly property real auxiliaryPlaneOpacity: 0.45
    readonly property color overlayBackground: darkMode ? "#D922262D" : "#E6FFFFFF"

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
    readonly property int errorBannerHeight: 36
    readonly property int axisLabelMargin: 4
    readonly property int axisLabelPixelSize: 11
    readonly property int originPointRadius: 3
    readonly property int leftPanelWidth: 235
    readonly property int leftPanelMinimumWidth: 180
    readonly property int centerAreaMinimumWidth: 540
    readonly property int rightPanelWidth: 300
    readonly property int rightPanelMinimumWidth: 240
}
