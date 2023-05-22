import maya.cmds as cmds


def on_button_clicked(*args):
    cmds.polySphere()

def create_ui():
    window = cmds.window(title="Common Controls", width=260)
    main_layout = cmds.columnLayout(adjustableColumn=True, parent=window)

    text = cmds.text("Text", parent=main_layout)
    text_field_grp = cmds.textFieldGrp(label="Text Field: ", parent=main_layout)

    button = cmds.button("Button", parent=main_layout, command=on_button_clicked)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()
