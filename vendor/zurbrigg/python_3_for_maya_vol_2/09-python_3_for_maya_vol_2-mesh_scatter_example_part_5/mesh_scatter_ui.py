from functools import partial

import maya.cmds as cmds
import mesh_scatter


def generate_meshes(mesh_type_option, mesh_count_field, *args):
    cmds.file(new=True, force=True)

    mesh_type = cmds.optionMenu(mesh_type_option, q=True, value=True)
    mesh_count = cmds.intField(mesh_count_field, q=True, value=True)

    mesh_scatter.mesh_scatter(mesh_count, mesh_type)

def create_ui():
    window = cmds.window(title="Randomizer", width=300)
    layout = cmds.formLayout()

    mesh_type_option = cmds.optionMenu(label="Mesh Type:", parent=layout)
    cmds.menuItem(label="cube")
    cmds.menuItem(label="sphere")
    cmds.menuItem(label="cylinder")
    cmds.menuItem(label="random")

    mesh_count_label = cmds.text(label="Mesh Count:", parent=layout)
    mesh_count_field = cmds.intField(value=20, minValue=1, parent=layout)

    generate_btn = cmds.button(label="Generate",
                               parent=layout,
                               command=partial(generate_meshes, mesh_type_option, mesh_count_field))

    cmds.formLayout(layout,
                    e=True,
                    af=[(mesh_type_option, "left", 4), (mesh_type_option, "top", 4)])
    cmds.formLayout(layout,
                    e=True,
                    af=[(mesh_count_label, "left", 4)],
                    ac=[(mesh_count_label, "top", 6, mesh_type_option), (mesh_count_field, "top", 4, mesh_type_option), (mesh_count_field, "left", 4, mesh_count_label)])
    cmds.formLayout(layout,
                    e=True,
                    af=[(generate_btn, "left", 4), (generate_btn, "right", 0), (generate_btn, "bottom", 10)],
                    ac=[(generate_btn, "top", 10, mesh_count_label)])

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()
