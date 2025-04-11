import cv2
import numpy as np
from flask import Response
import random

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
