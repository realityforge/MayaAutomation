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

import realityforge.maya.util as util

__all__ = ['IkChain', 'RiggingSettings', 'create_rig', 'copy_control_from_selection']


# TODO: In the future we should allow things like root group, controls group, controls set etc be prefixed
#  with a character name or like in some sort of templateable fashion. (alternatively we could just
#  have functions that create variants with prefixes?)

# TODO: Allow/Deny list for which attributes should be locked and removed from channelbox so animators
#  do not see them. i.e. Remove the ability for any FK controls to scale or translate unless allow listed?
#  Probably have a default allow state and then an exception list (probably do it per attribute? or per attribute group?

# TODO: Add display layer that contains the "controls_GRP" so can hide all controls with one click.
# TODO: Add display layers for groups of controls starting at a root. (so could have layer for LH or RH)

# TODO: Features to add:
# * a "set" that includes the joints to export as a skeleton
# * a "set" that includes the joints and mesh to export as a skeletal mesh
# * put controls in layers so that they can be turned off individually (Remove visibility switch from controls? or support both?). See Azri rig for example
# * Generate ik/fk (and stretch???) chains for limbs and switch between them? (See https://www.youtube.com/playlist?list=PLgala72Uap1rtRRi-MAI0RMc7w1fpD2Io


# TODO: Add validation before creating rig
# - check that the incoming joint chain is valid in that it
#    - has 0 jointOrient
#    - has preferred angle set for internal joints in IK chains
#    - has joint orientations that are world for certain joints chains????
#    - joints have sides specified as non None unless explicitly overriden

class IkChain:
    def __init__(self, name: str, joints: list[str], effector_name: Optional[str] = None):
        self.name = name
        self.joints = joints
        self.effector_name = effector_name if effector_name else f"{name}_end"

    def does_chain_start_at_joint(self, joint_base_name: str) -> bool:
        """Return True if the chain starts at the specified joint.

        :param joint_base_name: the base name of the joint to check
        :return True if the chain starts at the specified joint, false otherwise.
        """
        return joint_base_name == self.joints[0]

    def does_chain_contain_joint(self, joint_base_name: str) -> bool:
        """Return True if the chain contains the specified joint.

        :param joint_base_name: the base name of the joint to check
        :return True if the chain contains the specified joint, false otherwise.
        """
        return joint_base_name in self.joints

    def does_chain_end_at_joint(self, joint_base_name: str) -> bool:
        """Return True if the chain ends at the specified joint.

        :param joint_base_name: the base name of the joint to check
        :return True if the chain ends at the specified joint, false otherwise.
        """
        return joint_base_name == self.joints[-1]


class RiggingSettings:
    def __init__(self,
                 root_group: Optional[str] = "rig",
                 controls_group: Optional[str] = "controls_GRP",
                 control_set: Optional[str] = "controlsSet",
                 use_driver_hierarchy: bool = True,
                 use_control_hierarchy: bool = False,
                 use_control_set: bool = True,
                 driven_joint_name_pattern: str = "{name}_JNT",
                 driver_joint_name_pattern: str = "{name}_JDRV",
                 effector_name_pattern: str = "{name}_GRP",
                 ik_system_name_pattern: str = "{name}_IK_SYS",
                 ik_joint_base_name_pattern: str = "{name}_{chain}_IK",
                 fk_joint_base_name_pattern: str = "{name}_{chain}_FK",
                 offset_group_name_pattern: str = "{name}_OFF_GRP",
                 control_name_pattern: str = "{name}_CTRL",
                 sided_name_pattern: str = "{name}_{side}_{seq}",
                 cog_base_control_name: str = "cog",
                 world_offset_base_control_name: str = "world_offset",
                 ik_chains: list[IkChain] = None,
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
        self.effector_name_pattern = effector_name_pattern
        self.ik_system_name_pattern = ik_system_name_pattern
        self.ik_joint_base_name_pattern = ik_joint_base_name_pattern
        self.fk_joint_base_name_pattern = fk_joint_base_name_pattern
        self.offset_group_name_pattern = offset_group_name_pattern
        self.control_name_pattern = control_name_pattern
        self.sided_name_pattern = sided_name_pattern
        self.cog_base_control_name = cog_base_control_name
        self.world_offset_base_control_name = world_offset_base_control_name
        self.selection_child_highlighting = selection_child_highlighting
        self.debug_logging = debug_logging
        self.ik_chains = ik_chains if ik_chains else []
        self.left_side_color = left_side_color
        self.right_side_color = right_side_color
        self.center_side_color = center_side_color
        self.none_side_color = none_side_color
        self.left_side_name = left_side_name
        self.right_side_name = right_side_name
        self.center_side_name = center_side_name
        self.none_side_name = none_side_name

    def derive_control_name(self, base_name: str) -> str:
        return self.control_name_pattern.format(name=base_name)

    def derive_offset_group_name(self, base_name: str) -> str:
        return self.offset_group_name_pattern.format(name=base_name)

    def derive_effector_name(self, ik_chain: IkChain) -> str:
        return self.effector_name_pattern.format(name=ik_chain.effector_name, chain=ik_chain.name)

    def derive_ik_system_name(self, ik_chain: IkChain) -> str:
        return self.ik_system_name_pattern.format(name=ik_chain.name)

    def derive_target_joint_name(self, base_name: str) -> str:
        return self.get_target_joint_pattern().format(name=base_name)

    def derive_source_joint_name(self, base_name: str) -> str:
        return self.driven_joint_name_pattern.format(name=base_name)

    def extract_source_joint_base_name(self, joint_name: str) -> str:
        result = parse(self.driven_joint_name_pattern, joint_name)
        if not result:
            raise Exception(f"Joint named '{joint_name}' does not match expected pattern "
                            f"'{self.driven_joint_name_pattern}'. Aborting!")
        return result.named["name"]

    def get_target_joint_pattern(self) -> str:
        return self.driver_joint_name_pattern if self.use_driver_hierarchy else self.driven_joint_name_pattern

    def derive_ik_joint_base_name(self, base_name: str, chain_name: str) -> str:
        return self.ik_joint_base_name_pattern.format(name=base_name, chain=chain_name)

    def derive_ik_joint_name(self, base_name: str, chain_name: str) -> str:
        return self.derive_target_joint_name(self.derive_ik_joint_base_name(base_name, chain_name))

    def derive_fk_joint_base_name(self, base_name: str, chain_name: str) -> str:
        return self.fk_joint_base_name_pattern.format(name=base_name, chain=chain_name)

    def derive_fk_joint_name(self, base_name: str, chain_name: str) -> str:
        return self.derive_target_joint_name(self.derive_fk_joint_base_name(base_name, chain_name))

    def get_ik_chain_starting_at_joint(self, joint_base_name: str) -> Optional[IkChain]:
        """Return the IkChain that starts at the specified joint

        :param joint_base_name: the base name of the joint that starts the chain
        :return the chain or None if no such IkChain.
        """
        for chain in self.ik_chains:
            if chain.does_chain_start_at_joint(joint_base_name):
                return chain

        return None

    def get_ik_chain_ending_at_joint(self, joint_base_name: str) -> Optional[IkChain]:
        """Return the IkChain that ends at the specified joint

        :param joint_base_name: the base name of the joint that ends the chain
        :return the chain or None if no such IkChain.
        """
        for chain in self.ik_chains:
            if chain.does_chain_end_at_joint(joint_base_name):
                return chain

        return None


def _lock_and_hide_transform_properties(object_name: str) -> None:
    """Lock and remove from the channelbox the attributes of the specified transform object.

    :param object_name: the name of the transform object.
    """
    for attr in ["translate", "rotate", "scale"]:
        for axis in ["X", "Y", "Z"]:
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=False)
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=False, keyable=False, channelBox=False)
    cmds.setAttr(f"{object_name}.visibility", lock=False, keyable=False, channelBox=False)


def copy_control_from_selection(rs: RiggingSettings = RiggingSettings()) -> None:
    selected = cmds.ls(selection=True)
    if 2 != len(selected):
        raise Exception("Need to select a source and a target control and try again.")
    copy_control(selected[0], selected[1], rs)


def copy_control(source_control_name: str, target_control_name: str, rs: RiggingSettings) -> None:
    if rs.debug_logging:
        print(f"Copying control shape from '{source_control_name}' to '{target_control_name}'")

    util.ensure_single_object_named("transform", source_control_name)
    util.ensure_single_object_named("transform", target_control_name)

    duplicate_object_name = cmds.duplicate(source_control_name, returnRootsOnly=True)[0]

    source_side = None
    target_side = None

    try:
        source_side = cmds.getAttr(f"{source_control_name}.rfJointSide")
    except:
        pass
    try:
        target_side = cmds.getAttr(f"{target_control_name}.rfJointSide")
    except:
        pass

    if source_side != target_side:
        if ("left" == source_side and "right" == target_side) or ("right" == source_side and "left" == target_side):
            cmds.setAttr(f"{duplicate_object_name}.scaleX", -1)
            cmds.setAttr(f"{duplicate_object_name}.scaleY", -1)
            cmds.setAttr(f"{duplicate_object_name}.scaleZ", -1)
            cmds.makeIdentity(duplicate_object_name,
                              apply=True,
                              rotate=True,
                              translate=True,
                              preserveNormals=True,
                              scale=True,
                              normal=False)

    target_children = cmds.listRelatives(target_control_name, type="nurbsCurve")
    if target_children:
        for child in target_children:
            cmds.delete(child)
    source_children = cmds.listRelatives(duplicate_object_name, type="nurbsCurve")
    if source_children:
        index = 0
        for child in source_children:
            index += 1
            cmds.parent(child, target_control_name, shape=True, relative=True)
            cmds.rename(child, f"{target_control_name}Shape{index}")

    cmds.delete(duplicate_object_name)
    try:
        cmds.bakePartialHistory(all=True, prePostDeformers=True)
    except:
        pass

    _set_override_colors_based_on_side(target_control_name, rs)


def create_rig(root_joint_name: str, rigging_settings: RiggingSettings = RiggingSettings()) -> None:
    if rigging_settings.debug_logging:
        print(f"Creating rig with root joint '{root_joint_name}'")

    # Check the ik chains are valid
    _validate_ik_chains(rigging_settings)

    _setup_top_level_infrastructure(rigging_settings)
    _process_joint(rigging_settings, root_joint_name)

    if rigging_settings.debug_logging:
        print(f"Rig created for root joint '{root_joint_name}'")


def _validate_ik_chains(rs: RiggingSettings) -> None:
    """Verify that the ik chains specified in the settings are valid.
    They are valid if the joints in the ik chains are not overlapping, exist in the scene and have matching
    hierarchy.

    :param rs: the settings to check.
    """
    # A map of joint name => chain name. Used to ensure that a joint internal to a chain does not appear
    # in multiple chains
    internal_joints_in_ik_chains = {}
    for chain in rs.ik_chains:
        if 0 == len(chain.joints):
            raise Exception(f"Attempted to define invalid ik chain named '{chain.name}' with no joints")
        terminal_joint_index = len(chain.joints) - 1
        index = terminal_joint_index
        while index > 0:
            current_joint_base_name = chain.joints[index]
            current_joint_name = rs.derive_source_joint_name(current_joint_base_name)
            expected_previous_joint_name = rs.derive_source_joint_name(chain.joints[index - 1])
            actual_previous_joint_name = util.get_parent(current_joint_name)

            if actual_previous_joint_name != expected_previous_joint_name:
                raise Exception(f"Attempted to define invalid ik chain named '{chain.name}' as joint "
                                f"named '{current_joint_name} has an actual parent '{actual_previous_joint_name} "
                                f"but the configuration expected parent with the name '{expected_previous_joint_name}'")
            if terminal_joint_index != index:
                # If we are not on the terminal joint in the chain (or the head joint as index > 0)
                if current_joint_base_name in internal_joints_in_ik_chains:
                    raise Exception(
                        f"Attempted to create overlapping ik joint chains where '{current_joint_base_name}' "
                        f"is in the chains named '{chain.name} and "
                        f"'{internal_joints_in_ik_chains[current_joint_base_name]}'")
                internal_joints_in_ik_chains[current_joint_base_name] = chain.name

            index -= 1

def _process_joint(rs: RiggingSettings,
                   joint_name: str,
                   parent_joint_name: Optional[str] = None,
                   parent_control_name: Optional[str] = None,
                   ik_chain: Optional[IkChain] = None) -> None:
    if rs.debug_logging:
        print(
            f"Attempting to process joint '{joint_name}' with parent joint named '{parent_joint_name}', parent control named '{parent_control_name}' and ik chain {ik_chain}")

    # Ensure there is a single joint of expected name
    util.ensure_single_object_named("joint", joint_name)

    # Ensure there is a single parent joint of expected name
    if parent_joint_name:
        util.ensure_single_object_named("joint", parent_joint_name)

    # Derive the base name
    base_joint_name = rs.extract_source_joint_base_name(joint_name)

    # Derive the base parent name
    base_parent_joint_name = rs.extract_source_joint_base_name(parent_joint_name) if parent_joint_name else None

    # Setup the driver joint chain
    if rs.use_driver_hierarchy:
        driver_joint_name = rs.derive_target_joint_name(base_joint_name)

        if rs.debug_logging:
            print(f"Creating driver joint '{driver_joint_name}'")

        actual_driver_joint_name = cmds.joint(name=driver_joint_name)

        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)

        util.ensure_created_object_name_matches("driver joint", actual_driver_joint_name, driver_joint_name)

        if parent_joint_name:
            driver_parent_joint_name = rs.derive_target_joint_name(base_parent_joint_name)
            if rs.debug_logging:
                print(f"Parenting driver joint '{driver_joint_name}' to '{driver_parent_joint_name}'")

            parented = cmds.parent(driver_joint_name, driver_parent_joint_name)
            if 0 == len(parented):
                raise Exception(f"Failed to parent '{driver_joint_name}' under '{driver_parent_joint_name}'")
        elif rs.root_group:
            _safe_parent("driver joint", driver_joint_name, rs.root_group, rs)

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
        _set_selection_child_highlighting(driver_joint_name, rs)

        if rs.debug_logging:
            print(f"Driver joint '{driver_joint_name}' created.")

        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)

    if not parent_joint_name:
        root_control_name = _setup_control("root", base_joint_name, joint_name, parent_control_name, rs)

        world_offset_control_name = _setup_control("world offset",
                                                   rs.world_offset_base_control_name,
                                                   joint_name,
                                                   root_control_name,
                                                   rs)
        control_name = _setup_control("cog",
                                      rs.cog_base_control_name,
                                      joint_name,
                                      world_offset_control_name,
                                      rs)
    else:
        control_name = _setup_control(base_joint_name,
                                      base_joint_name,
                                      joint_name,
                                      parent_control_name,
                                      rs)

    at_chain_start = False
    at_chain_end = False
    in_chain_middle = False

    if ik_chain:
        if ik_chain.does_chain_start_at_joint(base_joint_name):
            # TODO: Create Group to contain PV control, ik handle control and ik handle named "{chain}_SYS"
            # TODO: Create another Group using effector_name that will contain downstream controls and switch control

            world_offset_control = rs.derive_control_name(rs.world_offset_base_control_name)

            # Create a group for all the controls that are past the end off the ik chain and also
            # contains the IK/FK switch control
            _create_group("ik effector group", rs.derive_effector_name(ik_chain), world_offset_control, rs)

            # Create a group to contain the Ik Handle and the controls for the PoleVector and IkHandle
            _create_group("ik system group", rs.derive_ik_system_name(ik_chain), world_offset_control, rs)

            at_chain_start = True
        else:
            # Otherwise we create IK/FK controls and support joints
            # TODO: Create joints

            ik_joint_base_name = rs.derive_ik_joint_base_name(base_joint_name, ik_chain.name)
            fk_joint_base_name = rs.derive_fk_joint_base_name(base_joint_name, ik_chain.name)
            ik_parent_joint_name = None
            fk_parent_joint_name = None
            if base_parent_joint_name:
                ik_parent_joint_name = rs.derive_ik_joint_name(base_parent_joint_name, ik_chain.name)
                fk_parent_joint_name = rs.derive_fk_joint_name(base_parent_joint_name, ik_chain.name)

            _setup_control(ik_joint_base_name, ik_joint_base_name, joint_name, ik_parent_joint_name, rs)
            _setup_control(fk_joint_base_name, fk_joint_base_name, joint_name, fk_parent_joint_name, rs)

            if ik_chain.does_chain_end_at_joint(base_joint_name):
                # TODO: Create IK Handle in ik_system group
                # TODO: Create PV control in ik_system group
                # TODO: Create IK Handle control in ik_system group
                # TODO: Create IK/FK switch control in effector group
                at_chain_end = True
            else:
                in_chain_middle = True

    child_joints = cmds.listRelatives(joint_name, type="joint")
    if child_joints:
        for child_joint_name in child_joints:
            child_base_joint_name = rs.extract_source_joint_base_name(child_joint_name)
            child_parent_control_name = control_name
            child_ik_chain = None
            if at_chain_end:
                # If we are at the end of an ik chain then the child controls are placed in another group
                child_parent_control_name = rs.derive_effector_name(ik_chain)
                child_ik_chain = None
            elif in_chain_middle:
                if ik_chain.does_chain_contain_joint(child_base_joint_name):
                    child_ik_chain = ik_chain

            print(f"Looking for ik chain starting at {child_base_joint_name} when have {child_ik_chain}")
            if not child_ik_chain:
                child_ik_chain = rs.get_ik_chain_starting_at_joint(child_base_joint_name)

            _process_joint(rs, child_joint_name, joint_name, child_parent_control_name, child_ik_chain)


def _set_selection_child_highlighting(object_name: str, rs: RiggingSettings):
    selection_child_highlighting = 1 if rs.selection_child_highlighting else 0
    # noinspection PyTypeChecker
    cmds.setAttr(f"{object_name}.selectionChildHighlighting", selection_child_highlighting)


def _setup_control(label: str,
                   base_control_name: str,
                   joint_name: str,
                   parent_control_name: Optional[str],
                   rs: RiggingSettings) -> str:
    """Create a control offset group and control.

    :param label: the human-readable label indicating the name of the control. (This may differ from base_control_name for some of specialised top-level controls like cog, world offset, root if the user overrides the generated control names)
    :param base_control_name: the base name of the control, offset group etc.
    :param joint_name: the name of the joint that the offset group will match transforms to and derived side-edness from. This is typically the joint in source skeleton that we want to control.
    :param parent_control_name: the name of the control that this control will be logically parented to (either in direct hierarchy or with constraints depending on configuration)
    :param rs: the settings that drive the rigging process.
    :return: the name of the control.
    """
    if rs.debug_logging:
        print(f"Creating {label} control with parent '{parent_control_name}'")

    offset_group_name = rs.derive_offset_group_name(base_control_name)
    _create_group("offset group", offset_group_name, joint_name, rs)

    joint_side = cmds.getAttr(f"{joint_name}.side")
    if 0 == joint_side:
        side = "center"
        _expect_control_matches_side(side, rs.center_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.left_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.right_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.none_side_name, base_control_name, rs)
    elif 1 == joint_side:
        side = "left"
        _expect_control_not_match_side(side, rs.center_side_name, base_control_name, rs)
        _expect_control_matches_side(side, rs.left_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.right_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.none_side_name, base_control_name, rs)
    elif 2 == joint_side:
        side = "right"
        _expect_control_not_match_side(side, rs.center_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.left_side_name, base_control_name, rs)
        _expect_control_matches_side(side, rs.right_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.none_side_name, base_control_name, rs)
    else:
        side = "none"
        _expect_control_not_match_side(side, rs.center_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.left_side_name, base_control_name, rs)
        _expect_control_not_match_side(side, rs.right_side_name, base_control_name, rs)
        _expect_control_matches_side(side, rs.none_side_name, base_control_name, rs)

    control_name = _create_control(base_control_name, rs)
    _safe_parent(f"{label} control", control_name, offset_group_name, rs)

    cmds.addAttr(control_name, longName="rfJointSide", niceName="Joint Side", dataType="string")
    cmds.setAttr(f"{control_name}.rfJointSide", side, type="string")

    _set_override_colors_based_on_side(control_name, rs)

    return control_name


def _expect_control_matches_side(side: str, side_label: str, base_control_name: str, rs: RiggingSettings) -> None:
    if side_label:
        p = rs.sided_name_pattern.replace("{side}", side_label)
        if not parse(p, base_control_name) and \
                not parse(p.replace("_{seq}", ""), base_control_name) and \
                not parse(p.replace("{seq}_", ""), base_control_name):
            raise Exception(f"Invalid name detected when creating control for side '{side}' with base "
                            f"name '{base_control_name}' which was expected to match '{p}'")


def _expect_control_not_match_side(side: str, side_label: str, base_control_name: str, rs: RiggingSettings) -> None:
    if side_label:
        p = rs.sided_name_pattern.replace("{side}", side_label)
        if parse(p, base_control_name) or \
                parse(p.replace("_{seq}", ""), base_control_name) or \
                parse(p.replace("{seq}_", ""), base_control_name):
            raise Exception(f"Invalid name detected when creating control for side '{side}' with base "
                            f"name '{base_control_name}' which un-expectedly matched '{p}'")


def _set_override_colors_based_on_side(control_name: str, rs: RiggingSettings) -> None:
    side = None
    try:
        side = cmds.getAttr(f"{control_name}.rfJointSide")
    except:
        pass
    if side:
        child_shapes = cmds.listRelatives(control_name, type="nurbsCurve")
        if child_shapes:
            for child in child_shapes:
                if "center" == side:
                    _set_override_color_attributes(child, rs.center_side_color)
                elif "left" == side:
                    _set_override_color_attributes(child, rs.left_side_color)
                elif "right" == side:
                    _set_override_color_attributes(child, rs.right_side_color)
                else:
                    # noinspection DuplicatedCode
                    _set_override_color_attributes(child, rs.none_side_color)


# noinspection PyTypeChecker
def _set_override_color_attributes(object_name: str, color: tuple[float, float, float]):
    if color:
        cmds.setAttr(f"{object_name}.overrideEnabled", True)
        cmds.setAttr(f"{object_name}.overrideRGBColors", True)
        cmds.setAttr(f"{object_name}.overrideColorR", color[0])
        cmds.setAttr(f"{object_name}.overrideColorG", color[1])
        cmds.setAttr(f"{object_name}.overrideColorB", color[2])


def _scale_constraint(driven_name: str, driver_name: str):
    cmds.scaleConstraint(driver_name,
                         driven_name,
                         name=f"{driven_name}_scaleConstraint_{driver_name}")


def _parent_constraint(driven_name: str, driver_name: str, maintain_offset: bool = False):
    cmds.parentConstraint(driver_name,
                          driven_name,
                          maintainOffset=maintain_offset,
                          name=f"{driver_name}_parentConstraint_{driven_name}")


def _safe_parent(label: str, child_name: str, parent_name: str, rs: RiggingSettings):
    """Parent child to parent with additional checks to verify success and add debug logging."""
    if rs.debug_logging:
        print(f"Parenting {label} '{child_name}' to '{parent_name}'")
    parented = cmds.parent(child_name, parent_name)
    if 0 == len(parented):
        raise Exception(f"Failed to parent '{child_name}' under '{parent_name}'")


def _create_group(label: str, group_name: str, parent_object_name: Optional[str], rs: RiggingSettings) -> None:
    """
    Create a group under a parent object.
    The group ensures all the transforms are locked and hidden from channel box.

    :param label: the human-readable name used to describe the group
    :param group_name: the name used to create group.
    :param parent_object_name: the object that this group will be "logically parented under" if specified
    :param rs:the RiggingSettings
    """
    if rs.debug_logging:
        print(f"Creating {label} '{group_name}' with parent '{parent_object_name}'")
    util.ensure_single_object_named(None, parent_object_name)
    actual_object_name = cmds.group(name=group_name, empty=True)
    util.ensure_created_object_name_matches(label, actual_object_name, group_name)
    if parent_object_name:
        cmds.matchTransform(group_name, parent_object_name)
    _set_selection_child_highlighting(group_name, rs)

    if rs.use_control_hierarchy and parent_object_name:
        _safe_parent(label, group_name, parent_object_name, rs)
    else:
        # Place the group under one of the administrative groups if enabled
        if rs.controls_group:
            _safe_parent(label, group_name, rs.controls_group, rs)
        elif rs.root_group:
            _safe_parent(label, group_name, rs.root_group, rs)

        # If there is a "logical" parent then add constraints so that the group behaves as
        # if it was in a direct hierarchy
        if parent_object_name:
            _parent_constraint(group_name, parent_object_name, True)
            _scale_constraint(group_name, parent_object_name)

    _lock_and_hide_transform_properties(group_name)
    cmds.select(clear=True)


def _create_control(base_name: str, rs: RiggingSettings) -> str:
    """
    Create a control with the specified base name.
    It is expected that the offset group has already been created. The control will be moved to the offset group

    :param base_name: the base name.
    :param rs: the RiggingSettings.
    :return: the name of the control.
    """
    control_name = rs.derive_control_name(base_name)
    offset_group_name = rs.derive_offset_group_name(base_name)
    if rs.debug_logging:
        print(f"Creating control '{control_name}' in offset group '{offset_group_name}'")
    util.ensure_single_object_named(None, offset_group_name)

    # TODO: In the future we should support all sorts of control types (copy from catalog?) and
    #  scaling based on bone size and all sorts of options. For now we go with random control shape
    actual_control_name = cmds.circle(name=control_name, normalX=1, normalY=0, normalZ=0, radius=1)[0]
    util.ensure_created_object_name_matches("offset group", actual_control_name, control_name)
    _set_selection_child_highlighting(control_name, rs)

    cmds.matchTransform(control_name, offset_group_name)
    cmds.select(clear=True)

    # TODO: At some point we may decide to filter which controls go into the control set
    if rs.use_control_set:
        # Add  control to the control set if configured
        cmds.sets(control_name, edit=True, forceElement=rs.control_set)

    return control_name


def _setup_top_level_infrastructure(rs: RiggingSettings) -> None:
    """Create the groups, sets, layers etc required to organize our rig."""
    _create_top_level_group(rs)
    _create_controls_group(rs)
    _create_control_sets_if_required(rs)


def _create_top_level_group(rs: RiggingSettings) -> None:
    """Create a group in which to place our rig and related infrastructure."""
    if rs.root_group:
        root_groups = cmds.ls(rs.root_group, exactType="transform")
        if 0 == len(root_groups):
            if rs.debug_logging:
                print(f"Creating root group '{rs.root_group}'")
        elif 1 == len(root_groups):
            if rs.debug_logging:
                print(f"Re-creating root group '{rs.root_group}'")
            cmds.delete(rs.root_group)
        else:
            raise Exception(f"Root group '{rs.root_group}' already has multiple instances. Aborting!")

        actual_root_group_name = cmds.group(name=rs.root_group, empty=True)
        util.ensure_created_object_name_matches("root group", actual_root_group_name, rs.root_group)
        _lock_and_hide_transform_properties(actual_root_group_name)
        _set_selection_child_highlighting(rs.root_group, rs)

        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)
        if rs.debug_logging:
            print(f"Created root group '{rs.root_group}'")


def _create_controls_group(rs: RiggingSettings) -> None:
    """
    Create a group to contain all the controls.
    This is organisational and particularly useful if controls use constraints rather than a hierarchy.
    """
    if rs.controls_group:
        actual_controls_group_name = cmds.group(name=rs.controls_group, empty=True)
        util.ensure_created_object_name_matches("controls group", actual_controls_group_name, rs.controls_group)
        _set_selection_child_highlighting(rs.controls_group, rs)
        _lock_and_hide_transform_properties(actual_controls_group_name)
        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)
        if rs.root_group:
            _safe_parent("controls group", rs.controls_group, rs.root_group, rs)

            # Clear selection to avoid unintended selection dependent behaviour
            cmds.select(clear=True)


def _create_control_sets_if_required(rs: RiggingSettings) -> None:
    """
      Create the set containing the controls if rigging settings enables this feature.
      The set is intended to make it easier for animators to locate all the controls without trawling the hierarchy.
    """
    if rs.use_control_set:
        control_sets = cmds.ls(rs.control_set, exactType="objectSet")
        if 0 == len(control_sets):
            if rs.debug_logging:
                print(f"Creating controls set '{rs.root_group}'")
        elif 1 == len(control_sets):
            if rs.debug_logging:
                print(f"Re-creating control set '{rs.root_group}'")
            cmds.delete(rs.control_set)
        else:
            raise Exception(f"Control set '{rs.control_set}' already has multiple instances. Aborting!")

        # TODO: In the future we may want to support multiple (potentially overlapping) control sets.

        cmds.sets(name=rs.control_set, empty=True)

        if rs.debug_logging:
            print(f"Created control set '{rs.control_set}'")
