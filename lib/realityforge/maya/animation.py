# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import maya.cmds as cmds


def insert_frames(timeshift: int) -> None:
    """
    Select all the keyframes in the scene and move them frame_count_delta forward.
    :param timeshift the number of frames to shift forward
    """
    # select all keyframes and move N frames
    cmds.select(cmds.ls(type='animCurve'))

    cmds.keyframe(edit=True, relative=True, option="over", timeChange=timeshift)
