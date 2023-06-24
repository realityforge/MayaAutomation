import maya.cmds as cmds


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
