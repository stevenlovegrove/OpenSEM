from nmigen import *
from nmigen.cli import main
from nmigen_boards.alchitry_au import *

from sampling import SampleReader
from sampling import SampleMux
from scanning import PixelScan
from backscatter import Backscatter

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