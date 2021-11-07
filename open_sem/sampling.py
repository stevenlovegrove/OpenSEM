from nmigen import *

# Stream data from the ADC's
class SampleReader(Elaboratable):
    def __init__(self):
        self.num_signals = 5
        self.samples = [Signal(12) for _ in range(self.num_signals)]

    def elaborate(self, platform):
        m = Module()
        # TODO: connect up to ADC's
        return m

# Module allows us to specify which samples and with what bitdepths
# we will be streaming to the host. We do this by applying user defined
# masks and shifts into a (possibly larger) output Signal
class SampleMux(Elaboratable):
    def __init__(self, output_bits, input_samples) -> None:
        self.output_bits = output_bits

        # In
        self.input_samples = input_samples
        self.input_mask = [Signal.like(x) for x in self.input_samples]
        self.input_shft = [Signal(8) for x in self.input_samples]

        # Out
        self.output_sample = Signal(output_bits)

    def elaborate(self, platform):
        m = Module()
        # If()

        anded = [Signal(self.output_bits) for _ in self.input_samples]
        shifted = [Signal(self.output_bits) for _ in self.input_samples]

        for i in range(len(anded)):
            m.d.comb += anded[i].eq( self.input_samples[i] & self.input_mask[i] )

        for i in range(len(shifted)): 
            abs_val = self.input_shft[i][:7]    # [0] is LSB
            m.d.comb += shifted[i].eq( 
                    Mux(self.input_shft[i][-1], # test MSB
                        anded[i] << abs_val,
                        anded[i] >> abs_val )
                )

        ored = shifted[0]
        for i in range(1, len(shifted)):
            ored = ored | shifted[i]

        m.d.comb += self.output_sample.eq(ored)
        m.Switch

        return m