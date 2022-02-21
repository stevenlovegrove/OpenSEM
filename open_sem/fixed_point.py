from argparse import ArgumentError
from amaranth import *
from amaranth.sim import *

# Example of multiplication with truncation of fractional LSB's
# m = module()
# a = SignedFixedPoint(8,2)
# b = SignedFixedPoint(2,8)
# c = SignedFixedPoint(10,2)
# m.d.comb += [
#    c.eq(a.mul(b))
# ]

class SignalFixedPoint:
    class OpResult:
        def __init__(self, s, frac_bits):
            self.s = s
            self.qf = frac_bits
            
    # int_bits / frac_bits can also be negative to shift decimal outside of represented digits
    def __init__(self, int_bits, frac_bits, value=None, signed=None):
        self.qi = int_bits
        self.qf = frac_bits
        self.bits = self.qi + self.qf
        if value is None:
            if signed is None:
                signed = False
            self.s = Signal(Shape(self.bits, signed))
        elif type(value) is float:
            if signed is None:
                signed = value < 0
            elif signed == False and value < 0:
                raise ArgumentError(signed, "Specified unsigned type for signed constant") 
            v_int = round(value / self.lsb_value())
            self.s = C(v_int, Shape(self.bits, signed))
        pass
    
    def __mul__(self, rhs):
        if isinstance(rhs, SignalFixedPoint):
            # result of mul would have:
            #   self.qi + rhs.qi integer bits
            #   self.qf + rhs.qf frac bits
            return self.OpResult(self.s * rhs.s, self.qf + rhs.qf)
        elif isinstance(rhs, Value):
            return self.OpResult(self.s * rhs, self.qf)
        else:
            raise ArgumentError("rhs not valid type")
    
    def __rmul__(self, rhs):
        # Commutative
        return self.__mul__(rhs)
    
    def __add__(self, rhs):
        if isinstance(rhs, SignalFixedPoint):
            self_extra_qf = self.qf - rhs.qf
            if self_extra_qf >= 0:
                return self.OpResult( self.s + (rhs.s.shift_left(self_extra_qf)), self.qf)
            else:
                return self.OpResult( rhs.s + (self.s.shift_left(-self_extra_qf)), rhs.qf)
        elif isinstance(rhs, Value):
            self_extra_qf = self.qf - 0
            if self_extra_qf >= 0:
                return self.OpResult( self.s + (rhs.shift_left(self_extra_qf)), self.qf)
            else:
                return self.OpResult( rhs + (self.s.shift_left(-self_extra_qf)), 0)
        else:
            raise ArgumentError("rhs not valid type")

    def __radd__(self, rhs):
        # Commutative
        return self.__add__(rhs)
    
    def __sub__(self, rhs):
        if isinstance(rhs, SignalFixedPoint):
            self_extra_qf = self.qf - rhs.qf
            if self_extra_qf >= 0:
                return self.OpResult( self.s - (rhs.s.shift_left(self_extra_qf)), self.qf)
            else:
                return self.OpResult( rhs.s - (self.s.shift_left(-self_extra_qf)), rhs.qf)
        elif isinstance(rhs, Value):
            self_extra_qf = self.qf - 0
            if self_extra_qf >= 0:
                return self.OpResult( self.s - (rhs.shift_left(self_extra_qf)), self.qf)
            else:
                return self.OpResult( rhs - (self.s.shift_left(-self_extra_qf)), 0)
        else:
            raise ArgumentError("rhs not valid type")
    
    def eq(self, rhs : OpResult ):
        self_extra_qf = self.qf - rhs.qf
        return self.s.eq( rhs.s.shift_left(self_extra_qf) )

    def lsb_value(self):
        return 1.0 / 2**self.qf

    # Internal integer representation
    def value(self):
        return self.value_rep() * self.lsb_value()
    
    def compute_value(self, s):
        return s * self.lsb_value()
    
    # Internal integer representation
    def value_rep(self):
        return self.s.value
    
def do_sim():
    class TopTest(Elaboratable):
        def __init__(self):
            self.a = SignalFixedPoint(0,20, value = 0.3)
            self.b = SignalFixedPoint(3,16, value = 4.4)
            self.c = SignalFixedPoint(8,8, value = -5.2)
            self.d = C(9)
            
            self.o1 = SignalFixedPoint(16,16, signed=True)
            self.o2 = SignalFixedPoint(16,16, signed=True)
            self.o3 = SignalFixedPoint(16,16, signed=True)
            self.o4 = SignalFixedPoint(16,16, signed=True)
            self.o5 = SignalFixedPoint(16,16, signed=True)
        
        def elaborate(self, platform):
            m = Module()
                
            m.d.sync += [
                self.o1.eq(self.a * self.b),
                self.o2.eq(self.a + self.b),
                self.o3.eq(self.a * self.c),
                self.o4.eq(self.a + self.c),
                self.o5.eq(self.b * self.d),
            ]
            
            return m

    from sem_board import OpenSemPlatform
    platform = OpenSemPlatform()
    dut = TopTest()
    sim = Simulator(dut)
    sim.add_clock(1.0 / 100e6, domain="sync")

    def sync_loop():
        yield
        yield
        # got = yield dut.c.s
        v = yield dut.o1.s; print(dut.o1.compute_value(v))
        v = yield dut.o2.s; print(dut.o2.compute_value(v))
        v = yield dut.o3.s; print(dut.o3.compute_value(v))
        v = yield dut.o4.s; print(dut.o4.compute_value(v))
        v = yield dut.o5.s; print(dut.o5.compute_value(v))
        
    sim.add_sync_process(sync_loop, domain="sync")
    
    with sim.write_vcd("sim/fixed_point.vcd"):
        sim.run()

if __name__ == "__main__":
    do_sim()
    