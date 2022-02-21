import os
from amaranth import *
from amaranth.sim import Simulator
from fixed_point import *

# Drive the x,y deflection beams for raster scanning.
# The DAC for the y-deflection is driven directly.
# The x-beam is driven through the parameters of an
# external analog linear ramp generator.
class DAC(Elaboratable):
    def __init__(self,
            delta_time : float,
            capacitor : float,
            resistors : list[float],
            ):
        # Constants
        self.n = len(resistors)
        self.max_voltage = Repl(C(1), self.bits)
        self.delta_t_inv_tau = [
            SignalFixedPoint(0, 20, delta_time / (capacitor*R) ) for R in resistors
        ]
        
        # Output (tristate)
        self.pwm = Signal(self.n)
        # self.out = Signal(self.n)

        # Input : [0,1]
        self.input = SignalFixedPoint(0,16)

        # Estimate of filtered output [0,1]        
        self.v_out = SignalFixedPoint(0,16)
        
    def delta_v(self, pwms):
        dvs = [self.delta_t_inv_tau[i].mul( pwms[i] - self.v_out) for i in range(self.n)]
        
        sum = Signal(self.bits)
    
    def elaborate(self, platform):
        m = Module()
        return m
        
        
        
if __name__ == "__main__":
    delta_time = 1.0 / 100e6
    capacitor = 1e-7
    resistor = 1e3
    fps = SignalFixedPoint(0, 15, delta_time / (capacitor*resistor) )
    print(fps.s)
    pass