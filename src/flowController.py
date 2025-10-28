from datetime import datetime
from PyTado.interface.interface import Tado
from simple_pid import PID

class FlowController:
    def __init__(self, name, Kp, Ki, Kd, Kpom, weightPom, fadePom, setpoint, output_limits, starting_output):
        self.name = name
        self.output = starting_output
        self.pid = PID(Kp=Kp,
                       Ki=Ki,
                       Kd=Kd,
                       Kpom=Kpom,
                       weightPom=weightPom,
                       fadePom=fadePom,
                       setpoint=setpoint,
                       sample_time=None,
                       output_limits=output_limits,
                       starting_output=starting_output)
        
    def update(self, setpoint, current):
        self.pid.setpoint = setpoint
        self.current = current
        self.output = self.pid(current)
    
    def set_output_limits(self, output_limits):
        self.pid.output_limits = output_limits
    
    def __repr__(self):
        components = self.pid.components
        p = components[0]
        i = components[1]
        d = components[2]
        pom = components[3]

        return f"{self.name} {self.current:.2f} {self.pid.setpoint:.2f} {self.output:.2f} [{p:.2f} {i:.2f} {d:.2f} {pom:.2f}]"

        

