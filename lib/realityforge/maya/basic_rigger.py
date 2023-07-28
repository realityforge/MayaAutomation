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
import math
import re
from typing import Optional

import maya.api.OpenMaya as om
import maya.cmds as cmds
from parse import parse

from realityforge.maya import util as util


# Feature List:
#  * Optional: controllers tagged as controllers so can pick walk between controllers correctly. Also improves
#    runtime performance ... due to GPU something something
#  * Optional "visible on proximity" setting
#  * Optional separate driver hierarchy. Makes exports clean and allows multiple mesh/skeleton combos to be
#    driven from one rig.
#  * Optional direct control hierarchy for performance or indirect hierarchy so that selecting one control
#    does not highlight tree of controllers. Alternatively "selection_child_highlighting" to allow individual
#    controllers highlighting be an editor setting
#  * Coloring by side
#  * Coloring by arbitrary matching on controllers names
#  * Name patterns for different elements and for extracting sides from joints
#  * Lock and hide parameters that should not be touched by animator. (improves performance and lowers number
#    of curves in animation)


# TODO: Add groups of controls that can be hidden from root control

# TODO: Hide all the channels on driver chain? (No locking except if equivalent control has locked? but all hidden)

# TODO: Add option to not create the direct connections between the driver skeleton and the exportable skeleton.
#  This allows you to reference an existing skeleton into a rig file, generate a rig, de-reference skeleton file
#  then go to separate scene, reference in the rig and direct connect it to local skeleton. So same rig can be used
#  for multiple actors with same skeleton

# TODO: Add "Side" to ControllerConfig and then add "default" rules to set the left, right, center none colors and
#   remove the left_side_color, right_side_color, center_side_color, none_side_color config

# TODO: Add "default" ControllerConfig at specific priority level. These are generated unless a boolean flag is
#  passed to skip them. These will apply rules that are probably generic all over such as:
#  * color patterns as defined above
#  * global has visibility_mode="default"
#  * global/world_offset/cog controls should be allowed translate/rotate
#  * ik handles allowed translate/rotate
#  * settings allowed none

# TODO: Perhaps add ability to generate other defaults. i.e. Humanoid defaults would allow hips translate but
#       the rest are rotate?

# TODO: Add display layers for groups of controls starting at a root. (so could have layer for LH or RH). Maybe
#  remove visibility switch from controls? or support both?). See Azri rig for example

# TODO: Pole vector controls only care about translation so lock and hide scale and then add a constraint so that
#  the pole vector control aims at the knee/elbow/whatevs and then hide

# TODO: Rename global in code back to "world"

# TODO: Color "cog", "world", "world offset" differently from each other and different from center line so easy for
#  animator to read

# TODO: Lock and hide "visibility" channels on all controls  or at least hide (but may not lock as could be
#  controlled by other elements). This is to avoid them being "animated"

# TODO: Default elbow to only animate in one rotate channel for "realistic" animation but sometimes animator wants
#  to break this rule.

# TODO: Some rigs allow scale on primary axis for arms/fingers (i.e. X)

# TODO: Features to add:
# * a "set" that includes the joints to export as a skeleton
# * a "set" that includes the joints and mesh to export as a skeletal mesh

# TODO: Support ik chains that are "single chain". These have no pole vector
# TODO: Verify IK chains that are not single chain are at least 3 long? (for working out pole vector?)

# TODO: Have some way to create reverse feet setup. i.e. SC IK for ankle to ball and ball to toe

# Rotation on Peel_Heel_GRP will move foot correctly
# peelHeel attribute then rotates an axis in "peel_heel_GRP". This can be done using set driven
#       keys or maths and direct connection nodes in node editor. 0 = foot resting on ground,
#       10 = max rotation before have to lift ball

# - foot_OFF_GRP (matched to ball)
#   - foot_CTRL
#     # Extra Attribute "peelHeel" float range 0-10 that is in channelBox
#     - Peel_Heel_Fix_GRP (Matched to ball joint)
#       - Peel_Heel_GRP (Matched to ball joint)
#         - Leg_ik_handle (ankle joint positioned, keeps relative offset)
#     - toe_ik_handles_GRP
#       - ball_ik_handle
#       - toe_ik_handle


# TODO: Generate certain controls in world orientation rather than joint orientation (i.e. head, eye, global,
#  cog, IK handle for foot (and hand?) should be world, head, eye should be world). It is unclear whether it
#  should just be the control that is in world or whether the joint should also be in world. AntCGI says joint
#  and control, others use just control byt sometimes that causes flipping. A lot of these choices are to make
#  animators lives easier (foot orientation should match world to make it easier for the animator to create walk
#  animation or game engineer to do foot planting)

# TODO: Add verification that joints are oriented with primary axis down bone unless allow listed to not be that way

# TODO: Add option for primary axis (i.e. down the bone) be y as that is less likely to cause gimbal lock (at least
#  for humanoid like skeletons with normal animations). So Y primary axis and z forward. However then you typically
#  need to change rotation order with y first (i.e. yxz or yzx). Of course this should not be done on bones that are
#  in world coordinates

class IkChain:
    def __init__(self, name: str,
                 joints: list[str],
                 end_name: Optional[str] = None,
                 pole_vector_distance: float = 10):
        self.name = name
        self.joints = joints
        self.end_name = end_name if end_name else f"{name}_end"
        self.pole_vector_distance = pole_vector_distance

    def __str__(self):
        return f"IkChain[{self.name}]"

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


class ControllerConfig:
    def __init__(self,
                 name_pattern: str,
                 priority: int = 10,
                 visibility_mode: Optional[str] = None,
                 control_template: Optional[str] = None,
                 control_set: Optional[str] = None,
                 control_scale: Optional[float] = None,
                 color: Optional[tuple[float, float, float]] = None,
                 translate_x: Optional[bool] = None,
                 translate_y: Optional[bool] = None,
                 translate_z: Optional[bool] = None,
                 rotate_x: Optional[bool] = None,
                 rotate_y: Optional[bool] = None,
                 rotate_z: Optional[bool] = None,
                 scale_x: Optional[bool] = None,
                 scale_y: Optional[bool] = None,
                 scale_z: Optional[bool] = None):
        self.name_pattern = name_pattern
        self.priority = priority
        self.visibility_mode = visibility_mode
        self.control_template = control_template
        self.control_set = control_set
        self.control_scale = control_scale
        self.color = color
        self.translate_x = translate_x
        self.translate_y = translate_y
        self.translate_z = translate_z
        self.rotate_x = rotate_x
        self.rotate_y = rotate_y
        self.rotate_z = rotate_z
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.scale_z = scale_z

    def any_translate_axis_control_overrides(self) -> bool:
        return self.translate_x is not None and self.translate_y is not None and self.translate_z is not None

    def any_rotate_axis_control_overrides(self) -> bool:
        return self.rotate_x is not None and self.rotate_y is not None and self.rotate_z is not None

    def any_scale_axis_control_overrides(self) -> bool:
        return self.scale_x is not None and self.scale_y is not None and self.scale_z is not None

    def __str__(self):
        return f"ControllerConfig[name={self.name_pattern}]"


class RiggingSettings:
    def __init__(self,
                 root_group_name: Optional[str] = "rig",
                 controls_group: Optional[str] = "controls_GRP",
                 driver_skeleton_group: Optional[str] = "driver_skeleton_GRP",
                 control_configurations: list[ControllerConfig] = None,
                 use_driver_hierarchy: bool = True,
                 use_control_hierarchy: bool = False,
                 use_control_set: bool = True,
                 tag_controls: bool = True,
                 generate_world_offset_control: bool = True,
                 generate_cog_control: bool = True,
                 driven_joint_name_pattern: str = "{name}_JNT",
                 driver_joint_name_pattern: str = "{name}_JDRV",
                 ik_end_name_pattern: str = "{name}_GRP",
                 ik_system_name_pattern: str = "{name}_IK_SYS",
                 ik_handle_name_pattern: str = "{name}_IK_handle",
                 pole_vector_base_name_pattern: str = "{name}_PV",
                 ik_switch_base_name_pattern: str = "{name}_settings",
                 ik_joint_base_name_pattern: str = "{name}_{chain}_IK",
                 fk_joint_base_name_pattern: str = "{name}_{chain}_FK",
                 offset_group_name_pattern: str = "{name}_OFF_GRP",
                 control_name_pattern: str = "{name}_CTRL",
                 sided_name_pattern: str = "{name}_{side}_{seq}",
                 global_base_control_name: str = "global",
                 world_offset_base_control_name: str = "world_offset",
                 cog_base_control_name: str = "cog",

                 # A list of joints that will abort further processing
                 stop_joints: Optional[list[str]] = None,

                 # This is the strategy for discovering the location of the cog in the rig. Of course this is only
                 # used if generate_cog_control is True. Possible strategy values include:
                 # - "root" - use transform of the root joint
                 # - "child_average" - derive position from the average of child bones.
                 # - Any other non-None value is the name of the locator to get the position from.
                 cog_location_strategy: str = "child_average",
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
        self.root_group_name = root_group_name
        self.controls_group = controls_group
        self.driver_skeleton_group = driver_skeleton_group
        if control_configurations:
            self.control_configurations = sorted(control_configurations, key=lambda x: x.priority)
        else:
            self.control_configurations = []
        self.use_driver_hierarchy = use_driver_hierarchy
        self.use_control_hierarchy = use_control_hierarchy
        self.use_control_set = use_control_set
        self.tag_controls = tag_controls
        self.generate_world_offset_control = generate_world_offset_control
        self.generate_cog_control = generate_cog_control
        self.driven_joint_name_pattern = driven_joint_name_pattern
        self.driver_joint_name_pattern = driver_joint_name_pattern
        self.ik_end_name_pattern = ik_end_name_pattern
        self.ik_system_name_pattern = ik_system_name_pattern
        self.ik_handle_name_pattern = ik_handle_name_pattern
        self.pole_vector_base_name_pattern = pole_vector_base_name_pattern
        self.ik_switch_base_name_pattern = ik_switch_base_name_pattern
        self.ik_joint_base_name_pattern = ik_joint_base_name_pattern
        self.fk_joint_base_name_pattern = fk_joint_base_name_pattern
        self.offset_group_name_pattern = offset_group_name_pattern
        self.control_name_pattern = control_name_pattern
        self.sided_name_pattern = sided_name_pattern
        self.global_base_control_name = global_base_control_name
        self.world_offset_base_control_name = world_offset_base_control_name
        self.cog_base_control_name = cog_base_control_name
        self.stop_joints = stop_joints if stop_joints else []
        self.selection_child_highlighting = selection_child_highlighting
        self.debug_logging = debug_logging
        self.cog_location_strategy = cog_location_strategy
        self.ik_chains = ik_chains if ik_chains else []
        self.left_side_color = left_side_color
        self.right_side_color = right_side_color
        self.center_side_color = center_side_color
        self.none_side_color = none_side_color
        self.left_side_name = left_side_name
        self.right_side_name = right_side_name
        self.center_side_name = center_side_name
        self.none_side_name = none_side_name

    def find_matching_control_config(self, controller_name: str) -> list[ControllerConfig]:
        configs = [x for x in self.control_configurations if re.search(x.name_pattern, controller_name)]
        return sorted(configs, key=lambda v: v.priority)

    # Return the name of the control the positions the character. This is either the world offset control or the
    def derive_character_offset_control_name(self) -> str:
        if self.generate_world_offset_control:
            return self.derive_control_name(self.world_offset_base_control_name)
        else:
            return self.derive_control_name(self.global_base_control_name)

    def derive_ik_handle_name(self, chain_name: str) -> str:
        return self.ik_handle_name_pattern.format(name=chain_name)

    def derive_pole_vector_base_name(self, chain_name: str) -> str:
        return self.pole_vector_base_name_pattern.format(name=chain_name)

    # Return attribute that is 1 when in FK mode
    def derive_fk_enabled_attribute_name(self, chain_name: str) -> str:
        return self.derive_ik_switch_attribute_name(chain_name)

    # Return attribute that is 1 when in IK mode
    def derive_ik_enabled_attribute_name(self, chain_name: str) -> str:
        return f"{self.derive_ik_switch_reverse_name(chain_name)}.outputX"

    def derive_ik_switch_attribute_name(self, chain_name: str) -> str:
        return f"{self.derive_ik_switch_name(chain_name)}.rfIkFkBlend"

    def derive_ik_switch_reverse_name(self, chain_name: str) -> str:
        return f"{self.derive_ik_switch_base_name(chain_name)}_rfIkFkBlend_reverse"

    def derive_ik_switch_base_name(self, chain_name: str) -> str:
        return self.ik_switch_base_name_pattern.format(name=chain_name)

    def derive_ik_switch_name(self, chain_name: str) -> str:
        return self.derive_control_name(self.derive_ik_switch_base_name(chain_name))

    def derive_control_name(self, base_name: str) -> str:
        return self.control_name_pattern.format(name=base_name)

    def derive_offset_group_name(self, base_name: str) -> str:
        return self.offset_group_name_pattern.format(name=base_name)

    def derive_ik_end_name(self, ik_chain: IkChain) -> str:
        return self.ik_end_name_pattern.format(name=ik_chain.end_name, chain=ik_chain.name)

    def derive_ik_system_name(self, ik_chain: IkChain) -> str:
        return self.ik_system_name_pattern.format(name=ik_chain.name)

    def derive_target_joint_name(self, base_name: str) -> str:
        return self.get_target_joint_pattern().format(name=base_name)

    def derive_driven_joint_name(self, base_name: str) -> str:
        return self.driven_joint_name_pattern.format(name=base_name)

    def derive_driver_joint_name(self, base_name: str) -> str:
        return self.driver_joint_name_pattern.format(name=base_name)

    def derive_source_joint_name(self, base_name: str) -> str:
        return self.driven_joint_name_pattern.format(name=base_name)

    def extract_source_joint_base_name(self, joint_name: str) -> str:
        result = parse(self.driven_joint_name_pattern, joint_name)
        if not result:
            raise Exception(f"Joint named '{joint_name}' does not match expected pattern "
                            f"'{self.driven_joint_name_pattern}'. Aborting!")
        return result.named["name"]

    def extract_control_base_name(self, name: str) -> str:
        result = parse(self.control_name_pattern, name)
        if not result:
            raise Exception(f"Control named '{name}' does not match expected pattern "
                            f"'{self.control_name_pattern}'. Aborting!")
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


def _hide_transform_properties(object_name: str) -> None:
    """Lock and remove from the channelbox the attributes of the specified transform object.

    :param object_name: the name of the transform object.
    """
    for attr in ["translate", "rotate", "scale"]:
        for axis in ["X", "Y", "Z"]:
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=False)
            cmds.setAttr(f"{object_name}.{attr}{axis}", keyable=False, channelBox=False)
    cmds.setAttr(f"{object_name}.visibility", keyable=False, channelBox=False)


def _lock_and_hide_transform_properties(object_name: str) -> None:
    """Lock and remove from the channelbox the attributes of the specified transform object.

    :param object_name: the name of the transform object.
    """
    for attr in ["translate", "rotate", "scale"]:
        for axis in ["X", "Y", "Z"]:
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=False)
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=True, keyable=False, channelBox=False)
    cmds.setAttr(f"{object_name}.visibility", lock=True, keyable=False, channelBox=False)


def _unlock_transform_properties(object_name: str) -> None:
    """UnLock the attributes of the specified transform object.

    :param object_name: the name of the transform object.
    """
    for attr in ["translate", "rotate", "scale"]:
        for axis in ["X", "Y", "Z"]:
            cmds.setAttr(f"{object_name}.{attr}{axis}", lock=False)
    cmds.setAttr(f"{object_name}.visibility", lock=False)


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

    duplicate_object_name = cmds.duplicate(source_control_name,
                                           name=f"{target_control_name}_tmp",
                                           renameChildren=True,
                                           returnRootsOnly=True)[0]
    # Delete all children that are no nurbs curves as they are probably child offset groups
    # and will cause duplicate name errors in subsequent unlock call
    children = cmds.listRelatives(duplicate_object_name)
    if children:
        for child in children:
            if "nurbsCurve" != cmds.objectType(child):
                cmds.delete(child)
    util.unlock_all_attributes(duplicate_object_name)

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
            # noinspection PyTypeChecker
            cmds.setAttr(f"{duplicate_object_name}.scaleX", -1)
            # noinspection PyTypeChecker
            cmds.setAttr(f"{duplicate_object_name}.scaleY", -1)
            # noinspection PyTypeChecker
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
            if 1 == len(source_children):
                cmds.rename(child, f"{target_control_name}Shape")
            else:
                cmds.rename(child, f"{target_control_name}Shape{index}")

    cmds.delete(duplicate_object_name)
    if rs.root_group_name:
        util.delete_history(rs.root_group_name)

    _set_override_colors(target_control_name, rs)

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)


def create_rig(root_joint_name: str,
               rigging_settings: RiggingSettings = RiggingSettings(),
               validate_only: bool = False) -> None:
    if rigging_settings.debug_logging:
        print(f"Creating rig with root joint '{root_joint_name}'")

    print(f"Validating skeleton with root joint '{root_joint_name}' is ready for rigging.")
    # Check the ik chains are valid
    _validate_ik_chains(rigging_settings)

    # TODO: Verify that root control is zero unless generate_cog is null cog_location_strategy is not root
    # TODO: Suggest that root bone has base name of root?

    if validate_only:
        print(f"Validation performed. Exiting early as requested.")
        return

    _setup_top_level_infrastructure(rigging_settings)
    _process_joint(rigging_settings, root_joint_name, True)
    if rigging_settings.root_group_name:
        util.delete_history(rigging_settings.root_group_name)

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

            if terminal_joint_index != index:
                # If we are an internal joint in an ik chain then make sure we have preferredAngle specified
                p = f'{current_joint_name}.preferredAngle'
                if 0 == cmds.getAttr(f'{p}X') and 0 == cmds.getAttr(f'{p}Y') and 0 == cmds.getAttr(f'{p}Z'):
                    raise Exception(f"Ik chain named '{chain.name}' has an internal joint named '{current_joint_name}'"
                                    f" that has not specified a non-zero preferredAngle.")
            for attr in ["rotateAxis", "rotate"]:
                for axis in ["X", "Y", "Z"]:
                    attr_name = f'{current_joint_name}.{attr}{axis}'
                    attr_value = cmds.getAttr(attr_name)
                    if 0 != attr_value:
                        raise Exception(f"Ik chain named '{chain.name}' has a joint named '{current_joint_name}'"
                                        f" that has a non-zero value for {attr_name}. Actual value: {attr_value}")
            for attr in ["scale"]:
                for axis in ["X", "Y", "Z"]:
                    attr_name = f'{current_joint_name}.{attr}{axis}'
                    attr_value = cmds.getAttr(attr_name)
                    if not math.isclose(1., attr_value, rel_tol=1e-6):
                        raise Exception(f"Ik chain named '{chain.name}' has a joint named '{current_joint_name}'"
                                        f" that has a non-one value for {attr_name}. Actual value: {attr_value}")

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


def _find_object_to_match_for_cog(root_joint_name: str, rs: RiggingSettings) -> Optional[str]:
    print(f"Finding cog position for root bone '{root_joint_name}' via strategy {rs.cog_location_strategy}")
    if "child_average" == rs.cog_location_strategy:
        x = 0.0
        y = 0.0
        z = 0.0
        object_count = 0.0
        child_joints = cmds.listRelatives(root_joint_name, type="joint")
        if child_joints:
            for child_joint in child_joints:
                # noinspection PyArgumentList
                translation = cmds.xform(child_joint, query=True, worldSpace=True, translation=True)
                # noinspection PyUnresolvedReferences
                x += translation[0]
                # noinspection PyUnresolvedReferences
                y += translation[1]
                # noinspection PyUnresolvedReferences
                z += translation[2]
                object_count += 1
        if 0 == object_count:
            return None
        else:
            final_x = x / object_count
            final_y = y / object_count
            final_z = z / object_count
            translation = (final_x, final_y, final_z)
            locator_name = cmds.spaceLocator(absolute=True, position=translation)[0]
            cmds.xform(locator_name, worldSpace=True, translation=translation)
            return locator_name
    elif "root" == rs.cog_location_strategy:
        return root_joint_name
    else:
        return rs.cog_location_strategy


def _process_joint(rs: RiggingSettings,
                   joint_name: str,
                   is_root: bool,
                   parent_joint_name: Optional[str] = None,
                   parent_control_name: Optional[str] = None,
                   ik_chain: Optional[IkChain] = None) -> None:
    if rs.debug_logging:
        print(f"Attempting to process joint '{joint_name}' with parent joint named '{parent_joint_name}', "
              f"parent control named '{parent_control_name}' and ik chain {ik_chain}")

    # Ensure there is a single joint of expected name
    util.ensure_single_object_named("joint", joint_name)

    # Ensure there is a single parent joint of expected name
    if parent_joint_name:
        util.ensure_single_object_named("joint", parent_joint_name)

    # Derive the base name
    base_name = rs.extract_source_joint_base_name(joint_name)

    if base_name in rs.stop_joints:
        print(f"Stopping rig creation at joint '{joint_name}' as it appears in stop_joints list.")
        return

    # Derive the base parent name
    base_parent_name = rs.extract_source_joint_base_name(parent_joint_name) if parent_joint_name else None

    # Set up the driver joint chain
    if rs.use_driver_hierarchy:
        _create_driver_joint(joint_name, base_name, base_parent_name, rs)

    control_name = None
    joint_constraining_control_name = None
    if is_root:
        if rs.generate_world_offset_control:
            control_name = _setup_control(rs.global_base_control_name, None, joint_name, rs)
            control_name = _setup_control(rs.world_offset_base_control_name, control_name, joint_name, rs)
            _maybe_lock_and_hide_controller_transform_attributes(control_name,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True)
        else:
            control_name = _setup_control(rs.global_base_control_name, None, joint_name, rs)
        joint_constraining_control_name = control_name
        if rs.generate_cog_control:
            cog_locator = _find_object_to_match_for_cog(joint_name, rs)
            control_name = _setup_control(rs.cog_base_control_name, control_name, cog_locator, rs)
            _maybe_lock_and_hide_controller_transform_attributes(control_name,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True)
            if "child_average" == rs.cog_location_strategy:
                cmds.delete(cog_locator)
    elif not ik_chain:
        joint_constraining_control_name = control_name = _setup_control(base_name, parent_control_name, joint_name, rs)

    if not ik_chain:
        control_configs = rs.find_matching_control_config(control_name)

        driver_joint_name = rs.derive_driver_joint_name(base_name) if rs.use_driver_hierarchy else joint_name

        # Setup constraints on axis that should be constrained as defined in configuration
        _maybe_create_point_constraint(control_configs, driver_joint_name, joint_constraining_control_name, rs)
        _maybe_create_orient_constraint(control_configs, driver_joint_name, joint_constraining_control_name, rs)
        _maybe_create_scale_constraint(control_configs, driver_joint_name, joint_constraining_control_name, rs)

        if rs.use_driver_hierarchy:
            _connect_transform_attributes(driver_joint_name, joint_name)

    at_chain_start = False
    at_chain_end = False
    in_chain_middle = False

    if ik_chain:
        chain_starts_at_current_joint = ik_chain.does_chain_start_at_joint(base_name)
        if chain_starts_at_current_joint:
            character_offset_control = rs.derive_character_offset_control_name()

            # Create a group for all the controls that are past the end off the ik chain and also
            # contains the IK/FK switch control
            ik_end_name = rs.derive_ik_end_name(ik_chain)
            _create_group("ik end group", ik_end_name, character_offset_control, rs)
            _parent_group("ik end group", ik_end_name, character_offset_control, rs)
            effector_end_ik_joint_name = rs.derive_driven_joint_name(ik_chain.joints[-1])
            cmds.matchTransform(ik_end_name, effector_end_ik_joint_name)

            # Create a group to contain the Ik Handle and the controls for the PoleVector and IkHandle
            ik_system_name = rs.derive_ik_system_name(ik_chain)
            _create_group("ik system group", ik_system_name, character_offset_control, rs)
            _parent_group("ik system group", ik_system_name, character_offset_control, rs)
            at_chain_start = True

            # Create Ik/FK switch
            ik_switch_base_name = rs.derive_ik_switch_base_name(ik_chain.name)
            ik_switch_name = _setup_control(ik_switch_base_name,
                                            ik_end_name,
                                            effector_end_ik_joint_name,
                                            rs,
                                            use_config_to_manage_control_channels=False)
            _lock_and_hide_transform_properties(ik_switch_name)
            cmds.addAttr(ik_switch_name,
                         longName="rfIkFkBlend",
                         niceName="Ik Fk Blend",
                         maxValue=1,
                         minValue=0,
                         defaultValue=1)
            cmds.setAttr(f"{ik_switch_name}.rfIkFkBlend", channelBox=True, keyable=True)

            # Create a reverse node so that it is inverse of ik switch
            reverse_name = rs.derive_ik_switch_reverse_name(ik_chain.name)
            actual_reverse_name = cmds.shadingNode("reverse", asUtility=True, name=reverse_name)
            util.ensure_created_object_name_matches("ik fk reverse", actual_reverse_name, reverse_name)

            cmds.connectAttr(f"{ik_switch_name}.rfIkFkBlend", f"{reverse_name}.inputX", lock=True, force=True)

        # Create IK/FK controls and support joints

        fk_joint_base_name = rs.derive_fk_joint_base_name(base_name, ik_chain.name)
        ik_parent_joint_name = None
        fk_parent_joint_name = None
        if base_parent_name:
            if at_chain_start:
                ik_parent_joint_name = rs.derive_target_joint_name(base_parent_name)
                fk_parent_joint_name = rs.derive_target_joint_name(base_parent_name)
            else:
                ik_parent_joint_name = rs.derive_ik_joint_name(base_parent_name, ik_chain.name)
                fk_parent_joint_name = rs.derive_fk_joint_name(base_parent_name, ik_chain.name)

        ik_joint_name = rs.derive_ik_joint_name(base_name, ik_chain.name)
        fk_joint_name = rs.derive_fk_joint_name(base_name, ik_chain.name)

        _create_joint_from_template(joint_name, "ik joint", ik_joint_name, ik_parent_joint_name, rs)
        _create_joint_from_template(joint_name, "fk joint", fk_joint_name, fk_parent_joint_name, rs)

        if chain_starts_at_current_joint:
            # Hide the IK/FK chains so that we only see the driven chain
            # noinspection PyTypeChecker
            cmds.setAttr(f"{ik_joint_name}.visibility", 0, lock=True)
            # noinspection PyTypeChecker
            cmds.setAttr(f"{fk_joint_name}.visibility", 0, lock=True)

        target_joint_name = rs.derive_target_joint_name(base_name)

        # Create a parent constraint that attempts to use FK and IK hierarchies to drive target joint (either driver
        # or original joint depending on whether the use_driver_hierarchy flag is enabled)
        ik_fk_parent_constraint_name = _ik_fk_parent_constraint(target_joint_name, ik_joint_name, fk_joint_name, rs)
        ik_fk_scale_constraint_name = _ik_fk_scale_constraint(target_joint_name, ik_joint_name, fk_joint_name, rs)

        cmds.setAttr(f"{ik_fk_parent_constraint_name}.w0", lock=False)
        ik_enabled_attribute_name = rs.derive_ik_enabled_attribute_name(ik_chain.name)
        fk_enabled_attribute_name = rs.derive_fk_enabled_attribute_name(ik_chain.name)
        cmds.connectAttr(ik_enabled_attribute_name, f"{ik_fk_parent_constraint_name}.w0", lock=True, force=True)
        cmds.connectAttr(fk_enabled_attribute_name, f"{ik_fk_parent_constraint_name}.w1", lock=True, force=True)

        cmds.setAttr(f"{ik_fk_scale_constraint_name}.w0", lock=False)
        cmds.connectAttr(ik_enabled_attribute_name, f"{ik_fk_scale_constraint_name}.w0", lock=True, force=True)
        cmds.connectAttr(fk_enabled_attribute_name, f"{ik_fk_scale_constraint_name}.w1", lock=True, force=True)

        if chain_starts_at_current_joint:
            fk_joint_control_name = _setup_control(fk_joint_base_name,
                                                   parent_control_name,
                                                   joint_name,
                                                   rs,
                                                   leave_visibility_unlocked=True)
        else:
            fk_joint_control_name = _setup_control(fk_joint_base_name,
                                                   fk_parent_joint_name,
                                                   joint_name,
                                                   rs,
                                                   leave_visibility_unlocked=True)

        cmds.connectAttr(fk_enabled_attribute_name, f"{fk_joint_control_name}.visibility", lock=True, force=True)

        # Ensure that the FK controls constrain the fk joints
        control_configs = rs.find_matching_control_config(fk_joint_control_name)
        _maybe_create_point_constraint(control_configs, fk_joint_name, fk_joint_control_name, rs)
        _maybe_create_orient_constraint(control_configs, fk_joint_name, fk_joint_control_name, rs)
        _maybe_create_scale_constraint(control_configs, fk_joint_name, fk_joint_control_name, rs)

        if ik_chain.does_chain_end_at_joint(base_name):
            ik_system_name = rs.derive_ik_system_name(ik_chain)
            ik_handle_name = rs.derive_ik_handle_name(ik_chain.name)
            pole_vector_base_name = rs.derive_pole_vector_base_name(ik_chain.name)

            # Create ik handle
            ik_start_joint = rs.derive_ik_joint_name(ik_chain.joints[0], ik_chain.name)
            actual_ik_handle_name, _ = cmds.ikHandle(name=ik_handle_name,
                                                     solver="ikRPsolver",
                                                     startJoint=ik_start_joint,
                                                     endEffector=ik_joint_name)
            util.ensure_created_object_name_matches("ik handle", actual_ik_handle_name, ik_handle_name)
            # Ik handle is always hidden as it is driven by a separate control
            # noinspection PyTypeChecker
            cmds.setAttr(f"{ik_handle_name}.visibility", 0, lock=True)
            _safe_parent("ik handle", ik_handle_name, ik_system_name, rs)
            # Lock scale/rotate on handle as they do not do anything
            _maybe_lock_and_hide_controller_transform_attributes(ik_handle_name,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 False)

            # This sets up the control but locates it at the end of the ik-chain
            # We need to unlock the offset group and move it to where the pole-vector should be
            pole_vector_name = _setup_control(pole_vector_base_name,
                                              ik_system_name,
                                              joint_name,
                                              rs,
                                              use_config_to_manage_control_channels=False)
            cmds.connectAttr(ik_enabled_attribute_name, f"{pole_vector_name}.visibility", lock=True, force=True)
            # Translate is only modifiable constraint on pole vector control
            _maybe_lock_and_hide_controller_transform_attributes(pole_vector_name,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 False)

            pole_vector_offset_group_name = rs.derive_offset_group_name(pole_vector_base_name)
            _unlock_transform_properties(pole_vector_offset_group_name)

            ik_mid_joint_name = rs.derive_driven_joint_name(ik_chain.joints[1])

            # Use magical maths to find the plane on which pole control should lie

            # First find 3 points on plane
            # noinspection PyArgumentList
            ik_start_pos = cmds.xform(ik_start_joint, query=True, worldSpace=True, translation=True)
            # noinspection PyArgumentList
            ik_mid_pos = cmds.xform(ik_mid_joint_name, query=True, worldSpace=True, translation=True)
            # noinspection PyArgumentList
            ik_end_pos = cmds.xform(ik_joint_name, query=True, worldSpace=True, translation=True)

            # Convert positions into vectors
            # noinspection PyArgumentList
            ik_start_vec = om.MVector(*ik_start_pos)
            # noinspection PyArgumentList
            ik_mid_vec = om.MVector(*ik_mid_pos)
            # noinspection PyArgumentList
            ik_end_vec = om.MVector(*ik_end_pos)

            # Create vectors from start to each other point to define the plane
            ik_start_end_vec = ik_end_vec - ik_start_vec
            ik_start_mid_vec = ik_mid_vec - ik_start_vec

            # Calculate a unit vector from the pole back to handle
            dot_product = ik_start_mid_vec * ik_start_end_vec
            projection_vec = ik_start_end_vec.normal() * float(dot_product) / float(ik_start_end_vec.length())

            pole_vec = (ik_start_mid_vec - projection_vec) * ik_chain.pole_vector_distance
            pv_control_vec = pole_vec + ik_mid_vec
            cmds.xform(pole_vector_offset_group_name, worldSpace=True, translation=pv_control_vec)
            _hide_transform_properties(pole_vector_offset_group_name)

            # TODO: Add support to verify poleVector
            cmds.poleVectorConstraint(pole_vector_name, ik_handle_name)

            # Create ik handle control
            ik_handle_control_name = _setup_control(ik_handle_name,
                                                    ik_system_name,
                                                    joint_name,
                                                    rs,
                                                    use_config_to_manage_control_channels=False)
            cmds.connectAttr(ik_enabled_attribute_name, f"{ik_handle_control_name}.visibility", lock=True, force=True)
            # Lock and hide scale transform attributes on the ik handle control
            _maybe_lock_and_hide_controller_transform_attributes(ik_handle_control_name,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 True,
                                                                 True,
                                                                 True,
                                                                 False)

            # Ensure that the IK control constrains the ik end joint and end group
            _point_constraint(ik_handle_name, ik_handle_control_name, rs)
            _orient_constraint(ik_joint_name, ik_handle_control_name, rs)

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
                child_parent_control_name = rs.derive_ik_end_name(ik_chain)
                child_ik_chain = None
            elif in_chain_middle:
                if ik_chain.does_chain_contain_joint(child_base_joint_name):
                    child_ik_chain = ik_chain

            if not child_ik_chain:
                child_ik_chain = rs.get_ik_chain_starting_at_joint(child_base_joint_name)

            _process_joint(rs, child_joint_name, False, joint_name, child_parent_control_name, child_ik_chain)


def _maybe_create_point_constraint(control_configs: list[ControllerConfig],
                                   driven_object_name: str,
                                   driver_object_name: str,
                                   rs: RiggingSettings) -> None:
    """Create the point constraint using specified control configs.
    * If no control configs exist or none have specified rules around translation then add point constraint on all axis.
    * Take the first config that has specified rules around translations and create the constraint using the rules or
      skip constraint creation if the rule explicitly indicates no axis are constrained.

    :param control_configs: the configs that match the current control.
    :param driven_object_name: the object that is driven by constraint.
    :param driver_object_name: the object that drives the driven object through constraint.
    :param rs: the associated RiggingSettings
    """
    for control_config in control_configs:
        if control_config.any_translate_axis_control_overrides():
            include_x = control_config.translate_x is None or control_config.translate_x
            include_y = control_config.translate_y is None or control_config.translate_y
            include_z = control_config.translate_z is None or control_config.translate_z
            if include_x or include_y or include_z:
                _point_constraint(driven_object_name,
                                  driver_object_name,
                                  rs,
                                  include_x=include_x,
                                  include_y=include_y,
                                  include_z=include_z)
            return

    _point_constraint(driven_object_name, driver_object_name, rs)


def _maybe_create_orient_constraint(control_configs: list[ControllerConfig],
                                    driven_object_name: str,
                                    driver_object_name: str,
                                    rs: RiggingSettings) -> None:
    """Create the orient constraint using specified control configs.
    * If no control configs exist or none have specified rules around rotation then add orient constraint on all axis.
    * Take the first config that has specified rules around rotations and create the constraint using the rules or
      skip constraint creation if the rule explicitly indicates no axis are constrained.

    :param control_configs: the configs that match the current control.
    :param driven_object_name: the object that is driven by constraint.
    :param driver_object_name: the object that drives the driven object through constraint.
    :param rs: the associated RiggingSettings
    """
    for control_config in control_configs:
        if control_config.any_rotate_axis_control_overrides():
            include_x = control_config.rotate_x is None or control_config.rotate_x
            include_y = control_config.rotate_y is None or control_config.rotate_y
            include_z = control_config.rotate_z is None or control_config.rotate_z
            if include_x or include_y or include_z:
                _orient_constraint(driven_object_name,
                                   driver_object_name,
                                   rs,
                                   include_x=include_x,
                                   include_y=include_y,
                                   include_z=include_z)
            return

    _orient_constraint(driven_object_name, driver_object_name, rs)


def _maybe_create_scale_constraint(control_configs: list[ControllerConfig],
                                   driven_object_name: str,
                                   driver_object_name: str,
                                   rs: RiggingSettings) -> None:
    """Create the scale constraint using specified control configs.
    * If no control configs exist or none have specified rules around scale then add scale constraint on all axis.
    * Take the first config that has specified rules around scales and create the constraint using the rules or
      skip constraint creation if the rule explicitly indicates no axis are constrained.

    :param control_configs: the configs that match the current control.
    :param driven_object_name: the object that is driven by constraint.
    :param driver_object_name: the object that drives the driven object through constraint.
    :param rs: the associated RiggingSettings
    """
    for control_config in control_configs:
        if control_config.any_scale_axis_control_overrides():
            include_x = control_config.scale_x is None or control_config.scale_x
            include_y = control_config.scale_y is None or control_config.scale_y
            include_z = control_config.scale_z is None or control_config.scale_z
            if include_x or include_y or include_z:
                _scale_constraint(driven_object_name,
                                  driver_object_name,
                                  rs,
                                  include_x=include_x,
                                  include_y=include_y,
                                  include_z=include_z)
            return

    _scale_constraint(driven_object_name, driver_object_name, rs)


def _connect_transform_attributes(driver_object_name: str, driven_object_name: str) -> None:
    """Connect the transform, rotate and scale attributes of the driver object to the driven object.

    This is typically used to copy attributes from a driver joint into a driven joint so that the
    joint hierarchy/skeleton can be cleanly exported for game engines.

    :param driver_object_name: the name of the driver object.
    :param driven_object_name:  the name of the driven object.
    """
    for attr in ["translate", "rotate", "scale"]:
        cmds.setAttr(f"{driven_object_name}.{attr}", lock=False)
        cmds.connectAttr(f"{driver_object_name}.{attr}", f"{driven_object_name}.{attr}", lock=True, force=True)


def _create_driver_joint(joint_name: str,
                         base_joint_name: str,
                         base_parent_joint_name: Optional[str],
                         rs: RiggingSettings) -> None:
    new_joint_name = rs.derive_driver_joint_name(base_joint_name)
    parent_new_joint_name = rs.derive_driver_joint_name(base_parent_joint_name) if base_parent_joint_name else None
    _create_joint_from_template(joint_name, "driver joint", new_joint_name, parent_new_joint_name, rs)


def _create_joint_from_template(source_joint_name: str,
                                label: str,
                                new_joint_name: str,
                                parent_new_joint_name: Optional[str],
                                rs: RiggingSettings) -> None:
    if rs.debug_logging:
        print(f"Creating {label} '{new_joint_name}'")
    actual_new_joint_name = cmds.joint(name=new_joint_name)
    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)
    util.ensure_created_object_name_matches(label, actual_new_joint_name, new_joint_name)
    if parent_new_joint_name:
        _safe_parent(label, new_joint_name, parent_new_joint_name, rs)
    elif rs.driver_skeleton_group and rs.use_driver_hierarchy:
        _safe_parent(label, new_joint_name, rs.driver_skeleton_group, rs)
    elif rs.root_group_name:
        _safe_parent(label, new_joint_name, rs.root_group_name, rs)
    cmds.matchTransform(new_joint_name, source_joint_name)
    cmds.makeIdentity(new_joint_name,
                      apply=True,
                      rotate=True,
                      translate=True,
                      preserveNormals=True,
                      scale=True,
                      normal=False)
    util.copy_attributes(source_joint_name,
                         new_joint_name,
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
    _set_selection_child_highlighting(new_joint_name, rs)
    if rs.debug_logging:
        print(f"Created {label} named '{new_joint_name}'.")
    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)


def _set_selection_child_highlighting(object_name: str, rs: RiggingSettings):
    selection_child_highlighting = 1 if rs.selection_child_highlighting else 0
    # noinspection PyTypeChecker
    cmds.setAttr(f"{object_name}.selectionChildHighlighting", selection_child_highlighting)


def _setup_control(base_control_name: str,
                   parent_control_name: Optional[str],
                   target_object_name: Optional[str],
                   rs: RiggingSettings,
                   use_config_to_manage_control_channels: bool = True,
                   leave_visibility_unlocked: bool = False) -> str:
    """Create a control offset group and control.

    :param base_control_name: the base name of the control, offset group etc.
    :param parent_control_name: the name of the parent object if any.
    :param target_object_name: the name of the object that the offset group will match transforms to and derived side-edness from. This is typically the joint in source skeleton that we want to control.
    :param rs: the settings that drive the rigging process.
    :return: the name of the control.
    """
    if rs.debug_logging:
        print(f"Creating {base_control_name} control for target '{target_object_name}' under "
              f"parent control '{parent_control_name}'")

    if target_object_name:
        util.ensure_single_object_named(None, target_object_name)

    offset_group_name = rs.derive_offset_group_name(base_control_name)
    _create_group("offset group", offset_group_name, target_object_name, rs)
    _parent_group("offset group", offset_group_name, parent_control_name, rs)

    if target_object_name:
        cmds.matchTransform(offset_group_name, target_object_name)

    control_name = _create_control(base_control_name, rs)
    _safe_parent(f"{base_control_name} control", control_name, offset_group_name, rs)

    control_configs = rs.find_matching_control_config(control_name)

    _configure_control_shape(control_name, control_configs, rs)
    _configure_control_scale(control_name, parent_control_name, control_configs)

    _configure_control_set(control_name, control_configs, rs)
    _configure_control_side(base_control_name, control_name, target_object_name, rs)
    _set_override_colors(control_name, rs)
    _tag_controls(control_name, parent_control_name, control_configs, rs)

    # Hide attributes on the controller that we do not want animators to access and/or keyframe
    if use_config_to_manage_control_channels:
        _lock_and_hide_controller_transform_attributes_based_on_config(control_name, rs, leave_visibility_unlocked)

    return control_name


def _configure_control_shape(control_name: str, control_configs: list[ControllerConfig], rs: RiggingSettings) -> None:
    for control_config in control_configs:
        if control_config.control_template:
            copy_control(control_config.control_template, control_name, rs)


def _configure_control_scale(control_name: str,
                             parent_control_name: str,
                             control_configs: list[ControllerConfig]) -> None:
    scale = None
    for config in control_configs:
        if scale is None and config.control_scale:
            scale = config.control_scale
            break
    if not scale and parent_control_name:
        # If we have a parent then try and make a random guess at what may be a good scale

        # noinspection PyArgumentList

        translation = cmds.xform(parent_control_name, query=True, worldSpace=True, translation=True)
        # noinspection PyUnresolvedReferences
        parent_x = translation[0]
        # noinspection PyUnresolvedReferences
        parent_y = translation[1]
        # noinspection PyUnresolvedReferences
        parent_z = translation[2]
        # noinspection PyArgumentList
        translation = cmds.xform(control_name, query=True, worldSpace=True, translation=True)
        # noinspection PyUnresolvedReferences
        control_x = translation[0]
        # noinspection PyUnresolvedReferences
        control_y = translation[1]
        # noinspection PyUnresolvedReferences
        control_z = translation[2]

        x = parent_x - control_x
        y = parent_y - control_y
        z = parent_z - control_z

        # length of joint acts as a scale
        scale = math.sqrt(x * x + y * y + z * z)
    if scale:
        cmds.scale(scale, scale, scale, control_name, absolute=True)
        cmds.makeIdentity(control_name,
                          apply=True,
                          translate=False,
                          rotate=False,
                          scale=True,
                          preserveNormals=True,
                          normal=False)


def _tag_controls(control_name: str,
                  parent_control_name: str,
                  control_configs: list[ControllerConfig],
                  rs: RiggingSettings) -> None:
    if rs.tag_controls:
        # Tag the control as a controller
        if parent_control_name and "transform" == cmds.objectType(parent_control_name):
            cmds.controller(control_name, parent_control_name, parent=True)
        else:
            cmds.controller(control_name)
        tag_name = None

        results = cmds.listConnections(control_name, connections=True)
        if results:
            for r in results:
                if r.startswith(f"{control_name}_tag"):
                    tag_name = r
        if not tag_name:
            raise Exception(f"Attempt to create tag for control {control_name} failed to produce a tag with "
                            f"the name {control_name}_tag. This is possibility due to failure to delete history "
                            f"before running script or another control with the same name.  Aborting!")

        for control_config in control_configs:
            if control_config.visibility_mode:
                if control_config.visibility_mode == 'inherit':
                    # noinspection PyTypeChecker
                    cmds.setAttr(f"{tag_name}.visibilityMode", 1)
                elif control_config.visibility_mode == 'show_on_proximity':
                    # noinspection PyTypeChecker
                    cmds.setAttr(f"{tag_name}.visibilityMode", 2)
                else:  # 'default' or bad value
                    # noinspection PyTypeChecker
                    cmds.setAttr(f"{tag_name}.visibilityMode", 0)
                break


def _configure_control_side(base_control_name: str,
                            control_name: str,
                            target_object_name: str,
                            rs: RiggingSettings) -> None:
    side = "center"
    if target_object_name and cmds.objExists(f"{target_object_name}.side"):
        joint_side = cmds.getAttr(f"{target_object_name}.side")
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
    cmds.addAttr(control_name, longName="rfJointSide", niceName="Joint Side", dataType="string")
    cmds.setAttr(f"{control_name}.rfJointSide", side, type="string")


def _configure_control_set(control_name: str, control_configs: list[ControllerConfig], rs: RiggingSettings) -> None:
    if rs.use_control_set:
        control_set = None
        for control_config in control_configs:
            if control_config.control_set:
                control_set = control_config.control_set
                break

        # Add control to the control set if configured
        if control_set:
            _maybe_create_set(control_set, rs)
            # noinspection PyArgumentList
            cmds.sets(control_name, edit=True, forceElement=control_set)


def _lock_and_hide_controller_transform_attributes_based_on_config(control_name: str,
                                                                   rs: RiggingSettings,
                                                                   leave_visibility_unlocked: bool = False) -> None:
    control_configs = rs.find_matching_control_config(control_name)

    translate_x = None
    translate_y = None
    translate_z = None
    rotate_x = None
    rotate_y = None
    rotate_z = None
    scale_x = None
    scale_y = None
    scale_z = None
    for control_config in control_configs:
        if translate_x is None and control_config.translate_x is not None:
            translate_x = control_config.translate_x
        if translate_y is None and control_config.translate_y is not None:
            translate_y = control_config.translate_y
        if translate_z is None and control_config.translate_z is not None:
            translate_z = control_config.translate_z
        if rotate_x is None and control_config.rotate_x is not None:
            rotate_x = control_config.rotate_x
        if rotate_y is None and control_config.rotate_y is not None:
            rotate_y = control_config.rotate_y
        if rotate_z is None and control_config.rotate_z is not None:
            rotate_z = control_config.rotate_z
        if scale_x is None and control_config.scale_x is not None:
            scale_x = control_config.scale_x
        if scale_y is None and control_config.scale_y is not None:
            scale_y = control_config.scale_y
        if scale_z is None and control_config.scale_z is not None:
            scale_z = control_config.scale_z

    _maybe_lock_and_hide_controller_transform_attributes(control_name,
                                                         translate_x is not None and not translate_x,
                                                         translate_y is not None and not translate_y,
                                                         translate_z is not None and not translate_z,
                                                         rotate_x is not None and not rotate_x,
                                                         rotate_y is not None and not rotate_y,
                                                         rotate_z is not None and not rotate_z,
                                                         scale_x is not None and not scale_x,
                                                         scale_y is not None and not scale_y,
                                                         scale_z is not None and not scale_z,
                                                         not leave_visibility_unlocked)


def _maybe_lock_and_hide_controller_transform_attributes(control_name: str,
                                                         lock_translate_x: bool,
                                                         lock_translate_y: bool,
                                                         lock_translate_z: bool,
                                                         lock_rotate_x: bool,
                                                         lock_rotate_y: bool,
                                                         lock_rotate_z: bool,
                                                         lock_scale_x: bool,
                                                         lock_scale_y: bool,
                                                         lock_scale_z: bool,
                                                         lock_visibility: bool):
    if lock_translate_x:
        cmds.setAttr(f"{control_name}.translateX", lock=True, keyable=False, channelBox=False)
    if lock_translate_y:
        cmds.setAttr(f"{control_name}.translateY", lock=True, keyable=False, channelBox=False)
    if lock_translate_z:
        cmds.setAttr(f"{control_name}.translateZ", lock=True, keyable=False, channelBox=False)
    if lock_rotate_x:
        cmds.setAttr(f"{control_name}.rotateX", lock=True, keyable=False, channelBox=False)
    if lock_rotate_y:
        cmds.setAttr(f"{control_name}.rotateY", lock=True, keyable=False, channelBox=False)
    if lock_rotate_z:
        cmds.setAttr(f"{control_name}.rotateZ", lock=True, keyable=False, channelBox=False)
    if lock_scale_x:
        cmds.setAttr(f"{control_name}.scaleX", lock=True, keyable=False, channelBox=False)
    if lock_scale_y:
        cmds.setAttr(f"{control_name}.scaleY", lock=True, keyable=False, channelBox=False)
    if lock_scale_z:
        cmds.setAttr(f"{control_name}.scaleZ", lock=True, keyable=False, channelBox=False)
    if lock_visibility:
        cmds.setAttr(f"{control_name}.visibility", lock=True, keyable=False, channelBox=False)


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


def _set_override_colors(control_name: str, rs: RiggingSettings) -> None:
    side = cmds.getAttr(f"{control_name}.rfJointSide") if cmds.objExists(f"{control_name}.rfJointSide") else None
    child_shapes = cmds.listRelatives(control_name, type="nurbsCurve")
    if child_shapes:
        for child in child_shapes:
            color_set = False
            for c in rs.find_matching_control_config(control_name):
                if c.color:
                    _set_override_color_attributes(child, c.color)
                    color_set = True
                    break

            if not color_set:
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


def _ik_fk_scale_constraint(driven_name: str,
                            ik_joint_name: str,
                            fk_joint_name: str,
                            rs: RiggingSettings,
                            maintain_offset: bool = False) -> str:
    if rs.debug_logging:
        print(f"Adding FK scale constraint for ik joint name '{ik_joint_name}' and fk joint name "
              f"'{fk_joint_name}' to drive '{driven_name}'")

    object_name = f"{driven_name}_scaleConstraint_ik_fk"
    actual_object_name = cmds.scaleConstraint(ik_joint_name,
                                              fk_joint_name,
                                              driven_name,
                                              maintainOffset=maintain_offset,
                                              name=object_name)[0]
    util.ensure_created_object_name_matches("scaleConstraint", actual_object_name, object_name)

    # Lock and hide attributes on constraint
    for attr_name in ["nodeState", "offsetX", "offsetY", "offsetZ"]:
        cmds.setAttr(f"{object_name}.{attr_name}", channelBox=False, keyable=False, lock=True)

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)

    return object_name


def _parent_constraint(driven_name: str, driver_name: str, rs: RiggingSettings, maintain_offset: bool) -> str:
    if rs.debug_logging:
        print(f"Adding parent constraint from child '{driven_name}' to parent '{driver_name}'")

    object_name = f"{driven_name}_parentConstraint_{driver_name}"
    actual_object_name = cmds.parentConstraint(driver_name,
                                               driven_name,
                                               maintainOffset=maintain_offset,
                                               name=object_name)[0]
    util.ensure_created_object_name_matches("parentConstraint", actual_object_name, object_name)

    # Lock and hide attributes on constraint
    for attr_name in ["nodeState",
                      "interpType",
                      "rotationDecompositionTargetX",
                      "rotationDecompositionTargetY",
                      "rotationDecompositionTargetZ",
                      "w0"]:
        cmds.setAttr(f"{object_name}.{attr_name}", channelBox=False, keyable=False, lock=True)

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)
    return object_name


def _point_constraint(driven_name: str,
                      driver_name: str,
                      rs: RiggingSettings,
                      include_x: bool = True,
                      include_y: bool = True,
                      include_z: bool = True,
                      maintain_offset: bool = False) -> str:
    if rs.debug_logging:
        print(f"Adding point constraint where '{driven_name}' is driven by '{driver_name}' including "
              f"axis x={include_x}, y={include_y}, z={include_z}")

    skip = []
    if not include_x:
        skip.append("x")
    if not include_y:
        skip.append("y")
    if not include_z:
        skip.append("z")
    if 0 == len(skip):
        skip.append("none")
    object_name = f"{driven_name}_pointConstraint_{driver_name}"
    # noinspection PyTypeChecker
    actual_object_name = cmds.pointConstraint(driver_name,
                                              driven_name,
                                              maintainOffset=maintain_offset,
                                              skip=skip,
                                              name=object_name)[0]
    util.ensure_created_object_name_matches("orientConstraint", actual_object_name, object_name)

    # Lock and hide attributes on constraint
    for attr_name in ["nodeState", "offsetX", "offsetY", "offsetZ", "w0"]:
        cmds.setAttr(f"{object_name}.{attr_name}", channelBox=False, keyable=False, lock=True)

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)
    return object_name


def _orient_constraint(driven_name: str,
                       driver_name: str,
                       rs: RiggingSettings,
                       include_x: bool = True,
                       include_y: bool = True,
                       include_z: bool = True,
                       maintain_offset: bool = False) -> str:
    if rs.debug_logging:
        print(f"Adding orient constraint where '{driven_name}' is driven by '{driver_name}' including "
              f"axis x={include_x}, y={include_y}, z={include_z}")

    skip = []
    if not include_x:
        skip.append("x")
    if not include_y:
        skip.append("y")
    if not include_z:
        skip.append("z")
    if 0 == len(skip):
        skip.append("none")
    object_name = f"{driven_name}_orientConstraint_{driver_name}"
    # noinspection PyTypeChecker
    actual_object_name = cmds.orientConstraint(driver_name,
                                               driven_name,
                                               maintainOffset=maintain_offset,
                                               skip=skip,
                                               name=object_name)[0]
    util.ensure_created_object_name_matches("orientConstraint", actual_object_name, object_name)

    # Lock and hide attributes on constraint
    for attr_name in ["nodeState", "interpType", "offsetX", "offsetY", "offsetZ", "w0"]:
        cmds.setAttr(f"{object_name}.{attr_name}", channelBox=False, keyable=False, lock=True)

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)
    return object_name


def _scale_constraint(driven_name: str,
                      driver_name: str,
                      rs: RiggingSettings,
                      include_x: bool = True,
                      include_y: bool = True,
                      include_z: bool = True,
                      maintain_offset: bool = False) -> str:
    if rs.debug_logging:
        print(f"Adding scale constraint where '{driven_name}' is driven by '{driver_name}' including "
              f"axis x={include_x}, y={include_y}, z={include_z}")

    skip = []
    if not include_x:
        skip.append("x")
    if not include_y:
        skip.append("y")
    if not include_z:
        skip.append("z")
    if 0 == len(skip):
        skip.append("none")
    object_name = f"{driven_name}_scaleConstraint_{driver_name}"
    # noinspection PyTypeChecker
    actual_object_name = cmds.scaleConstraint(driver_name,
                                              driven_name,
                                              maintainOffset=maintain_offset,
                                              skip=skip,
                                              name=object_name)[0]
    util.ensure_created_object_name_matches("scaleConstraint", actual_object_name, object_name)

    # Lock and hide attributes on constraint
    for attr_name in ["nodeState", "offsetX", "offsetY", "offsetZ", "w0"]:
        cmds.setAttr(f"{object_name}.{attr_name}", channelBox=False, keyable=False, lock=True)

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)
    return object_name


def _ik_fk_parent_constraint(driven_name: str,
                             ik_joint_name: str,
                             fk_joint_name: str,
                             rs: RiggingSettings,
                             maintain_offset: bool = False) -> str:
    if rs.debug_logging:
        print(f"Adding FK parent constraint for ik joint name '{ik_joint_name}' and fk joint name "
              f"'{fk_joint_name}' to drive '{driven_name}'")

    object_name = f"{driven_name}_parentConstraint_ik_fk"
    actual_object_name = cmds.parentConstraint(ik_joint_name,
                                               fk_joint_name,
                                               driven_name,
                                               maintainOffset=maintain_offset,
                                               name=object_name)[0]
    util.ensure_created_object_name_matches("parentConstraint", actual_object_name, object_name)

    # Lock and hide attributes on constraint
    for attr_name in ["nodeState",
                      "interpType",
                      "rotationDecompositionTargetX",
                      "rotationDecompositionTargetY",
                      "rotationDecompositionTargetZ"]:
        cmds.setAttr(f"{object_name}.{attr_name}", channelBox=False, keyable=False, lock=True)

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)
    return object_name


def _safe_parent(label: str, child_name: str, parent_name: str, rs: RiggingSettings):
    """Parent child to parent with additional checks to verify success and add debug logging."""
    if rs.debug_logging:
        print(f"Parenting {label} '{child_name}' to '{parent_name}'")
    parented = cmds.parent(child_name, parent_name)
    if 0 == len(parented):
        raise Exception(f"Failed to parent '{child_name}' under '{parent_name}'")

    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)


def _parent_group(label: str, group_name: str, parent_object_name: Optional[str], rs: RiggingSettings) -> None:
    if parent_object_name and rs.use_control_hierarchy:
        _safe_parent(label, group_name, parent_object_name, rs)
    else:
        # Place the group under one of the administrative groups if enabled
        if rs.controls_group:
            _safe_parent(label, group_name, rs.controls_group, rs)
        elif rs.root_group_name:
            _safe_parent(label, group_name, rs.root_group_name, rs)

        if parent_object_name:
            # If there is a "logical" parent then add constraints so that the group behaves as
            # if it was in a direct hierarchy
            _parent_constraint(group_name, parent_object_name, rs, maintain_offset=True)
            _scale_constraint(group_name, parent_object_name, rs, maintain_offset=True)


def _create_group(label: str, group_name: str, match_transform_object_name: Optional[str], rs: RiggingSettings) -> None:
    """
    Create a group under a parent object.
    The group ensures all the transforms are locked and hidden from channel box.

    :param label: the human-readable name used to describe the group
    :param group_name: the name used to create group.
    :param match_transform_object_name: the object that this group will match transform of
    :param rs:the RiggingSettings
    """
    if rs.debug_logging:
        if match_transform_object_name:
            print(f"Creating {label} '{group_name}' matching transform of '{match_transform_object_name}'")
        else:
            print(f"Creating {label} '{group_name}' at origin.")

    if match_transform_object_name:
        util.ensure_single_object_named(None, match_transform_object_name)
    cmds.select(clear=True)
    actual_object_name = cmds.group(name=group_name, empty=True)
    util.ensure_created_object_name_matches(label, actual_object_name, group_name)
    if match_transform_object_name:
        cmds.matchTransform(group_name, match_transform_object_name)
    _set_selection_child_highlighting(group_name, rs)

    _hide_transform_properties(group_name)
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
    #  scaling based on bone size and all sorts of options. For now we go with simple shape or copying from existing
    actual_control_name = cmds.circle(name=control_name, normalX=1, normalY=0, normalZ=0, radius=1)[0]
    util.ensure_created_object_name_matches("offset group", actual_control_name, control_name)
    _set_selection_child_highlighting(control_name, rs)

    cmds.matchTransform(control_name, offset_group_name)
    cmds.select(clear=True)

    return control_name


def _setup_top_level_infrastructure(rs: RiggingSettings) -> None:
    """Create the groups, sets, layers etc. required to organize our rig."""
    _create_top_level_group(rs)
    _create_controls_group(rs)
    _create_driver_skeleton_group(rs)


def _create_top_level_group(rs: RiggingSettings) -> None:
    """Create a group in which to place our rig and related infrastructure."""
    if rs.root_group_name:
        _pre_top_level_create("root group", "transform", rs.root_group_name, rs)

        actual_root_group_name = cmds.group(name=rs.root_group_name, empty=True)

        util.ensure_created_object_name_matches("root group", actual_root_group_name, rs.root_group_name)
        _lock_and_hide_transform_properties(actual_root_group_name)
        _set_selection_child_highlighting(rs.root_group_name, rs)

        _post_top_level_create("root group", rs.root_group_name, rs)


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
        if rs.root_group_name:
            _safe_parent("controls group", rs.controls_group, rs.root_group_name, rs)


def _create_driver_skeleton_group(rs: RiggingSettings) -> None:
    """
    Create a group to contain the driver skeleton.
    This is used for organisational purposes.
    """
    if rs.driver_skeleton_group and rs.driver_skeleton_group:
        actual_group_name = cmds.group(name=rs.driver_skeleton_group, empty=True)
        util.ensure_created_object_name_matches("driver skeleton group", actual_group_name, rs.driver_skeleton_group)
        _set_selection_child_highlighting(rs.driver_skeleton_group, rs)
        _lock_and_hide_transform_properties(rs.driver_skeleton_group)
        # Clear selection to avoid unintended selection dependent behaviour
        cmds.select(clear=True)
        if rs.root_group_name:
            _safe_parent("driver skeleton group", rs.driver_skeleton_group, rs.root_group_name, rs)


def _maybe_create_set(set_name: str, rs: RiggingSettings) -> None:
    """
      Create the set if it does not already exist.
    """

    if rs.use_control_set and 0 == len(cmds.ls(set_name, exactType="objectSet")):
        _pre_top_level_create("set", "objectSet", set_name, rs)

        cmds.sets(name=set_name, empty=True)

        _post_top_level_create("set", set_name, rs)


def _pre_top_level_create(label: str, maya_type: str, object_name: str, rs: RiggingSettings):
    existing_object_names = cmds.ls(object_name, exactType=maya_type)
    if 0 == len(existing_object_names):
        if rs.debug_logging:
            print(f"Creating {label} '{object_name}'")
    elif 1 == len(existing_object_names):
        if rs.debug_logging:
            print(f"Re-creating {label} '{object_name}'")
        cmds.delete(object_name)
        if rs.root_group_name:
            util.delete_history(rs.root_group_name)
    else:
        raise Exception(f"The {label} named '{object_name}' already has multiple instances. Aborting!")


def _post_top_level_create(label: str, object_name: str, rs: RiggingSettings):
    # Clear selection to avoid unintended selection dependent behaviour
    cmds.select(clear=True)

    if rs.debug_logging:
        print(f"Created {label} '{object_name}'")
