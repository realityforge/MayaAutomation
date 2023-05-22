import random

import maya.cmds as cmds


def set_random_position(transform_node):
    tx = random.randint(-10, 10)
    ty = random.randint(-10, 10)
    tz = random.randint(-10, 10)
    cmds.setAttr(f"{transform_node}.translate", tx, ty, tz, type="double3")

def mesh_scatter(num_meshes):
    for i in range(num_meshes):
        transform_node = cmds.polyCube()[0]
        set_random_position(transform_node)


if __name__ == "__main__":
    cmds.file(new=True, force=True)

    mesh_scatter(20)
