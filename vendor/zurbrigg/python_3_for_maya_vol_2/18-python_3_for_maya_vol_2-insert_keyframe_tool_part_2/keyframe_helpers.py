import maya.cmds as cmds
import maya.OpenMaya as om


def current_time():
    return cmds.currentTime(q=True)

def set_current_time(new_time):
    cmds.currentTime(new_time)

def insert_keyframe(keyframe_time=current_time()):
    selection = cmds.ls(sl=True)
    if not selection:
        om.MGlobal.displayWarning("No objects selected")
        return

    cmds.setKeyframe(time=keyframe_time)


if __name__ == "__main__":
    for new_time in range(1, 21):
        insert_keyframe(new_time)

    # insert_keyframe()
