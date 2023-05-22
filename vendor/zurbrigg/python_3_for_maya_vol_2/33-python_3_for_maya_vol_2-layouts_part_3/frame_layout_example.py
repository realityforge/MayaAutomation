import maya.cmds as cmds


def create_ui(window_name):
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title="Frame Layout Example")

    main_layout = cmds.scrollLayout(childResizable=True, parent=window)
    main_column_layout = cmds.columnLayout(adjustableColumn=True, parent=main_layout)

    colors_frame_layout = cmds.frameLayout(label="Colors", collapsable=True, parent=main_column_layout)
    colors_column_layout = cmds.columnLayout(adjustableColumn=True, parent=colors_frame_layout)

    cmds.button("Red", parent=colors_column_layout)
    cmds.button("Green", parent=colors_column_layout)
    cmds.button("Blue", parent=colors_column_layout)

    numbers_frame_layout = cmds.frameLayout(label="Numbers", collapsable=True, parent=main_column_layout)
    numbers_column_layout = cmds.columnLayout(adjustableColumn=True, parent=numbers_frame_layout)

    cmds.button("One", parent=numbers_column_layout)
    cmds.button("Two", parent=numbers_column_layout)
    cmds.button("Three", parent=numbers_column_layout)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui("LayoutExampleUI")
