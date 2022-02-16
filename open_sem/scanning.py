import os
from amaranth import *
from amaranth.sim import Simulator


# Drive the x,y deflection beams for raster scanning.
# The DAC for the y-deflection is driven directly.
# The x-beam is driven through the parameters of an
# external analog linear ramp generator.
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
        self.hold = Signal(reset=1)

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
        with m.FSM(domain="pixel") as fsm:
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
                            self.pos_y.eq(self.pos_y - 1),
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
   
def sim_pixelscan_1():
    dut = PixelScan()
    sim = Simulator(dut)
    sim.add_clock(1e-6/100,domain="pixel")

    def loopback_proc():
        yield dut.x_steps.eq(10)
        yield dut.y_steps.eq(20)
        yield dut.y_grad.eq(130)
        yield
        yield dut.hold.eq(0)
        while True:
            yield
        
    sim.add_sync_process(loopback_proc, domain="pixel")
    
    os.makedirs("sim", exist_ok=True)
    with sim.write_vcd("sim/pixelscan_1.vcd"):
        sim.run_until(1e-3) # 1ms
        
if __name__ == "__main__":
    sim_pixelscan_1()