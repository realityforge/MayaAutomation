# Maya Python Automation

This repository contains scripts that were developed while learning how to automate Maya using Python.

To make these available you need to add the following snippet to `userSetup.py` located correctly for your OS.

```python
import sys

sys.path.append("/path/to/this/repository/lib")

from realityforge.maya import setup

setup.setup()
```

The correct location to put this file is:

* **Mac**: /Users/&lt;username&gt;/Library/Preferences/Autodesk/maya/&lt;version&gt;/scripts
* **Linux**: ~&lt;username&gt;/maya/&lt;version&gt;/scripts
* **Windows**: C:\Users\\&lt;username&gt;\Documents\maya\\&lt;version&gt;\scripts

To add a script action to the shelf, the standard process is to force the reload of the script when the action runs. You can add a python snippet like  

```python
from importlib import reload

import realityforge.maya.myscript as myscript
reload(myscript)

myscript.my_function()
```

However, sometimes you want project specific code which you store in the scripts directory. In which case the code snippet may look like:


```python
from importlib import reload

# Add project scripts to path ... This is probably wrong.
project_scripts_dir = cmds.workspace(expandName = "scripts")
if not project_scripts_dir in sys.path:
    sys.path.append(project_scripts_dir)

import local_module_in_scripts
reload(local_module_in_scripts)

# Remove path
sys.path.pop(sys.path.index(project_scripts_dir))

  
local_module_in_scripts.my_function()
```

## TweenMachine

The [TweenMachine](https://github.com/The-Maize/tweenMachine) plugin has been vendored into this repository to make installation easier. This plugin is used to create breakdown poses.

You may also need to copy the icons from  `vendor/tweenMachine/python/icons/` into your maya directory `prefs/icon`. 

To install to your shelf add a button with the following snippet with the icon `vendor/tweenMachine/python/icons/tm3-ShelfIcon.png`.

```python
import tweenMachine

tweenMachine.start()
```
