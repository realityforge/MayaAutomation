import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om


def get_keyframe_times(interval=1):
    keyframe_range = get_selected_range()
    if not keyframe_range:
        keyframe_range = get_playback_range()

    range_start = keyframe_range[0]
    range_end = keyframe_range[1]

    keyframe_list = list(range(int(range_start), int(range_end + 1), interval))

    return keyframe_list

def get_playback_range():
    range_start = cmds.playbackOptions(q=True, minTime=True)
    range_end = cmds.playbackOptions(q=True, maxTime=True)
    return [range_start, range_end]

def get_selected_range():
    main_time_control = mel.eval("$temp = $gPlayBackSlider")
    if cmds.timeControl(main_time_control, q=True, rangeVisible=True):
        selected_range = cmds.timeControl(main_time_control, q=True, rangeArray=True)
        selected_range[1] -= 1

        return selected_range

    return None

def insert_keyframes(keyframe_times):
    selection = cmds.ls(sl=True)
    if not selection:
        om.MGlobal.displayWarning("No objects selected")
        return

    cmds.setKeyframe(time=keyframe_times)


if __name__ == "__main__":
    keyframe_times = get_keyframe_times(interval=1)
    insert_keyframes(keyframe_times)
