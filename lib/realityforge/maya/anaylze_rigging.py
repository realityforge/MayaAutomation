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


class NodeNamingRule:
    def __init__(self, node_type: str, pattern: str, optional_ik_system: bool, optional_fk_system: bool):
        # TODO: Replace optional_(i/f)k_system with system enum?
        self.node_type = node_type
        self.pattern = pattern
        self.needs_side = '[side]' in pattern
        self.optional_ik_system = optional_ik_system
        self.optional_fk_system = optional_fk_system

    def matches(self, needs_side: bool, optional_fk_system: bool, optional_ik_system: bool) -> bool:
        return needs_side == self.needs_side and optional_fk_system == self.optional_fk_system and optional_ik_system == self.optional_ik_system


class NodeNameMap:
    def __init__(self):
        self.rules: dict[str, list[NodeNamingRule]] = dict()

    def register_rule(self, node_type: str, pattern: str, optional_ik_system: bool = False,
                      optional_fk_system: bool = False) -> None:
        rule = NodeNamingRule(node_type, pattern, optional_ik_system=optional_ik_system,
                              optional_fk_system=optional_fk_system)
        if node_type not in self.rules:
            self.rules[node_type] = list()

        replaced = False
        for i in range(len(self.rules[node_type])):
            candidate = self.rules[node_type][i]
            if candidate.matches(rule.needs_side, rule.optional_fk_system, rule.optional_ik_system):
                self.rules[node_type][i] = rule
                replaced = True
        if not replaced:
            self.rules[node_type].append(rule)

    def derive_name(self, node_type: str, base_name: str, side_name: Optional[str], optional_ik_system: bool = False,
                    optional_fk_system: bool = False) -> str:
        needs_side = True if side_name else False
        matched: Optional[NodeNamingRule] = None
        for i in range(len(self.rules[node_type])):
            candidate = self.rules[node_type][i]
            if candidate.matches(needs_side, optional_fk_system, optional_ik_system):
                matched = candidate

        if matched:
            pattern = matched.pattern
            return pattern.replace("[name]", base_name).replace("[side]", side_name)
        else:
            raise Exception(
                f"Unable to match rule for node_type {node_type}, side_name {side_name}, optional_ik_system {optional_ik_system}, optional_fk_system {optional_fk_system}")


DefaultNameMap = NodeNameMap()
DefaultNameMap.register_rule("joint", "[name]_JNT")

DefaultNameMap.register_rule("control", "[name]_CTRL")
DefaultNameMap.register_rule("control", "[name]_[side]_CTRL")
DefaultNameMap.register_rule("control_offset", "[name]_CTRL_OFFSET")
DefaultNameMap.register_rule("control_offset", "[name]_[side]_CTRL_OFFSET")

DefaultNameMap.register_rule("control", "[name]_FK_CTRL", optional_fk_system=True)
DefaultNameMap.register_rule("control", "[name]_[side]_FK_CTRL", optional_fk_system=True)
DefaultNameMap.register_rule("control_offset", "[name]_FK_CTRL_OFFSET", optional_fk_system=True)
DefaultNameMap.register_rule("control_offset", "[name]_[side]_FK_CTRL_OFFSET", optional_fk_system=True)

DefaultNameMap.register_rule("control", "[name]_IK_CTRL", optional_ik_system=True)
DefaultNameMap.register_rule("control", "[name]_[side]_IK_CTRL", optional_ik_system=True)
DefaultNameMap.register_rule("control_offset", "[name]_IK_CTRL_OFFSET", optional_ik_system=True)
DefaultNameMap.register_rule("control_offset", "[name]_[side]_IK_CTRL_OFFSET", optional_ik_system=True)


def create_control_offset(base_name: str, side_name: Optional[str], optional_ik_system: bool = False,
                          optional_fk_system: bool = False) -> str:
    group_name = DefaultNameMap.derive_name("control_offset",
                                            base_name,
                                            side_name,
                                            optional_ik_system=optional_ik_system,
                                            optional_fk_system=optional_fk_system)
    control_name = DefaultNameMap.derive_name("control",
                                              base_name,
                                              side_name,
                                              optional_ik_system=optional_ik_system,
                                              optional_fk_system=optional_fk_system)
    # TODO: Placeholder code - do not use
    # actual_group_name = cmds.group(name=group_name)
    # cmds.parent(control_name, actual_group_name)


def analyze_CTRL_joints(print_errors_only=True):
    for o in cmds.ls('*_CTRL'):
        if 0 != cmds.getAttr(f'{o}.translateX') or 0 != cmds.getAttr(f'{o}.translateY') or 0 != cmds.getAttr(
                f'{o}.translateZ'):
            print(f"{o} BAD - Translation is not 0")
        elif 0 != cmds.getAttr(f'{o}.rotateX') or 0 != cmds.getAttr(f'{o}.rotateY') or 0 != cmds.getAttr(
                f'{o}.rotateZ'):
            print(f"{o} BAD - Rotation is not 0")
        elif not print_errors_only:
            print(f"{o} OK")


def has_IK_JDRV_parent(joint_name):
    parents = cmds.listRelatives(joint_name, parent=True)
    if parents and 0 != len(parents) and parents[0].endswith('_IK_JDRV'):
        return True
    else:
        return False


def has_IK_JDRV_child(joint_name):
    children = cmds.listRelatives(joint_name, children=True)
    if children:
        for child in children:
            if child.endswith('_IK_JDRV'):
                return True
    return False


def analyze_IK_JDRV_joints(print_errors_only=True):
    for o in cmds.ls('*_IK_JDRV'):
        if has_IK_JDRV_parent(o) and has_IK_JDRV_child(o) and 0 == cmds.getAttr(
                f'{o}.preferredAngleX') and 0 == cmds.getAttr(
                f'{o}.preferredAngleY') and 0 == cmds.getAttr(f'{o}.preferredAngleZ'):
            # We should change this so that this check is only applied to internal joints?
            print(f"{o} BAD - No Preferred Angle Set")
        # elif 0 != cmds.getAttr(f'{o}.rotateX') or 0 != cmds.getAttr(f'{o}.rotateY') or 0 != cmds.getAttr(f'{o}.rotateZ'):
        #     print(f"{o} BAD - Rotation is not 0")
        elif not print_errors_only:
            print(f"{o} OK")


analyze_IK_JDRV_joints()
analyze_CTRL_joints()
