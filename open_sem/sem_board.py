from amaranth import *
from amaranth_boards.alchitry_au_plus import *

# Extend definition of existing AlchitryAu board with our 
# custom connections to ftdi chip and ADC's etc
class OpenSemPlatform(AlchitryAuPlatform):
    def __init__(self):
        super().__init__()
        pass    
