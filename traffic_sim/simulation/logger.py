import logging

def setup_logger(log_level=logging.INFO):
    """Set up the logger for the simulation."""
    logger = logging.getLogger('traffic_simulation')
    
    # Only add handler if the logger doesn't already have handlers
    if not logger.handlers:
        logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger  # Ensure the logger is returned

def log_vehicle_movement(vehicle_id, position, speed, lane, timestamp):
    """Log vehicle movement details."""
    logger = setup_logger()
    logger.info(f"Vehicle {vehicle_id} moved to position {position} with speed {speed}, lane {lane} at time {timestamp}.")

def log_camera_detection(camera_id, detected_vehicles, timestamp):
    """Log camera detection details."""
    logger = setup_logger()
    logger.info(f"Camera {camera_id} detected vehicles: {detected_vehicles} at time {timestamp}.")

def log_warning(message):
    """Log a warning message."""
    logger = setup_logger()
    logger.warning(message)
