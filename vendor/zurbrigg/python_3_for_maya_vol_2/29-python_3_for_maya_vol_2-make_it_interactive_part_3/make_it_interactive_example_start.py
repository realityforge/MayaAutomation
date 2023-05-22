from functools import partial

import maya.cmds as cmds


def on_text_field_changed(text_field_grp, text_control, *args):
    new_text = cmds.textFieldGrp(text_field_grp, q=True, text=True)
    cmds.text(text_control, e=True, label=new_text)

def on_checkbox_toggled(*args):
    print("TODO: on_checkbox_toggled()")

def on_button_clicked(*args):
    cmds.polySphere()

def create_ui():
    window = cmds.window(title="Common Controls", width=260)
    main_layout = cmds.columnLayout(adjustableColumn=True, parent=window)

    text_control = cmds.text("Text", parent=main_layout)

    text_field_grp = cmds.textFieldGrp(label="Text Field: ", parent=main_layout)
    cmds.textFieldGrp(text_field_grp, e=True, changeCommand=partial(on_text_field_changed, text_field_grp, text_control))

    checkbox_grp = cmds.checkBoxGrp(label="Checkbox: " , parent=main_layout, changeCommand=on_checkbox_toggled)

    button = cmds.button("Button", parent=main_layout, command=on_button_clicked)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()
