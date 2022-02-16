import os
import functools

from amaranth import *
from amaranth.sim import Simulator

# Module allows us to specify which samples and with what bitdepths
# we will be streaming to the host. We do this by applying user defined
# masks and shifts into a (possibly larger) output Signal
class SampleMux(Elaboratable):
    def __init__(self, output_bits, input_bits_arr) -> None:
        self.output_bits = output_bits
        self.N = len(input_bits_arr)

        # In
        self.input_samples = []
        self.input_mask = []
        self.input_shft = []
        
        for i in range(0, self.N):
            input_bits = input_bits_arr[i]
            self.input_samples.append(Signal(input_bits, name="input{}".format(i) ))
            self.input_mask.append(Signal(input_bits, name="mask{}".format(i) ))
            self.input_shft.append(Signal(8, name="shift{}".format(i) ))

        # Out
        self.output_sample = Signal(output_bits)

    def elaborate(self, platform):
        m = Module()
        
        result = functools.reduce(lambda a,b: a | b, [ (self.input_samples[i] & self.input_mask[i]) << self.input_shft[i] for i in range(self.N)])
        
        m.d.comb += self.output_sample.eq(result)

        return m
    
def sim_samplemux_1():
    dut = SampleMux(16, [12,12,12,12]) 

    sim = Simulator(dut)

    def loopback_proc():
        yield dut.input_samples[0].eq(0x123)
        yield dut.input_samples[1].eq(0x456)
        yield dut.input_samples[2].eq(0x789)
        yield dut.input_samples[3].eq(0x000)
        
        yield dut.input_mask[0].eq(0x000f)
        yield dut.input_mask[1].eq(0x000f)
        yield dut.input_mask[2].eq(0x000f)
        yield dut.input_mask[3].eq(0x000f)
        
        yield dut.input_shft[0].eq(0)
        yield dut.input_shft[1].eq(4)
        yield dut.input_shft[2].eq(8)
        yield dut.input_shft[3].eq(12)        
        
    sim.add_process(loopback_proc)
    
    os.makedirs("sim", exist_ok=True)
    with sim.write_vcd("sim/samplemux_1.vcd"):
        sim.run()
        
if __name__ == "__main__":
    sim_samplemux_1()