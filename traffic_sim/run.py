import os
from traffic_sim.simulation.sim_controller import SimulationController
from traffic_sim.web_interface import app

def main():
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), 'config/simulation_config.yaml')
    
    # Initialize the simulation controller
    sim_controller = SimulationController(config_path)
    
    try:
        # Start the simulation in simulation-only mode (since we're in web environment)
        print("Starting traffic simulation in simulation-only mode...")
        sim_controller.start_simulation()
        
        # Run the Flask app
        print("Starting web interface on port 8000...")
        app.run(host='0.0.0.0', port=8000, debug=True)
        
    except KeyboardInterrupt:
        print("Server interrupted. Closing...")
    finally:
        sim_controller.close()

if __name__ == "__main__":
    main()
