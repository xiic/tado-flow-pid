"""Control the tado flowTemperature using PyTado"""

import os
import sys
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from PyTado.interface.interface import Tado, API
from PyTado.http import DeviceActivationStatus
from flowController import FlowController

load_dotenv()

FLOW_MIN = float(os.getenv('FLOW_MIN', 20))
FLOW_MAX_MINUS10 = float(os.getenv('FLOW_MAX_MINUS10', 75))
FLOW_MAX_PLUS20 = float(os.getenv('FLOW_MAX_PLUS20', 45))
PARAM_KP = float(os.getenv('PARAM_KP', 0.0))
PARAM_KI = float(os.getenv('PARAM_KI', 0.02))
PARAM_KD = float(os.getenv('PARAM_KD', 0.0))
PARAM_KPOM = float(os.getenv('PARAM_KPOM', 10.0))
PARAM_POM_WEIGHT = float(os.getenv('PARAM_POM_WEIGHT', 0.05))
PARAM_POM_FADE = float(os.getenv('PARAM_POM_FADE', 0.001))

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

    tado.set_flow_temperature_optimization(31)

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
                if zone_data.setting.power == 'OFF':
                    setpoint = frost_protection
                else:
                    setpoint = zone_data.setting.temperature.value - temperature_offset
                
                current = zone_data.sensor_data_points.inside_temperature.value
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
            print(" | ".join([str(controller) for controller in controllers.values()]))

            # Update flow temperature optimization if necessary
            if max_output_rounded != flow:
                print(f"Setting flow to: {max_output_rounded}")
                tado.set_flow_temperature_optimization(max_output_rounded)
                flow = max_output_rounded

            time.sleep(90) # sleep 90s (more frequent updates might cause issues)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(600)

def tado_auth(tado: Tado):
    if (tado.device_activation_status() == DeviceActivationStatus.COMPLETED):
        print('Already activated.')
        return
    
    if (tado.device_activation_status() == DeviceActivationStatus.NOT_STARTED):
        tado_wait_activation_start(tado)
    
    if (tado.device_activation_status() == DeviceActivationStatus.PENDING):
        print(f'Activation pending, please verify: {tado.device_verification_url()}')
        tado.device_activation() # Wait for activation
    
    if (tado.device_activation_status() != DeviceActivationStatus.COMPLETED):
        raise 'Device activation failed'

    print('_refresh_token' + tado._http._token_refresh)

    print('Activation completed.')

def tado_wait_activation_start(tado: Tado):
    while (tado.device_activation_status() == DeviceActivationStatus.NOT_STARTED):
        # Should never occur (at least if a fast internet connection is present)
        print('Activation not started yet, retrying in 30s...')
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
    
    print(f"Calculated flow max: {flow}")
    return round(flow)

if __name__ == "__main__":
    main()
