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


def zero_transform_properties(object_name: str) -> None:
    """Zero the translation, rotation and scale attributes of the specified transform node.

    :param object_name: the name of the transform object.
    """
    for attr in ["translate", "rotate"]:
        for axis in ["X", "Y", "Z"]:
            if not cmds.getAttr(f"{object_name}.{attr}{axis}", lock=True):
                cmds.setAttr(f"{object_name}.{attr}{axis}", 0)
    for axis in ["X", "Y", "Z"]:
        if not cmds.getAttr(f"{object_name}.scale{axis}", lock=True):
            cmds.setAttr(f"{object_name}.scale{axis}", 1)


def zero_transform_properties_in_hierarchy(object_name: str, object_name_pattern: str) -> int:
    """Zero the translation, rotation and scale attributes of transform nodes starting at specified
    root for all child nodes matching name pattern.

    :param object_name: The root transform object name.
    :param object_name_pattern: the f-string pattern used to match child transform objects.
    :return: The number of objects matched.
    """
    transformed = 0
    matched_object_names = cmds.ls(object_name, type=["transform"])
    if 1 == len(matched_object_names):
        if parse(object_name_pattern, object_name):
            zero_transform_properties(object_name)
            transformed += 1
    elif 0 != len(matched_object_names):
        raise Exception(f"Multiple objects detected with the name {object_name}. Aborting!")

    children = cmds.listRelatives(object_name, type=["transform"])
    if children:
        for child in children:
            transformed += zero_transform_properties_in_hierarchy(child, object_name_pattern)

    return transformed


def lock_influence_weights(object_name: str) -> None:
    """Lock the influence weights on the joint specified.

    :param object_name: the name of the joint object.
    """
    print(f"Locking {object_name}")
    cmds.setAttr(f"{object_name}.lockInfluenceWeights", 1)


def lock_influence_weights_in_hierarchy(object_name: str, object_name_pattern: str) -> int:
    """Lock the influence weights on the joints starting at specified root for all child nodes matching name pattern.

    :param object_name: The root object name.
    :param object_name_pattern: the f-string pattern used to match joint objects.
    :return: The number of objects matched.
    """
    transformed = 0
    matched_object_names = cmds.ls(object_name, exactType="joint")
    if 1 == len(matched_object_names):
        if parse(object_name_pattern, object_name):
            lock_influence_weights(object_name)
            transformed += 1
    elif 0 != len(matched_object_names):
        raise Exception(f"Multiple objects detected with the name {object_name}. Aborting!")

    children = cmds.listRelatives(object_name)
    if children:
        for child in children:
            transformed += lock_influence_weights_in_hierarchy(child, object_name_pattern)

    return transformed


def analyze_control_transform(object_name: str) -> bool:
    """Check that the control conforms to expected shape and conventions.

    :param object_name: the name of the object to check.
    :return: False if the object exists and is invalid, else True.
    """
    for attr in ["translate", "rotate"]:
        for axis in ["X", "Y", "Z"]:
            attr_name = f'{object_name}.{attr}{axis}'
            if 0 != cmds.getAttr(attr_name):
                print(f"{object_name} BAD - {attr_name} is not 0")
                return False
            elif not cmds.getAttr(attr_name, lock=True) and not cmds.getAttr(attr_name, settable=True):
                print(f"{object_name} BAD - {attr_name} is not settable and not locked. Assuming it is connected")
                return False
    for axis in ["X", "Y", "Z"]:
        attr_name = f'{object_name}.scale{axis}'
        if 1 != cmds.getAttr(attr_name):
            print(f"{object_name} BAD - {attr_name} is not 1")
            return False
        elif not cmds.getAttr(attr_name, lock=True) and not cmds.getAttr(attr_name, settable=True):
            print(f"{object_name} BAD - {attr_name} is not settable and not locked. Assuming it is connected")
            return False
    # noinspection PyTypeChecker
    constraints = cmds.listRelatives(object_name,
                                     type=["parentConstraint",
                                           "pointConstraint",
                                           "orientConstraint",
                                           "scaleConstraint",
                                           "aimConstraint",
                                           "pointOnPolyConstraint"])
    if constraints and 0 != len(constraints):
        print(f"{object_name} BAD - Constraints exist: {constraints}")
        return False
    return True


def analyze_control_transforms_in_hierarchy(object_name: str, object_name_pattern: str) -> int:
    """Check that the controls in object hierarchy conform to expected shape and conventions.

    :param object_name: The root object name.
    :param object_name_pattern: the f-string pattern used to match control transforms.
    :return: The number of invalid controls.
    """
    bad_controls = 0
    matched_object_names = cmds.ls(object_name, exactType="transform")
    if 1 == len(matched_object_names):
        if parse(object_name_pattern, object_name):
            if not analyze_control_transform(object_name):
                bad_controls += 1
    elif 0 != len(matched_object_names):
        raise Exception(f"Multiple objects detected with the name {object_name}. Aborting!")

    children = cmds.listRelatives(object_name)
    if children:
        for child in children:
            bad_controls += analyze_control_transforms_in_hierarchy(child, object_name_pattern)

    return bad_controls


def analyze_joint(object_name: str) -> bool:
    """Check that the joint conforms to expected shape and conventions.

    :param object_name: the name of the object to check.
    :return: False if the object exists and is invalid, else True.
    """
    for attr in ["jointOrient"]:
        for axis in ["X", "Y", "Z"]:
            attr_name = f'{object_name}.{attr}{axis}'
            if 0 != cmds.getAttr(attr_name):
                print(f"{object_name} BAD - {attr_name} is not 0")
                return False
    return True


def analyze_joints_in_hierarchy(object_name: str, object_name_pattern: str) -> int:
    """Check that the joints in object hierarchy conform to expected shape and conventions.

    :param object_name: The root object name.
    :param object_name_pattern: the f-string pattern used to match joint.
    :return: The number of invalid joints.
    """
    bad_joints = 0
    matched_object_names = cmds.ls(object_name, exactType="joint")
    if 1 == len(matched_object_names):
        if parse(object_name_pattern, object_name):
            if not analyze_joint(object_name):
                bad_joints += 1
    elif 0 != len(matched_object_names):
        raise Exception(f"Multiple objects detected with the name {object_name}. Aborting!")

    children = cmds.listRelatives(object_name)
    if children:
        for child in children:
            bad_joints += analyze_joints_in_hierarchy(child, object_name_pattern)

    return bad_joints
