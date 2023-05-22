class ClassA(object):

    def __init__(self):
        self.name = "ClassA"

    def display_stats(self):
        print(f"Name: {self.name}")


class ClassB(ClassA):

    def __init__(self):
        self.name = "ClassB"

    def display_stats(self):
        print(f"Class B Name: {self.name}")


class ClassC(ClassB):

    def __init__(self):
        self.name = "ClassC"


if __name__ == "__main__":

    class_a = ClassA()
    class_a.display_stats()

    class_b = ClassB()
    class_b.display_stats()

    class_c = ClassC()
    class_c.display_stats()
