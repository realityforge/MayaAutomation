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

import pathlib
import sys



def _workspace_path(relative_path: str) -> str:
    base_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
    path = pathlib.Path(f'{base_dir}/{relative_path}').resolve()
    return f"{path}"


def _add_sys_path(relative_path: str) -> None:
    sys.path.append(_workspace_path(relative_path))


def setup():
    # Tween Machines used for setting up breakdown poses

    # Add the path for TweenMachine library
    _add_sys_path('vendor/tweenMachine/python')
    import tweenMachine

    # Red 9 plugin primarily used for pose mirroring

    _add_sys_path('vendor/Red9_StudioPack_Python3')
    import Red9
    Red9.start()
    # Assume for now that all commands go to Custom shelf
    parent = 'Custom'

    names = cmds.shelfLayout(parent, query=True, childArray=True) or []
    labels = [cmds.shelfButton(n, query=True, label=True) for n in names]

    # Add Button for TweenMachine
    if 'TweenMachine' not in labels:
        icon_path = _workspace_path('vendor/tweenMachine/python/icons/tm3-ShelfIcon.png')
        cmds.shelfButton(
            command="import tweenMachine\ntweenMachine.start()",
            annotation='Tween Machine',
            sourceType='Python',
            label='TweenMachine',
            image=icon_path,
            image1=icon_path,
            parent=parent
        )

