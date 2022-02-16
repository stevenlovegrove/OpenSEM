import os
import math
from amaranth import *
from amaranth.sim import Simulator, Delay, Settle


# Drive the x,y deflection beams for raster scanning.
# The DAC for the y-deflection is driven directly.
# The x-beam is driven through the parameters of an
# external analog linear ramp generator.
class LedBar(Elaboratable):
    @staticmethod
    def ispow2(n):
        return (n & (n-1) == 0) and n != 0

    # @staticmethod
    # def programatic_definition(value):        
    #     pass

    def __init__(self, value_bits, bar_width):
        # INPUT
        self.value = Signal(value_bits)
        
        # OUTPUT
        assert self.ispow2(bar_width)
        self.bar = Signal(bar_width)

        ## Value is n bits wide
        self.n = value_bits
        ## We can use k MSB's of value_bits directly
        self.k = int(math.log2(bar_width))
        ## kn is size of bits k to n
        self.kn = self.n - self.k
        
    def elaborate(self, platform):
        m = Module()

        # val_k, the MSB's tell us how many LED's to light fully
        val_k = Signal(self.k)
        # val_kn, the LSB's tell us the PWM duty cycle of the next LED
        val_kn = Signal(self.kn)
        
        counter = Signal(self.kn)
        
        m.d.comb += [
            val_k.eq(self.value >> self.kn), # MSB's
            val_kn.eq(self.value)            # LSB's
        ]
        
        m.d.sync += [
            counter.eq(counter +1)
        ]
        
        for i in range(len(self.bar)):
            with m.If( C(i) == val_k):
                m.d.comb += self.bar[i].eq( counter < val_kn)
            with m.Else():
                m.d.comb += self.bar[i].eq( C(i) < val_k )
               
        return m
   
def sim_LedBar_1():
    dut = LedBar(12, 8)
    sim = Simulator(dut)
    sim.add_clock(1.0 / 100e6)

    def loopback_proc():
        for i in range(0,2**12,2^4):
            yield dut.value.eq(i)
            for k in range(512):
                yield
        
    sim.add_sync_process(loopback_proc)
    
    os.makedirs("sim", exist_ok=True)
    with sim.write_vcd("sim/ledbar_1.vcd"):
        sim.run()
        
if __name__ == "__main__":
    sim_LedBar_1()