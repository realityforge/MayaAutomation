import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om


def get_keyframe_times(skip_existing=False, interval=1):
    keyframe_range = get_selected_range()
    if not keyframe_range:
        keyframe_range = get_playback_range()

    range_start = keyframe_range[0]
    range_end = keyframe_range[1]

    keyframe_list = list(range(int(range_start), int(range_end + 1), interval))

    if skip_existing:
        filtered_list = []
        for keyframe_time in keyframe_list:
            if not keyframe_exists(keyframe_time):
                filtered_list.append(keyframe_time)

        return filtered_list

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

def keyframe_exists(keyframe_time):
    keyframe_count = cmds.keyframe(q=True, keyframeCount=True, time=(keyframe_time,))
    return keyframe_count > 0

def insert_keyframes(keyframe_times, force_overwrite=False):
    selection = cmds.ls(sl=True)
    if not selection:
        om.MGlobal.displayWarning("No objects selected")
        return

    if not force_overwrite:
        for keyframe_time in keyframe_times:
            if keyframe_exists(keyframe_time):
                raise RuntimeError(f"A keyframe exists a frame: {keyframe_time}")

    cmds.setKeyframe(time=keyframe_times)


if __name__ == "__main__":
    keyframe_times = get_keyframe_times(interval=1)
    insert_keyframes(keyframe_times, force_overwrite=True)


