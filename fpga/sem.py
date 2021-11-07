from nmigen import *
from nmigen.build.dsl import Clock, Connector
from nmigen.lib.fifo import AsyncFIFO
from nmigen_boards.alchitry_au import *
from nmigen.cli import main

# Extend definition of existing AlchitryAu board with our 
# custom connections to ftdi chip and ADC's etc
class SemBoard(AlchitryAuPlatform):
    def __init__(self):
        super().__init__()
        self.connect_ftdi_board()
        pass

    def connect_ftdi_board(self):
        # self.add_connectors()
        pass   

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

# Stream data from the ADC's
class SampleReader(Elaboratable):
    def __init__(self):
        self.num_signals = 5
        self.samples = [Signal(12) for _ in range(self.num_signals)]

    def elaborate(self, platform):
        m = Module()
        # TODO: connect up to ADC's
        return m

class PixelScan(Elaboratable):
    def __init__(self):
        ############ IN: Scan Config
        # DAC deflection beam offsets for top-left
        self.x_begin = Signal(16)
        self.y_begin = Signal(16)

        # DAC constant current x-ramp for saw waveform
        self.x_grad = Signal(16)

        # DAC y deflection beam step per row
        self.y_grad = Signal(16)

        # Width and Height
        self.x_steps = Signal(12)
        self.y_steps = Signal(12)

        ############ IN: State Control
        # Pull high to hold raster. Will start scanning on first clock low.
        # Whilst on hold, scan config will be latched in
        self.hold = Signal()

        ############ OUT: Running Status
        # Discrete x, y position relative to width, height
        self.pos_x = Signal(16)
        self.pos_y = Signal(16)

        # OUT: y beam deflection signal for DAC 
        self.dac_y = Signal(16)

        # OUT: blank pulse (one cycle) for end of row
        self.blank_x = Signal()

        # OUT: blank pulse (one cycle) for end of image
        self.blank_y = Signal()

        ############ OUT: Latched (running) version of config
        self.l_x_begin = Signal(16)
        self.l_y_begin = Signal(16)
        self.l_x_grad = Signal(16)
        self.l_y_grad = Signal(16)
        self.l_x_steps = Signal(12)
        self.l_y_steps = Signal(12)

    def elaborate(self, platform):
        m = Module()

        # Finite state machine (FSM): Starts in first state, "HOLD".
        # FSM accepts changes to parameters in HOLD state whilst hold
        # signal is applied. Scanning begins when this goes low.
        # blank_x and blank_y are asserted at end of the rows and whole
        # image respectively
        with m.FSM() as fsm:
            with m.State("HOLD"):
                m.d.pixel += [
                    # Sync user config
                    self.l_x_begin.eq(self.x_begin),
                    self.l_y_begin.eq(self.y_begin),
                    self.l_x_grad.eq(self.x_grad),
                    self.l_y_grad.eq(self.y_grad),
                    self.l_x_steps.eq(self.x_steps),
                    self.l_y_steps.eq(self.y_steps),

                    # Set starting values
                    self.blank_x.eq(0),
                    self.blank_y.eq(0),
                    self.pos_x.eq(self.x_steps),
                    self.pos_y.eq(self.y_steps),
                    self.dac_y.eq(self.y_begin)
                ]

                with m.If(self.hold):
                    m.next = "HOLD"
                with m.Else():
                    m.next = "SCAN"

            with m.State("SCAN"):
                with m.If(self.pos_x > 0):
                    m.d.pixel += self.pos_x.eq(self.pos_x - 1)
                    m.next = "SCAN"
                with m.Else():
                    m.d.pixel += [
                        self.pos_x.eq(self.l_x_steps),
                        self.blank_x.eq(1)
                    ]
                    with m.If(self.pos_y > 0):
                        m.d.pixel += [
                            # Move y deflector beam
                            self.dac_y.eq(self.dac_y + self.y_grad)
                        ]
                        m.next = "ROW_BLANK"
                    with m.Else():
                        m.d.pixel += [
                            self.pos_y.eq(self.y_steps),
                            self.blank_y.eq(1),
                            self.dac_y.eq(self.dac_y + self.y_grad),
                        ]
                        m.next = "HOLD"

            with m.State("ROW_BLANK"):
                # Just a cycle to signal row end and let row cap reset
                m.d.pixel += self.blank_x.eq(0)
                m.next = "SCAN"

        return m

# class UserConfig(Elaboratable):
#     def __init__(self):
#         pass

#     def elaborate(self, platform):
#         pass

# Top-level module glues everything together
class Top(Elaboratable):
    def __init__(self):
        self.fifo_width_bits = 16
        self.test = Signal()

    def elaborate(self, platform):
        m = Module()

        # Three clock domains, all rising edge
        #   sync and ftdi are similar clocks speeds, possibly out of phase
        #   pixel is derived from sync, possibly the same
        m.domains += ClockDomain('sync')   # Main board clock
        m.domains += ClockDomain('pixel')  # Pixel output clock
        m.domains += ClockDomain('ftdi')   # FTDI FIFO clock

        # Let's just set the pixel clock equal to main clock for now
        m.d.comb += ClockSignal('pixel').eq( ClockSignal('sync'))

        # Setup the submodules and connect their signals
        m.submodules.pixel_scan = PixelScan()
        m.submodules.sample_reader = SampleReader()
        m.submodules.backscatter = Backscatter(m.submodules.sample_reader.samples[0:4])
        m.submodules.sample_mux = SampleMux(16,
            [m.submodules.backscatter.sum,
             m.submodules.backscatter.x_diff, 
             m.submodules.backscatter.y_diff, 
             m.submodules.backscatter.cross]
            + m.submodules.sample_reader.samples[4:]
        )
        
        # m.submodules.ftdi_rx_fifo = AsyncFIFO(
        #     width=self.fifo_width_bits,  depth=2,
        #     r_domain='sync',  w_domain='ftdi'
        #     )
        # m.submodules.ftdi_tx_fifo = AsyncFIFO(
        #     width=self.fifo_width_bits,  depth=2,
        #     r_domain='ftdi',  w_domain='sync'
        #     )

        return m

if __name__ == "__main__":
    top = Top()
    main(top, ports=[top.test])