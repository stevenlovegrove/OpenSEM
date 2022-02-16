from amaranth import *

# Stream data from the ADC's
class SampleReader(Elaboratable):
    def __init__(self):
        self.num_signals = 5
        self.samples = [Signal(12) for _ in range(self.num_signals)]

    def elaborate(self, platform):
        m = Module()
        # TODO: connect up to ADC's
        return m

