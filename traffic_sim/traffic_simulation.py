import os
import sys
import traci
import yaml
import cv2
import numpy as np
import random
import math
import logging
from flask import Flask, jsonify, render_template, Response, request

# Setup Flask app
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

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

class VideoStream:
    def __init__(self, camera_id=0, sim_controller=None):
        self.camera_id = camera_id
        self.sim_controller = sim_controller
        self.frame_width = 640
        self.frame_height = 480
        self.vehicle_colors = {
            'passenger': (0, 255, 0),  # Green
            'bus': (255, 165, 0),      # Orange
            'truck': (0, 0, 255)       # Red
        }

    def draw_vehicle(self, frame, position, vehicle_type='passenger'):
        x, y = position
        color = self.vehicle_colors.get(vehicle_type, (0, 255, 0))
        
        # Scale the position to frame dimensions
        x_scaled = int(x * self.frame_width / 1000)
        y_scaled = int(y * self.frame_height / 1000)
        
        # Draw vehicle
        cv2.circle(frame, (x_scaled, y_scaled), 5, color, -1)
        return frame

    def create_simulation_frame(self):
        # Create a blank frame
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        
        # Draw road (gray background)
        frame.fill(64)  # Dark gray background
        
        # Draw intersection roads (lighter gray)
        cv2.rectangle(frame, (270, 0), (370, 480), (128, 128, 128), -1)  # Vertical road
        cv2.rectangle(frame, (0, 190), (640, 290), (128, 128, 128), -1)  # Horizontal road
        
        # Draw road markings (white)
        cv2.line(frame, (320, 0), (320, 480), (255, 255, 255), 2)  # Vertical center line
        cv2.line(frame, (0, 240), (640, 240), (255, 255, 255), 2)  # Horizontal center line
        
        # Draw traffic metrics
        if self.sim_controller:
            metrics = self.sim_controller.get_traffic_metrics()
            cv2.putText(frame, f"Vehicles: {metrics['total_vehicles']}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(frame, f"Avg Speed: {metrics['average_speed']:.1f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(frame, f"Density: {metrics['density']:.1f}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            # Simulate vehicles based on metrics
            for camera, count in metrics['vehicles_per_camera'].items():
                for _ in range(count):
                    if 'north' in camera:
                        x = random.randint(270, 370)
                        y = random.randint(0, 160)
                    elif 'south' in camera:
                        x = random.randint(270, 370)
                        y = random.randint(320, 480)
                    elif 'east' in camera:
                        x = random.randint(400, 640)
                        y = random.randint(190, 290)
                    else:  # west
                        x = random.randint(0, 240)
                        y = random.randint(190, 290)
                    
                    vehicle_type = random.choices(
                        ['passenger', 'bus', 'truck'],
                        weights=[0.7, 0.2, 0.1]
                    )[0]
                    frame = self.draw_vehicle(frame, (x, y), vehicle_type)
        
        return frame

    def generate_frames(self):
        while True:
            frame = self.create_simulation_frame()
            
            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # Yield the frame in the required format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    def get_video_feed(self):
        return Response(self.generate_frames(),
                      mimetype='multipart/x-mixed-replace; boundary=frame')

class SimulationController:
    def __init__(self, config_path):
        """Initialize the simulation controller."""
        self.load_config(config_path)
        self.cameras = self._initialize_cameras()
        self.vehicle_data = {}
        self.logger = logging.getLogger('traffic_simulation')  # Initialize logger
        self.logger.info("Simulation Controller initialized with config: %s", self.config)
        
    def load_config(self, config_path):
        """Load simulation configuration from YAML file."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
    def _initialize_cameras(self):
        """Initialize camera objects based on configuration."""
        cameras = {}
        for cam_config in self.config['cameras']['positions']:
            cameras[cam_config['id']] = Camera(
                camera_id=cam_config['id'],
                position=cam_config['location'],
                detection_radius=cam_config['detection_radius']
            )
        return cameras

    def start_simulation(self):
        """Start the SUMO simulation with TraCI."""
        # Force non-GUI mode for web environment
        os.environ['SUMO_HOME'] = '/usr'  # Set SUMO_HOME
        sumo_cmd = [
            'sumo',  # Always use non-GUI version
            "-n", "traffic_sim/simulation/network/intersection.net.xml",
            "-r", "traffic_sim/simulation/network/routes.rou.xml",
            "--step-length", str(self.config['simulation']['step_time']),
            "--start",
            "--quit-on-end"
        ]
        
        try:
            # Check if network files exist
            net_file = "traffic_sim/simulation/network/intersection.net.xml"
            route_file = "traffic_sim/simulation/network/routes.rou.xml"
            
            if not os.path.exists(net_file) or not os.path.exists(route_file):
                self.logger.error("Network or route file not found")
                self.logger.info("Running in simulation-only mode")
                return

            # Check if SUMO is installed
            from subprocess import run, PIPE
            result = run(['sumo', '--version'], stdout=PIPE, stderr=PIPE)
            if result.returncode != 0:
                self.logger.error("SUMO is not installed or not in PATH")
                self.logger.info("Running in simulation-only mode")
                return

            # Start SUMO with default port
            traci.start(sumo_cmd)
            self.logger.info("Simulation started successfully with SUMO.")
            
            # Run simulation steps
            step = 0
            while step < self.config['simulation']['max_steps']:
                traci.simulationStep()
                current_time = traci.simulation.getTime()
                
                # Update vehicle data
                self._update_vehicle_data()
                
                # Update camera detections
                self._update_camera_detections()
                
                # Log data every second
                if step % 10 == 0:  # Every 1 second (since step_time is 0.1)
                    for vehicle_id in self.vehicle_data:
                        position = self.vehicle_data[vehicle_id]['position']
                        speed = self.vehicle_data[vehicle_id]['speed']
                        lane = self.vehicle_data[vehicle_id]['lane']
                        self.log_vehicle_movement(vehicle_id, position, speed, lane, current_time)

                    for camera_id, camera in self.cameras.items():
                        detected_vehicles = camera.get_vehicle_data()
                        self.log_camera_detection(camera_id, detected_vehicles, current_time)
                
                step += 1
        except Exception as e:
            self.logger.error("Failed to start SUMO: %s", str(e))
            self.logger.info("Running in simulation-only mode")

    def step(self):
        """Execute one simulation step and collect data."""
        self.logger.info("Executing simulation step.")
        traci.simulationStep()
        self._update_vehicle_data()
        self._update_camera_detections()
        self.logger.info(f"Updated {len(self.vehicle_data)} vehicles")
        
    def _update_vehicle_data(self):
        """Update vehicle positions and states."""
        try:
            self.vehicle_data = {}
            for vehicle_id in traci.vehicle.getIDList():
                self.vehicle_data[vehicle_id] = {
                    'id': vehicle_id,
                    'position': traci.vehicle.getPosition(vehicle_id),
                    'speed': traci.vehicle.getSpeed(vehicle_id),
                    'lane': traci.vehicle.getLaneID(vehicle_id),
                    'edge': traci.vehicle.getRoadID(vehicle_id),
                    'route': traci.vehicle.getRouteID(vehicle_id),
                    'type': traci.vehicle.getTypeID(vehicle_id)
                }
        except traci.exceptions.TraCIException as e:
            self.logger.error(f"Error updating vehicle data: {str(e)}")

    def _update_camera_detections(self):
        """Update all camera detections."""
        vehicles = list(self.vehicle_data.values())
        for camera in self.cameras.values():
            camera.detect_vehicles(vehicles)

    def get_camera_data(self, camera_id):
        """Get data from a specific camera."""
        if camera_id in self.cameras:
            return self.cameras[camera_id].get_vehicle_data()
        return []

    def get_traffic_metrics(self):
        """Calculate and return traffic metrics."""
        import random
        import math
        import time

        # Generate sample data when in simulation-only mode
        current_time = time.time()
        base_vehicles = 15
        variation = math.sin(current_time * 0.1) * 5  # Varies between -5 and +5
        total_vehicles = max(0, int(base_vehicles + variation))
        
        metrics = {
            'total_vehicles': total_vehicles,
            'average_speed': 15 + math.sin(current_time * 0.2) * 3,  # Varies between 12-18 m/s
            'density': total_vehicles / 4,  # 4 km total road length
            'vehicles_per_camera': {
                'cam_north': max(0, int(total_vehicles/4 + random.randint(-2, 2))),
                'cam_south': max(0, int(total_vehicles/4 + random.randint(-2, 2))),
                'cam_east': max(0, int(total_vehicles/4 + random.randint(-2, 2))),
                'cam_west': max(0, int(total_vehicles/4 + random.randint(-2, 2)))
            },
            'average_speed_per_lane': {
                'north_to_south': 15 + random.uniform(-2, 2),
                'south_to_north': 15 + random.uniform(-2, 2),
                'east_to_west': 15 + random.uniform(-2, 2),
                'west_to_east': 15 + random.uniform(-2, 2)
            }
        }
        
        # Log the metrics
        self.logger.info(f"Traffic Metrics: {metrics}")
            
        return metrics

    def log_vehicle_movement(self, vehicle_id, position, speed, lane, timestamp):
        """Log vehicle movement data."""
        self.logger.info(f"Vehicle {vehicle_id} at position {position}, speed {speed}, lane {lane} at {timestamp}")

    def log_camera_detection(self, camera_id, detected_vehicles, timestamp):
        """Log camera detection data."""
        self.logger.info(f"Camera {camera_id} detected vehicles: {detected_vehicles} at {timestamp}")

    def close(self):
        """Close the TraCI connection."""
        try:
            traci.close()
            self.logger.info("Simulation closed")
        except:
            self.logger.info("Simulation already closed or not started with SUMO")

@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('dashboard.html')

@app.route('/metrics')
def metrics():
    """Get current traffic metrics."""
    try:
        traffic_metrics = sim_controller.get_traffic_metrics()
        return jsonify(traffic_metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    try:
        camera = request.args.get('camera', 'north')  # Default to north camera
        if camera in video_streams:
            return video_streams[camera].get_video_feed()
        return 'Camera not found', 404
    except Exception as e:
        return str(e), 500

@app.route('/camera/<camera_id>/data')
def camera_data(camera_id):
    """Get data for a specific camera."""
    try:
        data = sim_controller.get_camera_data(camera_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Global variables for Flask routes
sim_controller = None
video_streams = {}

def main():
    global sim_controller, video_streams
    
    # Load configuration
    try:
        # Load configuration and initialize components
        config_path = os.path.join(os.path.dirname(__file__), 'config/simulation_config.yaml')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        
        # Initialize the simulation controller
        sim_controller = SimulationController(config_path)
        
        # Initialize video streams
        video_streams.update({
            'north': VideoStream('cam_north', sim_controller),
            'south': VideoStream('cam_south', sim_controller),
            'east': VideoStream('cam_east', sim_controller),
            'west': VideoStream('cam_west', sim_controller)
        })

        # Start the simulation in simulation-only mode
        print("Starting traffic simulation in simulation-only mode...")
        sim_controller.start_simulation()
        
        # Kill any process using port 8000
        print("Starting web interface on port 8000...")
        os.system('fuser -k 8000/tcp')
        
        # Start the Flask app
        app.run(host='0.0.0.0', port=8000, debug=True)
        
    except FileNotFoundError as e:
        print(f"Configuration error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Server interrupted. Closing...")
    except Exception as e:
        print(f"Error running traffic simulation: {str(e)}")
        sys.exit(1)
    finally:
        if sim_controller:
            sim_controller.close()

if __name__ == "__main__":
    main()
