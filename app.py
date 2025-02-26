"""Control the tado flowTemperature using PyTado"""

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from PyTado.interface.interface import Tado
from flowController import FlowController

load_dotenv()

TADO_USERNAME = os.getenv('TADO_USERNAME')
TADO_PASSWORD = os.getenv('TADO_PASSWORD')
FLOW_MIN = 20
FLOW_MAX_MINUS10 = 70
FLOW_MAX_PLUS20 = 45

if len(TADO_USERNAME) == 0 or len(TADO_PASSWORD) == 0:
    sys.exit("TADO_USERNAME and TADO_PASSWORD must be set")

def main():
    """Retrieve all zones, once successfully logged in"""
    tado = Tado(username=TADO_USERNAME, password=TADO_PASSWORD)
    flow = tado.get_flow_temperature_optimization()['maxFlowTemperature']
    flow_max = 60 # TODO: calculate

    zoneStates = tado.get_zone_states() # TODO: Do not execute twice on startup
    z0 = zoneStates[0]
    print(z0)
    z1 = zoneStates[1]
    pid0 = FlowController(name = z0['name'],
                          Kp=0.0,
                          Ki=0.03,
                          Kd=0.0,
                          Kpom=10.0,
                          weightPom=0.05,
                          fadePom=0.001,
                          setpoint=z0['setting']['temperature']['value'],
                          output_limits=(FLOW_MIN, flow_max),
                          starting_output=flow)
    pid1 = FlowController(name = z1['name'],
                          Kp=0.0,
                          Ki=0.03,
                          Kd=0.0,
                          Kpom=10.0,
                          weightPom=0.05,
                          fadePom=0.001,
                          setpoint=z1['setting']['temperature']['value'],
                          output_limits=(FLOW_MIN, flow_max),
                          starting_output=flow)

    while True:
        zoneStates = tado.get_zone_states()

        p0Flow = pid0.update(zoneStates[0])
        p1Flow = pid1.update(zoneStates[1])

        new_flow = max(p0Flow, p1Flow)
        new_flow_rounded = round(new_flow)

        if new_flow_rounded != flow:
            print(f"Setting flow to: {new_flow_rounded}")
            tado.set_flow_temperature_optimization(new_flow_rounded)
            flow = new_flow_rounded
        
        time.sleep(60)

if __name__ == "__main__":
    main()
