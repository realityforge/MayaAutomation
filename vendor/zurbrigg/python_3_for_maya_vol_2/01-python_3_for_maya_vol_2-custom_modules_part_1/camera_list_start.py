import maya.cmds as cmds


if __name__ == "__main__":

    cmds.window(title="Cameras")
    cmds.paneLayout()
    cmds.textScrollList()
    cmds.showWindow()

