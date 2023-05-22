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
