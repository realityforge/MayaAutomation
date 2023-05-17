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


def is_locked(object_name, attr_name):
    """Return true if the property on the specified object is locked.

    :param object_name: the name of the object.
    :param attr_name: the long or short name of the property.
    :return: true if the property on the specified object is locked, false otherwise.
    """
    return cmds.getAttr(f"{object_name}.{attr_name}", lock=True)


def is_any_locked(object_name, attr_names):
    """Return true if any specified property on the specified object is locked.

    :param object_name: the name of the object.
    :param attr_names: a list of property names. They may be long or short names.
    :return: true if any specified property on the specified object is locked, false otherwise.
    """
    for attr_name in attr_names:
        if is_locked(object_name, attr_name):
            return True
    return False


def smart_parent_constraint(driver_object_name, driven_object_names):
    """Add a parent constraint between the driver object and the driven objects, skipping locked attributes.

    :param driver_object_name:  The parent or driver object.
    :param driven_object_names:  The child or driven objects
    """
    for driven_object_name in driven_object_names:
        skip_rotate = []
        skip_translate = []
        for axis in ['X', 'Y', 'Z']:
            if is_locked(driven_object_name, f"rotate{axis}"):
                skip_rotate.append(axis.lower())
            if is_locked(driven_object_name, f"translate{axis}"):
                skip_translate.append(axis.lower())
        # noinspection PyTypeChecker
        cmds.parentConstraint(driver_object_name,
                              driven_object_name,
                              maintainOffset=True,
                              skipRotate=skip_rotate,
                              skipTranslate=skip_translate)


def smart_scale_constraint(driver_object_name, driven_object_names):
    """Add a scale constraint between the driver object and the driven objects, skipping locked attributes.

    :param driver_object_name:  The parent or driver object.
    :param driven_object_names:  The child or driven objects
    """
    for driven_object_name in driven_object_names:
        skip = []
        for axis in ['X', 'Y', 'Z']:
            if is_locked(driven_object_name, f"scale{axis}"):
                skip.append(axis.lower())
        cmds.scaleConstraint(driver_object_name, driven_object_name, skip=skip)


def smart_master_constraint(driver_object_name, driven_object_names):
    """Add a parent constraint and scale between the driver object and the driven objects, skipping locked attributes.

    :param driver_object_name:  The parent or driver object.
    :param driven_object_names:  The child or driven objects
    """
    smart_parent_constraint(driver_object_name, driven_object_names)
    smart_scale_constraint(driver_object_name, driven_object_names)
