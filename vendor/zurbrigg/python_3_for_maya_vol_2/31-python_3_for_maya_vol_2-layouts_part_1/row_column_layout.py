import maya.cmds as cmds


def create_ui(window_name):
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title="Layout Example", width=260)

    # main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=3, parent=window)
    main_layout = cmds.rowColumnLayout(numberOfColumns=3, adjustableColumn=2, rowSpacing=(1, 3), parent=window)

    for i in range(1, 10):
        cmds.button(f"Button {i}", parent=main_layout)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui("LayoutExampleUI")
