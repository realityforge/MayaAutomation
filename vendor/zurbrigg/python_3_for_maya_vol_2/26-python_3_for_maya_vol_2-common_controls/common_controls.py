import maya.cmds as cmds


def create_ui():
    window = cmds.window(title="Common Controls", width=260)
    main_layout = cmds.columnLayout(adjustableColumn=True, parent=window)

    text = cmds.text("Text", parent=main_layout)
    text_field_grp = cmds.textFieldGrp(label="Text Field: ", parent=main_layout)
    int_field_grp = cmds.intFieldGrp(label="Int Field: ", parent=main_layout)
    checkbox_grp = cmds.checkBoxGrp(label="Checkbox: " , parent=main_layout)
    radio_btn_grp = cmds.radioButtonGrp( label='Radio Buttons: ', labelArray3=['Red', 'Green', 'Blue'], numberOfRadioButtons=3, parent=main_layout)

    options_menu_grp = cmds.optionMenuGrp(label="Options Menu: ", parent=main_layout)
    cmds.menuItem("Item 1")
    cmds.menuItem("Item 2")
    cmds.menuItem("Item 3")

    button = cmds.button("Button", parent=main_layout)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()
