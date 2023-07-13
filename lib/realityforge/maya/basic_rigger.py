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

from typing import Optional

import maya.cmds as cmds
from parse import parse

import realityforge.maya.rigging_tools as rigging_tools
import realityforge.maya.util as util

__all__ = ['RiggingSettings', 'create_rig']


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
                 sided_name_pattern: str = "{name}_{side}_{seq}",
                 cog_base_control_name: str = "cog2",
                 world_offset_base_control_name: str = "world_offset2",
                 left_side_color: Optional[tuple[float, float, float]] = (1, 0, 0),
                 right_side_color: Optional[tuple[float, float, float]] = (0, 0, 1),
                 center_side_color: Optional[tuple[float, float, float]] = (1, 1, 0),
                 none_side_color: Optional[tuple[float, float, float]] = None,
                 left_side_name: Optional[str] = "l",
                 right_side_name: Optional[str] = "r",
                 center_side_name: Optional[str] = None,
                 none_side_name: Optional[str] = None,

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
        self.left_side_color = left_side_color
        self.right_side_color = right_side_color
        self.center_side_color = center_side_color
        self.none_side_color = none_side_color
        self.left_side_name = left_side_name
        self.right_side_name = right_side_name
        self.center_side_name = center_side_name
        self.none_side_name = none_side_name


def create_rig(root_joint_name: str, rigging_settings: RiggingSettings = RiggingSettings()) -> None:
    if rigging_settings.debug_logging:
        print(f"Creating rig with root joint '{root_joint_name}'")

    process_joint(rigging_settings, root_joint_name)

    if rigging_settings.debug_logging:
        print(f"Rig created for root joint '{root_joint_name}'")


# TODO: This following method should also:
# - check that the incoming joint chain is valid in that it
#    - has 0 jointOrient
#    - has preferred angle set for internal joints in IK chains
#    - has skin clusters for all joins except those that are on an allow list for no clusters
#    - has joint orientations that are world for certain joints chains????
#    - joints have sides specified as non None unless explicitly overriden

def process_joint(rigging_settings: RiggingSettings,
                  joint_name: str,
                  parent_joint_name: Optional[str] = None,
                  parent_control_name: Optional[str] = None) -> None:
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

        if parent_joint_name:
            driver_parent_joint_name = rigging_settings.driver_joint_name_pattern.format(name=base_parent_joint_name)
            if rigging_settings.debug_logging:
                print(f"Parenting driver joint '{driver_joint_name}' to '{driver_parent_joint_name}'")

            parented = cmds.parent(driver_joint_name, driver_parent_joint_name)
            if 0 == len(parented):
                raise Exception(f"Failed to parent '{driver_joint_name}' under '{driver_parent_joint_name}'")
        elif rigging_settings.root_group:
            safe_parent("driver joint", driver_joint_name, rigging_settings.root_group, rigging_settings)

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
                                 "drawLabel",
                                 # Drawing Overrides
                                 "overrideEnabled",
                                 "overrideColor",
                                 "overridePlayback",
                                 "overrideShading",
                                 "overrideVisibility",
                                 "overrideTexturing",
                             ]
                             )
        set_selection_child_highlighting(driver_joint_name, rigging_settings)

        if rigging_settings.debug_logging:
            print(f"Driver joint '{driver_joint_name}' created.")

        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)

    if not parent_joint_name:
        root_control_name = setup_control("root", base_joint_name, joint_name, parent_control_name, rigging_settings)

        world_offset_control_name = setup_control("world offset",
                                                  rigging_settings.world_offset_base_control_name,
                                                  joint_name,
                                                  root_control_name,
                                                  rigging_settings)
        control_name = setup_control("cog",
                                     rigging_settings.cog_base_control_name,
                                     joint_name,
                                     world_offset_control_name,
                                     rigging_settings)
    else:
        control_name = setup_control(base_joint_name,
                                     base_joint_name,
                                     joint_name,
                                     parent_control_name,
                                     rigging_settings)

    child_joints = cmds.listRelatives(joint_name, type="joint")
    if child_joints:
        for child_joint_name in child_joints:
            process_joint(rigging_settings, child_joint_name, joint_name, control_name)


def set_selection_child_highlighting(object_name, rigging_settings):
    selection_child_highlighting = 1 if rigging_settings.selection_child_highlighting else 0
    # noinspection PyTypeChecker
    cmds.setAttr(f"{object_name}.selectionChildHighlighting", selection_child_highlighting)


def setup_control(label: str,
                  base_control_name: str,
                  joint_name: str,
                  parent_control_name: Optional[str],
                  rigging_settings: RiggingSettings) -> str:
    if rigging_settings.debug_logging:
        print(f"Creating {label} control with parent '{parent_control_name}'")

    offset_group_name = rigging_settings.offset_group_name_pattern.format(name=base_control_name)
    create_offset_group(offset_group_name, joint_name, rigging_settings)
    if rigging_settings.use_control_hierarchy and parent_control_name:
        safe_parent(f"{label} offset group", offset_group_name, parent_control_name, rigging_settings)
    else:
        if rigging_settings.controls_group:
            safe_parent(f"{label} offset group",
                        offset_group_name,
                        rigging_settings.controls_group,
                        rigging_settings)
        elif rigging_settings.root_group:
            safe_parent(f"{label} offset group",
                        offset_group_name,
                        rigging_settings.root_group,
                        rigging_settings)
        if parent_control_name:
            parent_constraint(offset_group_name, parent_control_name, True)
            scale_constraint(offset_group_name, parent_control_name)

    rigging_tools.lock_and_hide_transform_properties(offset_group_name)
    cmds.select(clear=True)

    joint_side = cmds.getAttr(f"{joint_name}.side")
    if 0 == joint_side:
        side = "center"
        expect_control_matches_side(side, rigging_settings.center_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.left_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.right_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.none_side_name, base_control_name, rigging_settings)
    elif 1 == joint_side:
        side = "left"
        expect_control_not_match_side(side, rigging_settings.center_side_name, base_control_name, rigging_settings)
        expect_control_matches_side(side, rigging_settings.left_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.right_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.none_side_name, base_control_name, rigging_settings)
    elif 2 == joint_side:
        side = "right"
        expect_control_not_match_side(side, rigging_settings.center_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.left_side_name, base_control_name, rigging_settings)
        expect_control_matches_side(side, rigging_settings.right_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.none_side_name, base_control_name, rigging_settings)
    else:
        side = "none"
        expect_control_not_match_side(side, rigging_settings.center_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.left_side_name, base_control_name, rigging_settings)
        expect_control_not_match_side(side, rigging_settings.right_side_name, base_control_name, rigging_settings)
        expect_control_matches_side(side, rigging_settings.none_side_name, base_control_name, rigging_settings)

    control_name = create_control(base_control_name, rigging_settings)
    safe_parent(f"{label} control", control_name, offset_group_name, rigging_settings)

    cmds.addAttr(control_name, longName="rfJointSide", niceName="Joint Side", dataType="string")
    cmds.setAttr(f"{control_name}.rfJointSide", side, type="string")

    set_override_colors_based_on_side(control_name, rigging_settings)

    return control_name


def expect_control_matches_side(side, side_label, base_control_name, rigging_settings) -> None:
    if side_label:
        p = rigging_settings.sided_name_pattern.replace("{side}", side_label)
        if not parse(p, base_control_name) and \
                not parse(p.replace("_{seq}", ""), base_control_name) and \
                not parse(p.replace("{seq}_", ""), base_control_name):
            raise Exception(f"Invalid name detected when creating control for side '{side}' with base "
                            f"name '{base_control_name}' which was expected to match '{expected_name_pattern}'")


def expect_control_not_match_side(side, side_label, base_control_name, rigging_settings) -> None:
    if side_label:
        p = rigging_settings.sided_name_pattern.replace("{side}", side_label)
        if parse(p, base_control_name) or \
                parse(p.replace("_{seq}", ""), base_control_name) or \
                parse(p.replace("{seq}_", ""), base_control_name):
            raise Exception(f"Invalid name detected when creating control for side '{side}' with base "
                            f"name '{base_control_name}' which un-expectedly matched '{expected_name_pattern}'")


def set_override_colors_based_on_side(control_name: str, rigging_settings: RiggingSettings) -> None:
    side = cmds.getAttr(f"{control_name}.rfJointSide")
    child_shapes = cmds.listRelatives(control_name, type="nurbsCurve")
    if child_shapes:
        for child in child_shapes:
            if "center" == side:
                set_override_color_attributes(child, rigging_settings.center_side_color)
            elif "left" == side:
                set_override_color_attributes(child, rigging_settings.left_side_color)
            elif "right" == side:
                set_override_color_attributes(child, rigging_settings.right_side_color)
            else:
                # noinspection DuplicatedCode
                set_override_color_attributes(child, rigging_settings.none_side_color)


# noinspection PyTypeChecker
def set_override_color_attributes(object_name: str, color: tuple[float, float, float]):
    if color:
        cmds.setAttr(f"{object_name}.overrideEnabled", True)
        cmds.setAttr(f"{object_name}.overrideRGBColors", True)
        cmds.setAttr(f"{object_name}.overrideColorR", color[0])
        cmds.setAttr(f"{object_name}.overrideColorG", color[1])
        cmds.setAttr(f"{object_name}.overrideColorB", color[2])


def scale_constraint(driven_name, driver_name):
    cmds.scaleConstraint(driver_name,
                         driven_name,
                         name=f"{driven_name}_scaleConstraint_{driver_name}")


def parent_constraint(driven_name, driver_name, maintain_offset: bool = False):
    cmds.parentConstraint(driver_name,
                          driven_name,
                          maintainOffset=maintain_offset,
                          name=f"{driver_name}_parentConstraint_{driven_name}")


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
    actual_control_name = cmds.circle(name=control_name, normalX=1, normalY=0, normalZ=0, radius=1)[0]
    util.ensure_created_object_name_matches("offset group", actual_control_name, control_name)
    set_selection_child_highlighting(control_name, rigging_settings)

    cmds.select(clear=True)

    parent_constraint(control_name, offset_group_name, False)

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

# TODO: Features to add:
# * a "set" that includes the joints to export as a skeleton
# * a "set" that includes the joints and mesh to export as a skeletal mesh
# * put controls in layers so that they can be turned off individually (Remove visibility switch from controls? or support both?). See Azri rig for example
# * Generate ik/fk (and stretch???) chains for limbs and switch between them? (See https://www.youtube.com/playlist?list=PLgala72Uap1rtRRi-MAI0RMc7w1fpD2Io
