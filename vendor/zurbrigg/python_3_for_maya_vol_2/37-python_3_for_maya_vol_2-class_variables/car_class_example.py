class Car(object):

    version = "1.0"

    def __init__(self, make, color):
        self.make = make
        self.color = color

    def print_stats(self):
        print(f"make: {self.make}")
        print(f"color: {self.color}")
        print(f"version: {Car.version}")
        print("---")


if __name__ == "__main__":
    car_a = Car("Mazda", "black")
    car_b = Car("Honda", "red")

    car_a.print_stats()
    car_b.print_stats()

    Car.version = "2.0"

    car_a.print_stats()
    car_b.print_stats()

