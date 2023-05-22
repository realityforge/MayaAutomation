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



if __name__ == "__main__":

    vehicle = Vehicle(50, 4)
    vehicle.display_info()
