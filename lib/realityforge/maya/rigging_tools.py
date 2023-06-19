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
from parse import parse


# Note: to use this script you need to run
# "C:\Program Files\Autodesk\Maya2023\bin\mayapy.exe" -m pip install --user parse

def connect_transform_attributes(driver_object_name: str, driven_object_name: str) -> None:
    """Connect the transform, rotate and scale attributes of the driver object to the driven object.

    This is typically used to copy attributes from a driver joint into a driven joint so that the
    joint hierarchy/skeleton can be cleanly exported for game engines.

    :param driver_object_name: the name of the driver object.
    :param driven_object_name:  the name of the driven object.
    """
    for attr in ["translate", "rotate", "scale"]:
        cmds.setAttr(f"{driven_object_name}.{attr}", lock=False)
        cmds.connectAttr(f"{driver_object_name}.{attr}", f"{driven_object_name}.{attr}", lock=True, force=True)


def connect_transform_attributes_in_hierarchy(name: str,
                                              driver_object_name_pattern: str,
                                              driven_object_name_pattern: str) -> int:
    """Connect the transform, rotate and scale attributes of the driver object to the driven object.
    :param name: The "base" name of the object.
    :param driver_object_name_pattern: the f-string pattern used to derive the driver name.
    :param driven_object_name_pattern: the f-string pattern used to derive the driven name.
    :return: The number of objects matched.
    """
    driver_name = driver_object_name_pattern.format(name=name)
    driver = cmds.ls(driver_name)
    if 0 == len(driver):
        return 0
    elif 1 != len(driver):
        raise Exception(f"Multiple driver objects detected with the name {driver_name}. Aborting!")

    driven_name = driven_object_name_pattern.format(name=name)
    driven = cmds.ls(driven_name)
    if 0 == len(driven):
        return 0
    elif 1 != len(driven):
        raise Exception(f"Multiple driven objects detected with the name {driven_name}. Aborting!")

    connect_transform_attributes(driver_name, driven_name)

    transformed = 1

    children = cmds.listRelatives(driven_name)
    if children:
        for child in children:
            match = parse(driven_object_name_pattern, child)
            if match:
                child_base_name = match.named.get("name")
                if child_base_name:
                    transformed += connect_transform_attributes_in_hierarchy(child_base_name,
                                                                             driver_object_name_pattern,
                                                                             driven_object_name_pattern)

    return transformed


def lock_and_hide_transform_properties(object_name: str) -> None:
    """Lock and remove from the channelbox the attributes of the specified transform object.

    :param object_name: the name of the transform object.
    """
    for attr in ["translate", "rotate", "scale"]:
        for axis in ["X", "Y", "Z"]:
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=False)
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=False, keyable=False, channelBox=False)
    cmds.setAttr(f"{object_name}.visibility", lock=False, keyable=False, channelBox=False)


def lock_and_hide_transform_properties_in_hierarchy(object_name: str, object_name_pattern: str) -> int:
    """Lock and remove from the channelbox the attributes of the specified transform object and all transitive
     child objects that match the specified name pattern.

    :param object_name: The root transform object name.
    :param object_name_pattern: the f-string pattern used to match child transform objects.
    :return: The number of objects matched.
    """
    transformed = 0
    matched_object_names = cmds.ls(object_name, type=["transform"])
    print(f"{object_name} => {matched_object_names}")
    if 1 == len(matched_object_names):
        if parse(object_name_pattern, object_name):
            lock_and_hide_transform_properties(object_name)
            transformed += 1
    elif 0 != len(matched_object_names):
        raise Exception(f"Multiple objects detected with the name {object_name}. Aborting!")

    children = cmds.listRelatives(object_name, type=["transform"])
    if children:
        for child in children:
            transformed += lock_and_hide_transform_properties_in_hierarchy(child, object_name_pattern)

    return transformed
