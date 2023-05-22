import maya.cmds as cmds
import node_helpers


def display():
    cameras = node_helpers.camera_transforms()

    cmds.window(title="Cameras")
    cmds.paneLayout()
    cmds.textScrollList(append=cameras)
    cmds.showWindow()


if __name__ == "__main__":
    display()
