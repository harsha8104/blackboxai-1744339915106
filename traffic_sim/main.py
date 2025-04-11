import os
import sys
from traffic_sim.simulation.sim_controller import SimulationController

def main():
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), 'config/simulation_config.yaml')
    
    # Initialize the simulation controller
    sim_controller = SimulationController(config_path)
    
    try:
        # Start the simulation
        sim_controller.start_simulation()
        
        # Generate some sample metrics for simulation-only mode
        metrics = {
            'total_vehicles': 10,
            'average_speed': 15.5,
            'density': 2.5,
            'vehicles_per_camera': {
                'cam_north': 3,
                'cam_south': 2,
                'cam_east': 2,
                'cam_west': 3
            },
            'average_speed_per_lane': {
                'north_to_south': 16.2,
                'south_to_north': 14.8,
                'east_to_west': 15.1,
                'west_to_east': 15.9
            }
        }
        
        # Print formatted metrics
        print("\nTraffic Metrics Summary:")
        print(f"Total Vehicles: {metrics['total_vehicles']}")
        print(f"Average Speed: {metrics['average_speed']:.2f} m/s")
        print(f"Network Density: {metrics['density']:.2f} vehicles/km")
        
        print("\nVehicles per Camera:")
        for camera_id, count in metrics['vehicles_per_camera'].items():
            print(f"  {camera_id}: {count} vehicles")
        
        print("\nAverage Speed per Lane:")
        for lane_id, speed in metrics['average_speed_per_lane'].items():
            print(f"  {lane_id}: {speed:.2f} m/s")
            
    except KeyboardInterrupt:
        print("Simulation interrupted. Closing...")
    finally:
        sim_controller.close()

if __name__ == "__main__":
    main()
