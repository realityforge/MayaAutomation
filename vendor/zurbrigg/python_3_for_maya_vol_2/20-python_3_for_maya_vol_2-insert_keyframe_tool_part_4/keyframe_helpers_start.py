import maya.cmds as cmds
import maya.OpenMaya as om


def get_keyframe_times():
    keyframe_range = get_playback_range()
    range_start = keyframe_range[0]
    range_end = keyframe_range[1]

    keyframe_list = list(range(int(range_start), int(range_end + 1)))

    return keyframe_list

def get_playback_range():
    range_start = cmds.playbackOptions(q=True, minTime=True)
    range_end = cmds.playbackOptions(q=True, maxTime=True)
    return [range_start, range_end]

def insert_keyframes(keyframe_times):
    selection = cmds.ls(sl=True)
    if not selection:
        om.MGlobal.displayWarning("No objects selected")
        return

    cmds.setKeyframe(time=keyframe_times)


if __name__ == "__main__":
    keyframe_times = get_keyframe_times()
    insert_keyframes(keyframe_times)
