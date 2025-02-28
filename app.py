"""Control the tado flowTemperature using PyTado"""

import os
import sys
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from PyTado.interface.interface import Tado
from flowController import FlowController

load_dotenv()

TADO_USERNAME = os.getenv('TADO_USERNAME')
TADO_PASSWORD = os.getenv('TADO_PASSWORD')
FLOW_MIN = float(os.getenv('FLOW_MIN', 20))
FLOW_MAX_MINUS10 = float(os.getenv('FLOW_MAX_MINUS10', 75))
FLOW_MAX_PLUS20 = float(os.getenv('FLOW_MAX_PLUS20', 45))
PARAM_KP = float(os.getenv('PARAM_KP', 0.0))
PARAM_KI = float(os.getenv('PARAM_KI', 0.03))
PARAM_KD = float(os.getenv('PARAM_KD', 0.0))
PARAM_KPOM = float(os.getenv('PARAM_KPOM', 10.0))
PARAM_POM_WEIGHT = float(os.getenv('PARAM_POM_WEIGHT', 0.05))

temperature_offset = 0.5 # "Disable" Tado control algorithm
flow_max_update_interval = timedelta(hours=1)
flow_max = None
flow_max_last_update = datetime.min

if len(TADO_USERNAME) == 0 or len(TADO_PASSWORD) == 0:
    sys.exit("TADO_USERNAME and TADO_PASSWORD must be set")

def main():
    """Retrieve all zones, once successfully logged in"""
    tado = Tado(username=TADO_USERNAME, password=TADO_PASSWORD)
    flow = tado.get_flow_temperature_optimization()['maxFlowTemperature']
    controllers = {}

    while True:
        update_flow_max(tado)
        zoneStates = tado.get_zone_states()

        # Create or update a controller for each zone
        for zone in zoneStates:
            # Only execute for this zone if setting power is not OFF:
            if zone['setting']['power'] == 'OFF':
                continue
            
            setpoint = zone['setting']['temperature']['value'] - temperature_offset
            current = zone['sensorDataPoints']['insideTemperature']['value']
            id = zone['id']
            name = zone['name']

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
        
        time.sleep(60)

def create_new_controller(name, setpoint, flow):
    return FlowController(name = name,
                          Kp = PARAM_KP,
                          Ki = PARAM_KI,
                          Kd = PARAM_KD,
                          Kpom = PARAM_KPOM,
                          weightPom = PARAM_POM_WEIGHT,
                          setpoint = setpoint,
                          output_limits=(FLOW_MIN, flow_max),
                          starting_output=flow)

def update_flow_max(tado):
    global flow_max_last_update
    global flow_max_update_interval
    global flow_max

    # Return if last update was less than an hour ago
    if datetime.now() - flow_max_last_update < flow_max_update_interval:
        return
    
    outsideTemperature = tado.get_weather()['outsideTemperature']['celsius']
    flow_max = _calc_flow_max(outsideTemperature)
    flow_max_last_update = datetime.now()
    print(f"Calculated flow_max: {flow_max}")

def _calc_flow_max(outsideTemperature):
    a_x = -10
    a_y = FLOW_MAX_MINUS10
    b_x = 20
    b_y = FLOW_MAX_PLUS20
    flow = a_y + (b_y - a_y) / (b_x - a_x) * (outsideTemperature - a_x)
    
    if flow < FLOW_MAX_PLUS20:
        return FLOW_MAX_PLUS20
    if flow > FLOW_MAX_MINUS10:
        return FLOW_MAX_MINUS10
    
    return round(flow)

if __name__ == "__main__":
    main()
