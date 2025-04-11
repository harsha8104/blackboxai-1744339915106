import math
import logging

class Camera:
    def __init__(self, camera_id, position, detection_radius):
        """Initialize a camera."""
        self.id = camera_id
        self.position = position
        self.detection_radius = detection_radius
        self.detected_vehicles = []
        self.logger = logging.getLogger('traffic_simulation')

    def detect_vehicles(self, vehicles):
        """Detect vehicles within the camera's detection radius."""
        try:
            self.detected_vehicles = []
            for vehicle in vehicles:
                if self._is_in_range(vehicle['position']):
                    vehicle_data = {
                        'id': vehicle['id'],
                        'position': vehicle['position'],
                        'speed': vehicle['speed'],
                        'edge': vehicle['edge'],
                        'route': vehicle['route'],
                        'type': vehicle['type'],
                        'distance_to_camera': self._calculate_distance(vehicle['position'])
                    }
                    self.detected_vehicles.append(vehicle_data)
        except Exception as e:
            self.logger.error(f"Error in camera {self.id} detection: {str(e)}")

    def _is_in_range(self, vehicle_position):
        """Check if a vehicle is within the camera's detection radius."""
        try:
            distance = self._calculate_distance(vehicle_position)
            return distance <= self.detection_radius
        except Exception as e:
            self.logger.error(f"Error checking vehicle range in camera {self.id}: {str(e)}")
            return False

    def _calculate_distance(self, vehicle_position):
        """Calculate the Euclidean distance between the camera and a vehicle."""
        try:
            x1, y1 = self.position
            x2, y2 = vehicle_position
            return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        except Exception as e:
            self.logger.error(f"Error calculating distance in camera {self.id}: {str(e)}")
            return float('inf')

    def get_vehicle_data(self):
        """Return the list of detected vehicles."""
        return self.detected_vehicles
