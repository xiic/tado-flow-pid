from datetime import datetime
from PyTado.interface.interface import Tado
from simple_pid import PID

tempOffset = 0.5 # "Disable" Tado control algorithm

class FlowController:
    def __init__(self, name, Kp, Ki, Kd, Kpom, weightPom, fadePom, setpoint, output_limits, starting_output):
        self.name = name
        self.Kp = Kp
        self.Ki = Ki
        self.Kd =Kd
        self.Kpom = Kpom
        self.weightPom = weightPom
        self.fadePom = fadePom
        self.setpoint = setpoint
        self.output_limits = output_limits
        self.starting_output = starting_output

        self.pid = PID(Kp=0.0,
                       Ki=0.03,
                       Kd=0.0,
                       Kpom=10.0,
                       weightPom=0.05,
                       fadePom=0.001,
                       setpoint=setpoint,
                       sample_time=None,
                       output_limits=output_limits,
                       starting_output=starting_output)
        
    def update(self, zoneState):
        target = zoneState['setting']['temperature']['value'] - tempOffset
        current = zoneState['sensorDataPoints']['insideTemperature']['value']

        self.pid.setpoint = target
        new_flow = self.pid(current)

        print(f"{datetime.now().replace(microsecond=0).isoformat()} {self.name} ({current:.2f} {target:.2f}) ({new_flow:.2f}) {self.pid.components}")

        return new_flow

        

