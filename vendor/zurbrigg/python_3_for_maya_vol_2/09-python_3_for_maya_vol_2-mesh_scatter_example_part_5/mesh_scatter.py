import random

import maya.cmds as cmds


def set_random_position(transform_node):
    tx = random.randint(-10, 10)
    ty = random.randint(-10, 10)
    tz = random.randint(-10, 10)
    cmds.setAttr(f"{transform_node}.translate", tx, ty, tz, type="double3")

def mesh_scatter(num_meshes, mesh_type="cube", size=1):
    mesh_transforms = []
    valid_mesh_types = ["cube", "sphere", "cylinder"]

    is_random = mesh_type == "random"

    for i in range(num_meshes):
        if is_random:
            mesh_type = random.choice(valid_mesh_types)

        if mesh_type == "sphere":
            transform_node = cmds.polySphere(radius=size)[0]
        elif mesh_type == "cylinder":
            transform_node = cmds.polyCylinder(radius=size, height=2*size)[0]
        else:
            transform_node = cmds.polyCube(width=size, depth=size, height=size)[0]

        set_random_position(transform_node)

        mesh_transforms.append(transform_node)

    cmds.group(mesh_transforms, name="scattered_meshes")


if __name__ == "__main__":
    cmds.file(new=True, force=True)

    mesh_scatter(20, mesh_type="random", size=0.5)
