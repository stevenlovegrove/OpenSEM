from amaranth import *
from amaranth.build import *
from amaranth.vendor.xilinx import *
from amaranth_boards.alchitry_au_plus import *
from amaranth_boards.resources import *

class SemAddOn:
    resources = [
        Resource("analog_secondary_electron", 0, 
            Subsignal("p", Pins("H8", dir="i")), # AVP (Element BR - D31)
            Subsignal("n", Pins("J7", dir="i")), # AVN (Element BR - D30)
        ),
        Resource("dac_scan_y", 0, 
            Subsignal("R1E2", Pins("T15", dir="o")), # (Element BR - D43)
            Subsignal("R1E5", Pins("T14", dir="o")), # (Element BR - D42)
            Attrs(IOSTANDARD="LVCMOS33")
        ),
    ]

# Extend definition of existing AlchitryAu board with our 
# custom connections to ftdi chip and ADC's etc
class OpenSemPlatform(AlchitryAuPlatform):
    def __init__(self):
        super().__init__()
        self.add_element_board(AlchitryElementBoard_FT())
        self.add_element_board(SemAddOn())
        pass    
