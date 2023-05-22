import maya.cmds as cmds

def create_row(label, parent):
    row_layout = cmds.rowLayout(numberOfColumns=3,
                                columnWidth3=(80, 75, 150),
                                adjustableColumn=3,
                                columnAlign=(1, "right"),
                                columnAttach=[(1, "both", 0), (2, "both", 0), (3, "both", 0)],
                                parent=parent)

    cmds.text(label=label, parent=row_layout)
    cmds.intField(parent=row_layout)
    cmds.intSlider(parent=row_layout)

def create_ui(window_name):
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title="Layout Example", width=260)

    main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=2, parent=window)

    for i in range(1, 10):
        create_row(f"Row {i}", main_layout)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui("LayoutExampleUI")
