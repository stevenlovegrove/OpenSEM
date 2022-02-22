import os
from amaranth import *
from amaranth.sim import Simulator
from fixed_point import *
import functools

# https://stackoverflow.com/questions/12370379/flat-permutations-of-n-tuple-breadth-first
def seq(n, k):
    if (k == 0):
        yield ()
        return

    for i in range(n+1):
        for subseq in seq(i, k-1):
            for j in range(k):
                yield subseq[:j] + (i,) + subseq[j:]
                if j != k-1 and subseq[j] == i:
                    break

# def ternary_op(cond : Value, case_true: Value, case_false : Value):
#     assert cond.shape().width == 1
#     assert case_true.shape().width == case_false.shape().width
#     assert case_true.shape().signed == case_false.shape().signed 
#     out_bits = case_true.shape().width
#     cond_extend = Repl(cond, out_bits)
#     ret = (cond_extend & case_true) | (~cond_extend & case_false)    
#     assert ret.shape().width == out_bits
#     return ret


def argmin( vals : list ):
    def idx_least(a,b):
        assert a[1].shape().width == b[1].shape().width
        a_less_b = a[1] < b[1]
        # return ( ternary_op(a_less_b, a[0], b[0]), ternary_op(a_less_b, a[1].as_unsigned(), b[1].as_unsigned()).as_signed() )
        return ( Mux(a_less_b, a[0], b[0]), Mux(a_less_b, a[1].as_unsigned(), b[1].as_unsigned()).as_signed() )

    list_idx_bits = C(len(vals)-1).shape().width
    idx_vals = [ (C(idx,list_idx_bits), vals[idx]) for idx in range(len(vals))]
    (idx, _) = functools.reduce( idx_least, idx_vals )
    return idx

# Drive the x,y deflection beams for raster scanning.
# The DAC for the y-deflection is driven directly.
# The x-beam is driven through the parameters of an
# external analog linear ramp generator.
class DAC(Elaboratable):
    def __init__(self,
            delta_time : float,
            capacitor : float,
            resistors : list[float],
            output_pwm
            ):
        # Constants
        self.n = len(resistors)
        self.delta_t_inv_tau = [
            SignalFixedPoint(1, 19, constant= delta_time/(capacitor*R), signed=True ) for R in resistors
        ]
        
        # Output (tristate)
        self.pwm = output_pwm

        # Input : [0,1]
        self.input = SignalFixedPoint(1,19,signed=True)
        self.input.s.name = "input"

        # Estimate of filtered output [0,1]        
        self.v_out = SignalFixedPoint(1,19,signed=True)
        self.v_out.s.reset = self.v_out.to_binary(0.5)
        self.v_out.s.name = "vout"
        
        # possible pwm array states
        self.options = [ Cat([C(y,1) for y in list(x)]) for x in list(seq(1,self.n)) ]
        
    @staticmethod
    def info(name, fixed):
        print(name, fixed.s.shape(), fixed.s.shape().width - fixed.qf, fixed.qf)
        
    def delta_v(self, pwms):
        diffs = [ SignalFixedPoint(value=pwm,frac_bits=0) - self.v_out for pwm in pwms]
        dvs = [self.delta_t_inv_tau[i] * diffs[i] for i in range(self.n)]
        sum = functools.reduce(lambda a, b: a+b, dvs)
        return sum
    
    def elaborate(self, platform):
        m = Module()

        deltas = [ self.delta_v(opt) for opt in self.options]
        outcomes = [ self.v_out + delta for delta in deltas]
        errors = [ abs((o - self.input).s) for o in outcomes]
        
        least_idx = argmin(errors)
        least_pwm = Cat(self.options).word_select(least_idx, self.n )
                
        m.d.sync += [
            self.pwm.eq( least_pwm ),
            self.v_out.eq( self.v_out + self.delta_v(least_pwm)),
        ]
        
        # # debug signals
        # for i in range(len(outcomes)):
        #     s = Signal(outcomes[i].s.shape().width, name="outcome{}".format(i)); m.d.comb += s.eq(outcomes[i].s)
        #     s = Signal(errors[i].shape().width, name="errors{}".format(i)); m.d.comb += s.eq(errors[i])
        
        # v0 = SignalFixedPoint(1,0, constant=0.0)
        # v1 = SignalFixedPoint(1,0, constant=1.0)
        # diff0 = v0 - self.v_out
        # diff1 = v1 - self.v_out
        
        # m.d.sync += [
        #     Signal(2,name="least_idx").eq(least_idx),
        #     Signal(2,name="least_pwm").eq(least_pwm),
        #     Signal(2,name="v0").eq(v0.s),
        #     Signal(2,name="v1").eq(v1.s),            
        #     Signal(40,name="diff0").eq(diff0.s),
        #     Signal(40,name="diff1").eq(diff1.s),            
        # ]
        
        return m
        
        
        
if __name__ == "__main__":
    from sem_board import OpenSemPlatform
    platform = OpenSemPlatform()
    ftdi_resource = platform.request("ft600")
    period = 1.0/100e6
    dut = DAC(delta_time=period, capacitor=1e-7, resistors=[1e2, 1e5])
    sim = Simulator(dut)
    sim.add_clock(period, domain="sync")

    def sync_loop():
        yield dut.input.eq( SignalFixedPoint(8,16,signed=True,constant=0.1))
        yield
        v = yield dut.input.s; print(dut.input.compute_value(v))
        # v = yield dut.delta_t_inv_tau[0].s; print(dut.delta_t_inv_tau[0].compute_value(v))
        # v = yield dut.delta_t_inv_tau[1].s; print(dut.delta_t_inv_tau[1].compute_value(v))
        print()
        
        
        for i in range(20):
            v = yield dut.v_out.s; print(dut.v_out.compute_value(v))
            yield
        
        for i in range(1000):
            yield
        
    sim.add_sync_process(sync_loop, domain="sync")
    
    os.makedirs("sim", exist_ok=True)
    with sim.write_vcd("sim/dac.vcd"):
        sim.run()
