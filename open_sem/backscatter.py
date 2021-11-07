from nmigen import *

# Define derived samples from backscatter quadrant measurements
# We will be able to stream these derived samples alongside the raw
class Backscatter(Elaboratable):
    def __init__(self, quadrant_signals):
        assert(len(quadrant_signals) == 4)

        # in: ADC Samples from backscatter quadrants
        self.xy_00 = quadrant_signals[0]
        self.xy_10 = quadrant_signals[1]
        self.xy_01 = quadrant_signals[2]
        self.xy_11 = quadrant_signals[3]

        # out: Derived signals
        self.sum    = Signal.like(self.xy_00+self.xy_10+self.xy_01+self.xy_11)
        self.x_diff = Signal.like(self.sum)
        self.y_diff = Signal.like(self.sum)
        self.cross  = Signal.like(self.sum)

    def elaborate(self, platform):
        m = Module()

        # sum terms
        xx0 = Signal.like(self.xy_00+self.xy_10)
        xx1 = Signal.like(xx0)
        yy0 = Signal.like(xx0)
        yy1 = Signal.like(xx0)

        # horizontal and vertical sums
        m.d.comb += xx0.eq(self.xy_00 + self.xy_01)
        m.d.comb += xx1.eq(self.xy_10 + self.xy_11)
        m.d.comb += yy0.eq(self.xy_00 + self.xy_10)
        m.d.comb += yy1.eq(self.xy_01 + self.xy_11)

        # Compute output signals
        half_val = 2**(self.sum.shape().width-1)
        m.d.comb += self.sum.eq(xx0 + xx1)
        m.d.comb += self.x_diff.eq( half_val + xx0 - xx1 )
        m.d.comb += self.y_diff.eq( half_val + yy0 - yy1 )
        m.d.comb += self.cross.eq( half_val + self.xy_00 + self.xy_11 - self.xy_10 - self.xy_01 )

        return m