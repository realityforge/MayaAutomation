class Vehicle(object):

    VEHICLE_TYPE = "Vehicle"

    def __init__(self, top_speed, passenger_count):
        self.top_speed = top_speed
        self.passenger_count = passenger_count

    def get_number_of_wheels(self):
        return 0

    def display_info(self):
        print(f"Vehicle Type: {self.VEHICLE_TYPE}")
        print(f"Top Speed: {self.top_speed}")
        print(f"Passenger Count: {self.passenger_count}")
        print(f"Number of Wheels: {self.get_number_of_wheels()}")


class Car(Vehicle):

    VEHICLE_TYPE = "Car"

    def __init__(self, top_speed, passenger_count):
        super().__init__(top_speed, passenger_count)

    def get_number_of_wheels(self):
        return 4


class FloatPlane(Vehicle):

    VEHICLE_TYPE = "Float Plane"

    def __init__(self, top_speed, passenger_count):
        super().__init__(top_speed, passenger_count)

        self.can_eject = False

    def display_info(self):
        super().display_info()
        print(f"Can Eject: {self.can_eject}")


if __name__ == "__main__":

    vehicle = FloatPlane(200, 4)
    vehicle.display_info()

