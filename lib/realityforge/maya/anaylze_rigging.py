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
from typing import Optional


def move_preferred_angle(source_joint_name: str, target_joint_name: str) -> None:
    """Move the preferred angle value from one joint to another joint.

    Used when patching an existing rig. The preferred angle on the source joint is zeroed. This function behaves
    correctly  when source_joint_name is the same as target_joint_name.

    :param source_joint_name: The source joint from which the preferred angle will be moved.
    :param target_joint_name: The target joint to which the preferred angle will be moved.
    """
    x = cmds.getAttr(f"{source_joint_name}.preferredAngleX")
    y = cmds.getAttr(f"{source_joint_name}.preferredAngleY")
    z = cmds.getAttr(f"{source_joint_name}.preferredAngleZ")
    cmds.setAttr(f"{source_joint_name}.preferredAngleX", 0)
    cmds.setAttr(f"{source_joint_name}.preferredAngleY", 0)
    cmds.setAttr(f"{source_joint_name}.preferredAngleZ", 0)
    cmds.setAttr(f"{target_joint_name}.preferredAngleX", x)
    cmds.setAttr(f"{target_joint_name}.preferredAngleY", y)
    cmds.setAttr(f"{target_joint_name}.preferredAngleZ", z)
