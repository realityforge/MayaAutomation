import maya.cmds as cmds

def transforms_from_shape_nodes(shapes):
    transforms = []

    for obj in shapes:
        if cmds.objectType(obj, isAType="shape"):
            parents = cmds.listRelatives(obj, parent=True)
            if parents:
                transforms.append(parents[0])

    return transforms

def camera_transforms():
    camera_shapes = cmds.ls(cameras=True)
    cameras = transforms_from_shape_nodes(camera_shapes)

    return cameras

def print_stats():
    print("Stats Line 1")
    print("Stats Line 2")
    print("Stats Line 3")
    print("Stats Line 4")



if __name__ == "__main__":
    print(camera_transforms())

