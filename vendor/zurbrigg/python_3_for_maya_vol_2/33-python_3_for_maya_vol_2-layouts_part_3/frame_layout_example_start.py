import maya.cmds as cmds


def create_ui(window_name):
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title="Frame Layout Example")

    main_column_layout = cmds.columnLayout(adjustableColumn=True, parent=window)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui("LayoutExampleUI")
