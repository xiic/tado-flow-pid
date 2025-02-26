"""Control the tado flowTemperature using PyTado"""

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from PyTado.interface.interface import Tado
from simple_pid import PID

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
    pid = None

    while True:
        zoneState = tado.get_zone_state(1)
        current = zoneState.current_temp
        target = zoneState.target_temp - 0.5 # "Disable" Tado control algorithm
        flow = tado.get_flow_temperature_optimization()['maxFlowTemperature']
        flow_max = 60 # todo: calculate

        # If proportional_on_measurement=True:
        #   Increase Kp to reduce overshooting
        #   Increase Ki to speed up base value change (look at 'I' component in log for base value)
        #   Kd - probably not needed, and for values < 1000 it should not affect the output by much anyway
        if pid is None:
            pid = PID(Kp=0.0,
                      Ki=0.03,
                      Kd=0.0,
                      Kpom=10.0,
                      weightPom=0.05,
                      fadePom=0.001,
                      setpoint=target,
                      sample_time=None,
                      output_limits=(FLOW_MIN, flow_max),
                      starting_output=flow)

        pid.setpoint = target
        new_flow = pid(current)
        new_flow_rounded = round(new_flow)
        # new_flow = new_flowp * (flow_max - flow_min) + flow_min

        print(f"{datetime.now().replace(microsecond=0).isoformat()} ({current:.2f} {target:.2f}) ({flow} {new_flow:.2f} {new_flow_rounded}) {pid.components}")

        if new_flow_rounded != flow:
            tado.set_flow_temperature_optimization(new_flow_rounded)

        time.sleep(60)

if __name__ == "__main__":
    main()
