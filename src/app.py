"""Control the tado flowTemperature using PyTado"""

import os
import logging
import sys
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from PyTado.interface.interface import Tado
from PyTado.http import DeviceActivationStatus
from PyTado.models.pre_line_x import ZoneState
from PyTado.models.line_x import RoomState
from flowController import FlowController

load_dotenv()

# Configure logging level from environment variable
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level_value = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=log_level_value,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

FLOW_MIN = float(os.getenv('FLOW_MIN', 20))
FLOW_MAX_MINUS10 = float(os.getenv('FLOW_MAX_MINUS10', 70))
FLOW_MAX_PLUS20 = float(os.getenv('FLOW_MAX_PLUS20', 40))
PARAM_KP = float(os.getenv('PARAM_KP', 0.0))
PARAM_KI = float(os.getenv('PARAM_KI', 0.02))
PARAM_KD = float(os.getenv('PARAM_KD', 0.0))
PARAM_KPOM = float(os.getenv('PARAM_KPOM', 6.0))
PARAM_POM_WEIGHT = float(os.getenv('PARAM_POM_WEIGHT', 0.04))
PARAM_POM_FADE = float(os.getenv('PARAM_POM_FADE', 0.004))

temperature_offset = 0.5 # "Disable" Tado control algorithm
frost_protection = 5.0 # Minimum temperature to prevent frost
flow_max_update_interval = timedelta(hours=1)
flow_max_last_update = datetime.min
flow_max = None

token_file_path = './data/refresh_token'

def main():
    """Adjust the flow temperature to control the room temperature"""
    global flow_max
    
    tado = Tado(token_file_path)  
    tado_auth(tado)

    flow = tado.get_flow_temperature_optimization().max_flow_temperature
    controllers = {}

    while True:
        try:
            # If flow_max_new is different from flow_max, update output limits for all controllers
            flow_max_new = get_flow_max(tado)
            if flow_max_new != flow_max:
                flow_max = flow_max_new
                for controller in controllers.values():
                    controller.set_output_limits((FLOW_MIN, flow_max))
            
            # Get all zone states
            zoneStates = tado.get_zone_states()

            # Create or update a controller for each zone
            for zone_id, zone_data in zoneStates.items():
                logger.debug(f"zone_data for zone {zone_id}: {zone_data}")

                # Skip if no inside temperature data
                if not hasattr(zone_data, 'sensor_data_points') or zone_data.sensor_data_points.inside_temperature is None:
                    logger.debug(f"Skipping zone {zone_id} (no inside_temperature)")
                    continue

                if isinstance(zone_data, ZoneState):
                    # Create a ZoneState object for pre-line X
                    zone_data_prex: ZoneState = zone_data
                    current = zone_data_prex.sensor_data_points.inside_temperature.celsius
                    if zone_data_prex.setting.power == 'OFF':
                        setpoint = frost_protection
                    else:
                        setpoint = zone_data_prex.setting.temperature.celsius - temperature_offset
                elif isinstance(zone_data, RoomState):
                    # Create a RoomState object for line X
                    zone_data_linex: RoomState = zone_data
                    current = zone_data_linex.sensor_data_points.inside_temperature.value
                    if zone_data_linex.setting.power == 'OFF':
                        setpoint = frost_protection
                    else:
                        setpoint = zone_data_linex.setting.temperature.value - temperature_offset
                else:
                    logger.warning(f"Unknown zone data type: {type(zone_data).__name__}")
                    setpoint = frost_protection
                
                id = zone_data.id
                name = zone_data.name

                # Initialize controller in controllers identified by id if it does not exist
                if id not in controllers:
                    controllers[id] = create_new_controller(name, setpoint, flow)
                
                controllers[id].update(setpoint, current)
            
            # Get maximum controller output for all controllers
            max_output = max([controller.output for controller in controllers.values()])
            max_output_rounded = round(max_output)

            # Print representation of all controllers in one line concatenated with |
            logger.info(" | ".join([str(controller) for controller in controllers.values()]))

            # Update flow temperature optimization if necessary
            if max_output_rounded != flow:
                logger.info(f"Setting flow to: {max_output_rounded}")
                tado.set_flow_temperature_optimization(max_output_rounded)
                flow = max_output_rounded

            time.sleep(90) # sleep 90s (more frequent updates might cause issues)
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(600)

def tado_auth(tado: Tado):
    if (tado.device_activation_status() == DeviceActivationStatus.COMPLETED):
        logger.info('Already activated.')
        return
    
    if (tado.device_activation_status() == DeviceActivationStatus.NOT_STARTED):
        logger.info('Starting tado activation...')
        tado_wait_activation_start(tado)
    
    if (tado.device_activation_status() == DeviceActivationStatus.PENDING):
        logger.info(f'Activation pending, please verify: {tado.device_verification_url()}')
        tado.device_activation() # Wait for activation
    
    if (tado.device_activation_status() != DeviceActivationStatus.COMPLETED):
        raise 'Device activation failed'

    logger.info('Activation completed.')

def tado_wait_activation_start(tado: Tado):
    while (tado.device_activation_status() == DeviceActivationStatus.NOT_STARTED):
        # Should never occur (at least if a fast internet connection is present)
        logger.warning('Activation not started yet (device activation might have been revoked - please reset data)')
        time.sleep(30)

def create_new_controller(name, setpoint, flow):
    global flow_max

    return FlowController(name = name,
                          Kp = PARAM_KP,
                          Ki = PARAM_KI,
                          Kd = PARAM_KD,
                          Kpom = PARAM_KPOM,
                          weightPom = PARAM_POM_WEIGHT,
                          fadePom= PARAM_POM_FADE,
                          setpoint = setpoint,
                          output_limits=(FLOW_MIN, flow_max),
                          starting_output=flow)

def get_flow_max(tado):
    """Return the flow max based on the outside temperature, updated once an hour"""
    global flow_max
    global flow_max_last_update
    global flow_max_update_interval

    # Return if last update was less than an hour ago
    if datetime.now() - flow_max_last_update < flow_max_update_interval:
        return flow_max
    
    flow_max_last_update = datetime.now()
    outsideTemperature = tado.get_weather().outside_temperature.celsius

    a_x = -10
    a_y = FLOW_MAX_MINUS10
    b_x = 20
    b_y = FLOW_MAX_PLUS20
    flow = a_y + (b_y - a_y) / (b_x - a_x) * (outsideTemperature - a_x)
    
    if flow < FLOW_MAX_PLUS20:
        return FLOW_MAX_PLUS20
    if flow > FLOW_MAX_MINUS10:
        return FLOW_MAX_MINUS10
    
    logger.info(f"Calculated flow max: {flow}")
    return round(flow)

if __name__ == "__main__":
    main()
