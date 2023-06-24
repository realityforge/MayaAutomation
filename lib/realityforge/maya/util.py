import maya.cmds as cmds


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
    return True


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
