import maya.cmds as cmds

def do_insert_keyframes(*args):
    print("TODO: do_insert_keyframes")

def create_ui():
    window = cmds.window(title="Keyframe Tool", width=260)
    main_layout = cmds.columnLayout(adjustableColumn=True, parent=window)

    cmds.checkBox(label="Insert on 2's", parent=main_layout)
    insert_frames_btn = cmds.button("Insert Keyframes", parent=main_layout)

    cmds.button(insert_frames_btn, edit=True, command=do_insert_keyframes)

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()
