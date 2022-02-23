import os
import math
from amaranth import *
from amaranth.sim import Simulator, Delay, Settle


# Drive the x,y deflection beams for raster scanning.
# The DAC for the y-deflection is driven directly.
# The x-beam is driven through the parameters of an
# external analog linear ramp generator.
class PWM(Elaboratable):
    def __init__(self, period_clock_cyles = 2**16):
        # Internal params
        self.period_clock_cyles = period_clock_cyles
        self.counter_bits = int(math.log2(period_clock_cyles))
        
        # INPUT: ranges from [0 to period_clock_cyles]
        self.input = Signal(self.counter_bits)
        
        # OUTPUT
        self.pwm = Signal()
        
    def elaborate(self, platform):
        m = Module()

        counter = Signal(self.counter_bits)

        m.d.sync += [
            counter.eq(Mux(counter >= self.period_clock_cyles, 0, counter + 1))
        ]
        
        m.d.comb += [
            self.pwm.eq( counter < self.input )
        ]
               
        return m
   
def sim_PWM_1():
    #  2**16 * 10ns = 655.36us period
    pwm_period_clocks = 2**16
    
    dut = PWM(pwm_period_clocks)
    sim = Simulator(dut)
    sim.add_clock(1.0 / 100e6)

    def loopback_proc():
        yield dut.input.eq( C(round(pwm_period_clocks / 10)) )
        for i in range(0,2**18):
            yield
        
    sim.add_sync_process(loopback_proc)
    
    os.makedirs("sim", exist_ok=True)
    with sim.write_vcd("sim/pwm.vcd"):
        sim.run()
        
if __name__ == "__main__":
    sim_PWM_1()