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
from parse import parse
import realityforge.maya.util as util


class RiggingSettings:
    def __init__(self,
                 root_group: Optional[str] = "rig",
                 controls_group: Optional[str] = "controls",
                 use_driver_hierarchy: bool = True,
                 driven_joint_name_pattern: str = "{name}_JNT",
                 driver_joint_name_pattern: str = "{name}_JDRV2",
                 ik_joint_name_pattern: str = "{name}_IK_JDRV2",
                 fk_joint_name_pattern: str = "{name}_FK_JDRV2",
                 offset_group_name_pattern: str = "{name}_OFF_GRP2",
                 control_name_pattern: str = "{name}_CTRL2",
                 sided_name_pattern: str = "{name}_{side}",
                 debug_logging: bool = True):
        self.root_group = root_group
        self.controls_group = controls_group
        self.use_driver_hierarchy = use_driver_hierarchy
        self.driven_joint_name_pattern = driven_joint_name_pattern
        self.driver_joint_name_pattern = driver_joint_name_pattern
        self.ik_joint_name_pattern = ik_joint_name_pattern
        self.fk_joint_name_pattern = fk_joint_name_pattern
        self.offset_group_name_pattern = offset_group_name_pattern
        self.control_name_pattern = control_name_pattern
        self.sided_name_pattern = sided_name_pattern
        self.debug_logging = debug_logging


DefaultRiggingSettings = RiggingSettings()


def process_joint(joint_name: str,
                  parent_joint_name: Optional[str] = None,
                  rigging_settings: RiggingSettings = DefaultRiggingSettings) -> None:
    if rigging_settings.debug_logging:
        print(f"Attempting to process joint '{joint_name}' with parent joint named '{parent_joint_name}'")

    # Ensure there is a single joint of expected name
    util.ensure_single_object_named("joint", joint_name)

    # Ensure there is a single parent joint of expected name
    if parent_joint_name:
        util.ensure_single_object_named("joint", parent_joint_name)

    # Derive the base name
    driven_joint_name_result = parse(rigging_settings.driven_joint_name_pattern, joint_name)
    if not driven_joint_name_result:
        raise Exception(f"Joint named '{joint_name}' does not match expected pattern "
                        f"'{rigging_settings.driven_joint_name_pattern}'. Aborting!")
    base_joint_name = driven_joint_name_result.named["name"]

    # Derive the base parent name
    if parent_joint_name:
        driven_parent_joint_name_result = parse(rigging_settings.driven_joint_name_pattern, parent_joint_name)
        if not driven_parent_joint_name_result:
            raise Exception(f"Parent joint named '{parent_joint_name}' does not match expected pattern "
                            f"'{rigging_settings.driven_joint_name_pattern}'. Aborting!")
        base_parent_joint_name = driven_parent_joint_name_result.named["name"]
    else:
        base_parent_joint_name = None

    # Setup the root group for rig ... if required
    if not parent_joint_name:
        setup_top_level_group(rigging_settings)

    # Setup the driver joint chain
    if rigging_settings.use_driver_hierarchy:
        driver_joint_name = rigging_settings.driver_joint_name_pattern.format(name=base_joint_name)

        if rigging_settings.debug_logging:
            print(f"Creating driver joint '{driver_joint_name}'")

        actual_driver_joint_name = cmds.joint(name=driver_joint_name)

        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)

        util.ensure_created_object_name_matches("driver joint", actual_driver_joint_name, driver_joint_name)

        cmds.matchTransform(driver_joint_name, joint_name)
        cmds.makeIdentity(driver_joint_name, apply=True, rotate=True)

        util.copy_attributes(joint_name,
                             driver_joint_name,
                             [
                                 # Joint Attributes
                                 "drawStyle",
                                 "radius",
                                 "jointTypeX", "jointTypeY", "jointTypeZ",
                                 "preferredAngleX", "preferredAngleY", "preferredAngleZ",
                                 "jointOrientX", "jointOrientY", "jointOrientZ",
                                 "segmentScaleCompensate",
                                 # Joint Labelling
                                 "side",
                                 "type",
                                 "drawLabel"
                             ]
                             )

        if parent_joint_name:
            driver_parent_joint_name = rigging_settings.driver_joint_name_pattern.format(name=base_parent_joint_name)
            if rigging_settings.debug_logging:
                print(f"Parenting driver joint '{driver_joint_name}' to '{driver_parent_joint_name}'")

            parented = cmds.parent(driver_joint_name, driver_parent_joint_name)
            if 0 == len(parented):
                raise Exception(f"Failed to parent '{driver_joint_name}' under '{driver_parent_joint_name}'")
        elif rigging_settings.root_group:
            safe_parent("driver joint", driver_joint_name, rigging_settings.root_group, rigging_settings)

        if rigging_settings.debug_logging:
            print(f"Driver joint '{driver_joint_name}' created.")

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)

    child_joints = cmds.listRelatives(joint_name, type="joint")
    if child_joints:
        for child_joint_name in child_joints:
            process_joint(child_joint_name, joint_name, rigging_settings)


def safe_parent(label, object_name, parent_group_name, rigging_settings):
    if rigging_settings.debug_logging:
        print(f"Parenting {label} '{object_name}' to '{parent_group_name}'")
    parented = cmds.parent(object_name, parent_group_name)
    if 0 == len(parented):
        raise Exception(f"Failed to parent '{object_name}' under '{parent_group_name}'")


def setup_top_level_group(rigging_settings: RiggingSettings) -> None:
    if rigging_settings.root_group:
        root_groups = cmds.ls(rigging_settings.root_group, exactType="transform")
        if 0 == len(root_groups):
            if rigging_settings.debug_logging:
                print(f"Creating root group '{rigging_settings.root_group}'")
        elif 1 == len(root_groups):
            if rigging_settings.debug_logging:
                print(f"Re-creating root group '{rigging_settings.root_group}'")
            cmds.delete(rigging_settings.root_group)
        else:
            raise Exception(f"Root group '{rigging_settings.root_group}' already has multiple instances. Aborting!")

        actual_root_group_name = cmds.group(name=rigging_settings.root_group, empty=True)
        util.ensure_created_object_name_matches("root group", actual_root_group_name, rigging_settings.root_group)
        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)

    if rigging_settings.controls_group:
        actual_controls_group_name = cmds.group(name=rigging_settings.controls_group, empty=True)
        util.ensure_created_object_name_matches("controls group",
                                                actual_controls_group_name,
                                                rigging_settings.controls_group)
        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)
        if rigging_settings.root_group:
            safe_parent("controls group",
                        rigging_settings.controls_group,
                        rigging_settings.root_group,
                        rigging_settings)

            # Clear selection to avoid unintended selection dependent behaviour
            cmds.select(clear=True)
