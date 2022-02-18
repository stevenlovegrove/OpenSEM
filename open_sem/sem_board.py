from amaranth import *
from amaranth.build import *
from amaranth.vendor.xilinx import *
from amaranth_boards.alchitry_au_plus import *
from amaranth_boards.resources import *

class SemAddOn:
    resources = [
        Resource("analog_secondary_electron", 0, 
            Subsignal("p", Pins("H8", dir="i")),
            Subsignal("n", Pins("J7", dir="i")),
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
