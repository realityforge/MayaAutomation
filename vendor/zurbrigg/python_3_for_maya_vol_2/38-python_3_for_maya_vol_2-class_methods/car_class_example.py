class Car(object):

    DEFAULT_MAZDA_COLOR = "black"
    DEFAULT_HONDA_COLOR = "white"

    def __init__(self, make, color):
        self.make = make
        self.color = color

    def print_stats(self):
        print(f"make: {self.make}")
        print(f"color: {self.color}")
        print("---")

    @classmethod
    def create_mazda(cls):
        mazda = Car("Mazda", cls.DEFAULT_MAZDA_COLOR)
        return mazda

    @classmethod
    def create_honda(cls):
        honda = Car("Honda", cls.DEFAULT_HONDA_COLOR)
        return honda


if __name__ == "__main__":
    car_a = Car.create_mazda()
    car_b = Car.create_honda()

    car_a.print_stats()
    car_b.print_stats()


