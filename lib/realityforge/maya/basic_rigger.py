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


# TODO: In the future we should allow things like root group, controls group, controls set etc be prefixed
#  with a character name or like in some sort of templateable fashion. (alternatively we could just
#  have functions that create variants with prefixes?)

class RiggingSettings:
    def __init__(self,
                 root_group: Optional[str] = "rig",
                 controls_group: Optional[str] = "controls_GRP",
                 control_set: Optional[str] = "controlsSet",
                 use_driver_hierarchy: bool = True,
                 use_control_hierarchy: bool = False,
                 use_control_set: bool = True,
                 driven_joint_name_pattern: str = "{name}_JNT",
                 driver_joint_name_pattern: str = "{name}_JDRV2",
                 ik_joint_name_pattern: str = "{name}_IK_JDRV2",
                 fk_joint_name_pattern: str = "{name}_FK_JDRV2",
                 offset_group_name_pattern: str = "{name}_OFF_GRP2",
                 control_name_pattern: str = "{name}_CTRL2",
                 sided_name_pattern: str = "{name}_{side}",
                 cog_base_control_name: str = "cog2",
                 world_offset_base_control_name: str = "world_offset2",

                 # Should this variable be set on created elements? If so the user can change the
                 # "Settings > Selection > Selection Child Highlighting" config via the menu item
                 # "Windows > Settings/Preferences > Preferences" so that highlighting will not
                 # flow down the hierarchy
                 selection_child_highlighting: bool = False,
                 debug_logging: bool = True):
        self.root_group = root_group
        self.controls_group = controls_group
        self.control_set = control_set
        self.use_driver_hierarchy = use_driver_hierarchy
        self.use_control_hierarchy = use_control_hierarchy
        self.use_control_set = use_control_set
        self.driven_joint_name_pattern = driven_joint_name_pattern
        self.driver_joint_name_pattern = driver_joint_name_pattern
        self.ik_joint_name_pattern = ik_joint_name_pattern
        self.fk_joint_name_pattern = fk_joint_name_pattern
        self.offset_group_name_pattern = offset_group_name_pattern
        self.control_name_pattern = control_name_pattern
        self.sided_name_pattern = sided_name_pattern
        self.cog_base_control_name = cog_base_control_name
        self.world_offset_base_control_name = world_offset_base_control_name
        self.selection_child_highlighting = selection_child_highlighting
        self.debug_logging = debug_logging


# TODO: This following method should also:
# - check that the incoming joint chain is valid in that it
#    - has 0 jointOrient
#    - has preferred angle set for internal joints in IK chains
#    - has skin clusters for all joins except those that are on an allow list for no clusters
#    - has joint orientations that are world for certain joints chains????

def process_joint(joint_name: str,
                  parent_joint_name: Optional[str] = None,
                  rigging_settings: RiggingSettings = RiggingSettings()) -> None:
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
        cmds.makeIdentity(driver_joint_name,
                          apply=True,
                          rotate=True,
                          translate=True,
                          preserveNormals=True,
                          scale=True,
                          normal=False)

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

    if not parent_joint_name:
        root_offset_group_name = rigging_settings.offset_group_name_pattern.format(name=base_joint_name)
        world_offset_offset_group_name = \
            rigging_settings.offset_group_name_pattern.format(name=rigging_settings.world_offset_base_control_name)
        cog_offset_group_name = \
            rigging_settings.offset_group_name_pattern.format(name=rigging_settings.cog_base_control_name)

        if rigging_settings.debug_logging:
            print(f"Creating root control starting at '{base_joint_name}'")

        create_offset_group(root_offset_group_name, joint_name, rigging_settings)

        if rigging_settings.controls_group:
            safe_parent("root offset group", root_offset_group_name, rigging_settings.controls_group, rigging_settings)
        elif rigging_settings.root_group:
            safe_parent("root offset group", root_offset_group_name, rigging_settings.root_group, rigging_settings)

        root_control_name = create_control(base_joint_name, rigging_settings)
        safe_parent("world offset control", root_control_name, root_offset_group_name, rigging_settings)

        if rigging_settings.debug_logging:
            print(f"Creating world offset control starting at '{root_control_name}'")

        create_offset_group(world_offset_offset_group_name, joint_name, rigging_settings)
        if rigging_settings.use_control_hierarchy:
            safe_parent("world offset group", world_offset_offset_group_name, root_control_name, rigging_settings)
        else:
            if rigging_settings.controls_group:
                safe_parent("world offset group",
                            world_offset_offset_group_name,
                            rigging_settings.controls_group,
                            rigging_settings)
            elif rigging_settings.root_group:
                safe_parent("world offset group",
                            world_offset_offset_group_name,
                            rigging_settings.root_group,
                            rigging_settings)
            parentConstraint(world_offset_offset_group_name, root_control_name)
            scaleConstraint(world_offset_offset_group_name, root_control_name)

        world_offset_control_name = create_control(rigging_settings.world_offset_base_control_name, rigging_settings)
        safe_parent("world offset control", world_offset_control_name, world_offset_offset_group_name, rigging_settings)

        if rigging_settings.debug_logging:
            print(f"Creating cog control starting at '{root_control_name}'")

        create_offset_group(cog_offset_group_name, joint_name, rigging_settings)
        if rigging_settings.use_control_hierarchy:
            safe_parent("cog offset group", cog_offset_group_name, world_offset_control_name, rigging_settings)
        else:
            if rigging_settings.controls_group:
                safe_parent("cog offset group",
                            cog_offset_group_name,
                            rigging_settings.controls_group,
                            rigging_settings)
            elif rigging_settings.root_group:
                safe_parent("cog offset group",
                            cog_offset_group_name,
                            rigging_settings.root_group,
                            rigging_settings)
            parentConstraint(cog_offset_group_name, world_offset_control_name)
            scaleConstraint(cog_offset_group_name, world_offset_control_name)

        cog_control_name = create_control(rigging_settings.cog_base_control_name, rigging_settings)
        safe_parent("cog control", cog_control_name, cog_offset_group_name, rigging_settings)

    child_joints = cmds.listRelatives(joint_name, type="joint")
    if child_joints:
        for child_joint_name in child_joints:
            process_joint(child_joint_name, joint_name, rigging_settings)


def scaleConstraint(driven_name, driverl_name):
    cmds.scaleConstraint(driverl_name,
                         driven_name,
                         name=f"{driven_name}_scaleConstraint_{driverl_name}")


def parentConstraint(driven_name, driver_name):
    cmds.parentConstraint(driver_name,
                          driven_name,
                          name=f"{driven_name}_parentConstraint_{driver_name}")


def safe_parent(label, object_name, parent_group_name, rigging_settings):
    if rigging_settings.debug_logging:
        print(f"Parenting {label} '{object_name}' to '{parent_group_name}'")
    parented = cmds.parent(object_name, parent_group_name)
    if 0 == len(parented):
        raise Exception(f"Failed to parent '{object_name}' under '{parent_group_name}'")


def create_offset_group(object_name: str, object_name_to_match: str, rigging_settings: RiggingSettings) -> None:
    if rigging_settings.debug_logging:
        print(f"Creating offset group '{object_name}' matching '{object_name_to_match}'")
    util.ensure_single_object_named(None, object_name_to_match)
    actual_object_name = cmds.group(name=object_name, empty=True)
    util.ensure_created_object_name_matches("offset group", actual_object_name, object_name)
    cmds.matchTransform(object_name, object_name_to_match)
    set_selection_child_highlighting(object_name, rigging_settings)


def create_control(base_name: str, rigging_settings: RiggingSettings) -> str:
    control_name = rigging_settings.control_name_pattern.format(name=base_name)
    offset_group_name = rigging_settings.offset_group_name_pattern.format(name=base_name)
    if rigging_settings.debug_logging:
        print(f"Creating control '{control_name}' in offset group '{offset_group_name}'")
    util.ensure_single_object_named(None, offset_group_name)

    # TODO: In the future we should support all sorts of control types (copy from catalog?) and
    #  scaling based on bone size and all sorts of options. For now we go with random control shape
    actual_control_name = cmds.circle(name=control_name)[0]
    util.ensure_created_object_name_matches("offset group", actual_control_name, control_name)
    set_selection_child_highlighting(control_name, rigging_settings)

    # TODO: At some point we may decide to filter which controls go into the control set
    if rigging_settings.use_control_set:
        cmds.sets(control_name, edit=True, forceElement=rigging_settings.control_set)

    return control_name


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
        set_selection_child_highlighting(rigging_settings.root_group, rigging_settings)
        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)
        if rigging_settings.debug_logging:
            print(f"Created root group '{rigging_settings.root_group}'")

    if rigging_settings.controls_group:
        actual_controls_group_name = cmds.group(name=rigging_settings.controls_group, empty=True)
        util.ensure_created_object_name_matches("controls group",
                                                actual_controls_group_name,
                                                rigging_settings.controls_group)
        set_selection_child_highlighting(rigging_settings.controls_group, rigging_settings)
        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)
        if rigging_settings.root_group:
            safe_parent("controls group",
                        rigging_settings.controls_group,
                        rigging_settings.root_group,
                        rigging_settings)

            # Clear selection to avoid unintended selection dependent behaviour
            cmds.select(clear=True)

    if rigging_settings.use_control_set:
        control_sets = cmds.ls(rigging_settings.control_set, exactType="objectSet")
        if 0 == len(control_sets):
            if rigging_settings.debug_logging:
                print(f"Creating controls set '{rigging_settings.root_group}'")
        elif 1 == len(control_sets):
            if rigging_settings.debug_logging:
                print(f"Re-creating control set '{rigging_settings.root_group}'")
            cmds.delete(rigging_settings.control_set)
        else:
            raise Exception(f"Control set '{rigging_settings.control_set}' already has multiple instances. Aborting!")

        cmds.sets(name=rigging_settings.control_set, empty=True)

        if rigging_settings.debug_logging:
            print(f"Created control set '{rigging_settings.control_set}'")
