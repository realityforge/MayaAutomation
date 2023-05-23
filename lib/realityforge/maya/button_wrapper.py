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


def wrap(fn, *args, **kwargs):
    """ A function that can be used to wrap functions for passing as command argument in Button command in maya.

    Use it like cmds.button(label='Do Stuff'), command=wrap(my_function, arg_1, arg_2, arg_3)

    :param fn: The function to call.
    :param args: The arguments to pass to the function.
    :param kwargs: The keyword arguments to pass to the function.
    :return: The function with the correct shape for use in the Maya button command argument.
    """
    def wrapped(_):
        fn(*args, **kwargs)

    return wrapped
