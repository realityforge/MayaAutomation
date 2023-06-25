import maya.cmds as cmds

import os
import pathlib
import subprocess

import maya.cmds as cmds


def open_explorer(path: str) -> None:
    """Open the windows explorer with the specified path.

    :param path: the directory
    """
    actual_path = os.path.normpath(path)

    explorer_path = pathlib.Path(os.getenv('WINDIR')) / 'explorer.exe'

    if os.path.isdir(actual_path):
        subprocess.run([explorer_path, actual_path])
    elif os.path.isfile(actual_path):
        subprocess.run([explorer_path, '/select,', actual_path])


def open_explorer_in_workspace() -> None:
    """Open the windows explorer in the workspace directory."""
    # noinspection PyArgumentList
    open_explorer(cmds.workspace(query=True, directory=True))


def get_scene_short_name():
    """Return the basename of the scene file.

    Returns:
        the basename of the scene file.
    """

    # Get Full path of maya scene
    # noinspection PyArgumentList
    scene_filename = cmds.file(query=True, sceneName=True)
    # Get last part of the path
    local_scene_filename = scene_filename.split('/')[-1]
    size = len(local_scene_filename)
    # Remove ".mb" from the filename
    scene_short_name = local_scene_filename[:size - 3]
    return scene_short_name


def select_if_present(object_name):
    """Check if object with that name exists and select it if present

    Args:
        object_name: the name of the object to select

    Returns:
        bool: True if node was selected, False otherwise
    """

    try:
        cmds.select(object_name, replace=True)
        return True
    except:
        return False


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


def unlock_all_attributes(object_name: str, print_debug: bool = False, transitive: bool = True) -> None:
    """Unlock the attributes of the specified object and optionally unlock all child objects.

    :param object_name: the name of the object to start unlock process at.
    :param print_debug: should debug prints be emitted.
    :param transitive: should the unlocking process propagate to child.
    """
    for attr in cmds.listAttr(object_name):
        try:
            qualified_attr_name = f"{object_name}.{attr}"
            if cmds.getAttr(qualified_attr_name, lock=True) == True:
                if print_debug:
                    print(f"{qualified_attr_name} is Locked")
                cmds.setAttr(qualified_attr_name, lock=False)
                if print_debug:
                    print(f"{qualified_attr_name} has been unlocked")
            else:
                if print_debug:
                    print(f"{qualified_attr_name} is not Locked")
        except ValueError:
            if print_debug:
                print(f"Couldn't get locked-state of {qualified_attr_name}")
    if transitive:
        children = cmds.listRelatives(object_name)
        if children:
            for child_object_name in cmds.listRelatives(object_name):
                unlock_all_attributes(child_object_name, print_debug, transitive)


def apply_material(object_name: str, material_name: str) -> None:
    """Apply specified material to specified object.
    The object is expected to transform node above a Shape and will be left selected after this method.

    :param object_name:  the name of the object.
    :param material_name: the material to apply.
    """
    cmds.select(object_name, replace=True)
    cmds.hyperShade(assign=material_name)


def ensure_single_object_named(object_type: str, object_name: str) -> None:
    """Generate an error if there is not exactly one object with the specified name.

    :param object_type: the type of the object (as used in error message)
    :param object_name: the name of the object.
    """
    actual_joint_names = cmds.ls(object_name, exactType=object_type)
    if 0 == len(actual_joint_names):
        raise Exception(f"Unable to locate {object_type} named '{object_name}'")
    elif 1 != len(actual_joint_names):
        raise Exception(f"Multiple {object_type} instances named '{object_name}'. Aborting!")


def ensure_created_object_name_matches(object_description: str,
                                       actual_object_name: str,
                                       expected_object_name: str) -> None:
    """Generate an error if the actual object name does not match the expected object name.
    This is expected to be used after the object has been created.

    :param object_description: the description of the object created.
    :param actual_object_name: the created objects name.
    :param expected_object_name: the expected name of the created object.
    """
    if actual_object_name != expected_object_name:
        raise Exception(f"Attempt to create a {object_description} named '{expected_object_name}' resulted in "
                        f"the creation of a joint named {actual_object_name}'. Possible multiple objects with "
                        f"the same name. Aborting!")


def copy_attributes(source_object_name: str, target_object_name: str, attribute_names: list[str]) -> None:
    """Copy the values of the specified attributes from the source object to the target object.

    :param source_object_name: the source object.
    :param target_object_name: the target object.
    :param attribute_names: the attributes to copy
    """
    for attribute_name in attribute_names:
        try:
            value = cmds.getAttr(f"{source_object_name}.{attribute_name}")
        except Exception:
            raise Exception(f"Failed to get attribute {source_object_name}.{attribute_name} when attempting "
                            f"to copy attribute to {target_object_name}.{attribute_name}")
        try:
            cmds.setAttr(f"{source_object_name}.{attribute_name}", value)
        except Exception:
            raise Exception(f"Failed to set attribute {target_object_name}.{attribute_name} when attempting "
                            f"to copy attribute from {source_object_name}.{attribute_name}")
