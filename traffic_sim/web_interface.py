from flask import Flask, jsonify, render_template, Response, request
from traffic_sim.simulation.sim_controller import SimulationController
from traffic_sim.simulation.video_stream import VideoStream
import os

app = Flask(__name__)

# Load configuration and initialize the simulation controller
config_path = os.path.join(os.path.dirname(__file__), 'config/simulation_config.yaml')
sim_controller = SimulationController(config_path)

# Initialize video streams for each camera
video_streams = {
    'north': VideoStream('cam_north', sim_controller),
    'south': VideoStream('cam_south', sim_controller),
    'east': VideoStream('cam_east', sim_controller),
    'west': VideoStream('cam_west', sim_controller)
}

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

if __name__ == "__main__":
    # Start the simulation
    sim_controller.start_simulation()
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=8000)
