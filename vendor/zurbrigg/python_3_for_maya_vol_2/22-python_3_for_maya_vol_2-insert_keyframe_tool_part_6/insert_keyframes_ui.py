from functools import partial
import maya.cmds as cmds
import keyframe_helpers


def do_insert_keyframes(insert_on_twos_cb, skip_existing_cb, force_overwrite_cb, *args):
    skip_existing = cmds.checkBox(skip_existing_cb, q=True, value=True)
    force_overwrite = cmds.checkBox(force_overwrite_cb, q=True, value=True)

    interval = 1
    if cmds.checkBox(insert_on_twos_cb, q=True, value=True):
        interval = 2

    keyframe_times = keyframe_helpers.get_keyframe_times(skip_existing, interval)
    keyframe_helpers.insert_keyframes(keyframe_times, force_overwrite)

def create_ui():
    window = cmds.window(title="Keyframe Tool", width=260)
    main_layout = cmds.columnLayout(adjustableColumn=True)

    insert_on_twos_cb = cmds.checkBox(label="Insert on 2's", parent=main_layout)
    skip_existing_cb = cmds.checkBox(label="Skip Existing Keyframes", parent=main_layout)
    force_overwrite_cb = cmds.checkBox(label="Force Overwrite", parent=main_layout)
    insert_frames_btn = cmds.button("Insert Keyframes", parent=main_layout)

    cmds.button(insert_frames_btn,
                edit=True,
                command=partial(do_insert_keyframes, insert_on_twos_cb, skip_existing_cb, force_overwrite_cb))

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()
