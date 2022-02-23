from argparse import ArgumentError
from amaranth import *
from amaranth.sim import *
from black import target_version_option_callback

# Example of multiplication with truncation of fractional LSB's
# m = module()
# a = SignedFixedPoint(8,2)
# b = SignedFixedPoint(2,8)
# c = SignedFixedPoint(10,2)
# m.d.comb += [
#    c.eq(a.mul(b))
# ]

class SignalFixedPoint:
    # int_bits / frac_bits can also be negative to shift decimal outside of represented digits
    def __init__(
        self, 
        int_bits : int = None,
        frac_bits : int = 0,
        constant=None,
        signed=None,
        *, value : Value = None,
    ):
        assert(frac_bits is not None)
        self.qf = frac_bits
        
        if value is None:
            assert(int_bits is not None)

            if constant is None:
                if signed is None:
                    signed = False
                self.s = Signal(Shape(int_bits + frac_bits, signed))
            elif isinstance(constant, float):
                if signed is None:
                    signed = constant < 0
                elif signed == False and constant < 0:
                    raise ArgumentError(signed, "Specified unsigned type for signed constant") 
                self.s = C(self.to_binary(constant), Shape(int_bits + frac_bits, signed))
            else:
                assert(False)
        else:
            assert(constant is None)
            assert(int_bits is None or int_bits == value.width)
            assert(signed is None or signed == value.signed)
            self.s = value
    
    def to_binary(self, v : float):
        return round(v / self.lsb_value())
    
    def __mul__(self, rhs):
        if isinstance(rhs, SignalFixedPoint):
            # result of mul would have:
            #   self.qi + rhs.qi integer bits
            #   self.qf + rhs.qf frac bits
            return SignalFixedPoint( value = self.s * rhs.s, frac_bits=self.qf + rhs.qf)
        elif isinstance(rhs, Value):
            return SignalFixedPoint( value = self.s * rhs, frac_bits=self.qf)
        else:
            raise ArgumentError("rhs not valid type")
    
    def __rmul__(self, rhs):
        # Commutative
        return self.__mul__(rhs)
    
    def __add__(self, rhs):
        if isinstance(rhs, SignalFixedPoint):
            self_extra_qf = self.qf - rhs.qf
            if self_extra_qf >= 0:
                return SignalFixedPoint( value = self.s + (rhs.s.shift_left(self_extra_qf)), frac_bits=self.qf)
            else:
                return SignalFixedPoint( value = (self.s.shift_left(-self_extra_qf)) + rhs.s, frac_bits=rhs.qf)
        elif isinstance(rhs, Value):
            self_extra_qf = self.qf - 0
            if self_extra_qf >= 0:
                return SignalFixedPoint( value = self.s + (rhs.shift_left(self_extra_qf)), frac_bits=self.qf)
            else:
                return SignalFixedPoint( value = (self.s.shift_left(-self_extra_qf)) + rhs, frac_bits=0)
        else:
            raise ArgumentError("rhs not valid type")

    def __radd__(self, rhs):
        # Commutative
        return self.__add__(rhs)
    
    def __sub__(self, rhs):
        if isinstance(rhs, SignalFixedPoint):
            self_extra_qf = self.qf - rhs.qf
            if self_extra_qf >= 0:
                return SignalFixedPoint( value = self.s - (rhs.s.shift_left(self_extra_qf)), frac_bits=self.qf)
            else:
                return SignalFixedPoint( value = (self.s.shift_left(-self_extra_qf)) - rhs.s, frac_bits=rhs.qf)
        elif isinstance(rhs, Value):
            self_extra_qf = self.qf - 0
            if self_extra_qf >= 0:
                return SignalFixedPoint( value = self.s - (rhs.shift_left(self_extra_qf)), frac_bits=self.qf)
            else:
                return SignalFixedPoint( value = (self.s.shift_left(-self_extra_qf)) - rhs, frac_bits=0)
        else:
            raise ArgumentError("rhs not valid type")
    
    def __neg__(self):
        return SignalFixedPoint( value = -self.s, frac_bits=self.qf)
    
    def eq(self, rhs : "SignalFixedPoint" ):
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
            self.a = SignalFixedPoint(0,20, constant = 0.3)
            self.b = SignalFixedPoint(3,16, constant = 4.4)
            self.c = SignalFixedPoint(8,8, constant = -5.2)
            self.d = C(9)
            
            self.o1 = SignalFixedPoint(16,16, signed=True)
            self.o2 = SignalFixedPoint(16,16, signed=True)
            self.o3 = SignalFixedPoint(16,16, signed=True)
            self.o4 = SignalFixedPoint(16,16, signed=True)
            self.o5 = SignalFixedPoint(16,16, signed=True)
            self.o6 = SignalFixedPoint(16,16, signed=True)
            self.o7 = SignalFixedPoint(16,16, signed=True)
        
        def elaborate(self, platform):
            m = Module()
                
            m.d.sync += [
                self.o1.eq(self.a * self.b),
                self.o2.eq(self.a + self.b),
                self.o3.eq(self.a * self.c),
                self.o4.eq(self.a + self.c),
                self.o5.eq(self.b * self.d),
                self.o6.eq(self.a + self.b * self.d - self.c),
                self.o7.eq(-self.b),
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
        v = yield dut.o6.s; print(dut.o6.compute_value(v))
        v = yield dut.o7.s; print(dut.o7.compute_value(v))
        
    sim.add_sync_process(sync_loop, domain="sync")
    
    with sim.write_vcd("sim/fixed_point.vcd"):
        sim.run()

if __name__ == "__main__":
    do_sim()
    