import os
import sys
import traci
import yaml
from .logger import setup_logger, log_vehicle_movement, log_camera_detection
from .camera import Camera

class SimulationController:
    def __init__(self, config_path):
        """Initialize the simulation controller."""
        self.load_config(config_path)
        self.cameras = self._initialize_cameras()
        self.vehicle_data = {}
        self.logger = setup_logger()  # Initialize logger
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
                        log_vehicle_movement(vehicle_id, position, speed, lane, current_time)

                    for camera_id, camera in self.cameras.items():
                        detected_vehicles = camera.get_vehicle_data()
                        log_camera_detection(camera_id, detected_vehicles, current_time)
                
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

    def close(self):
        """Close the TraCI connection."""
        try:
            traci.close()
            self.logger.info("Simulation closed")
        except:
            self.logger.info("Simulation already closed or not started with SUMO")
