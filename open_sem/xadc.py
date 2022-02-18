import os
from amaranth import *
from amaranth.sim import Simulator

# https://www.xilinx.com/support/documentation/user_guides/ug480_7Series_XADC.pdf
# Configuration Registers
# #0, DADDR[6:0] = 40h: CAVG, 0, AVG1, AVG0, MUX, BU, EC, ACQ, 0, 0, 0, CH4, CH3, CH2, CH1, CH0
# #1, DADDR[6:0] = 41h: SEQ3, SEQ2, SEQ1, SEQ0, ALM6, ALM5, ALM4, ALM3, CAL3, CAL2, CAL1, CAL0, ALM2, ALM1, ALM0, OT
# #2, DADDR[6:0] = 42h: CD7, CD6, CD5, CD4, CD3, CD2, CD1, CD0, 0, 0, PD1, PD0, 0, 0, 0, 0

# Register 0 config (0x40)
# CH = 00011 (VP, VN analog input)
# ACQ = 0 (low settling time, higher data rate)
# EC = 0 (continuous sampling)
# BU = 0 (unipolar mode, 0-1V, +ive only)
# MUX = 0 (No external mux)
# AVG = 00 (No averaging)
# CAVG = 0 (enable averaging for calibration)
#   == 0000000000000011 = 0x0003

# Register 1 config (0x41)
# OT = 1 (disable over temperature alarm)
# ALM = 111111 (disable all other alarms)
# CAL = 0000 (disable all calib params for now)
# SEQ = 0011 (single channel mode, sequencing off)
#   == 0011111100001111 = 0x3f0f

# Register 2 config (0x42)
# PD = 10 (power down ADC B)
# CD = 00000100 (4x clock divisor for 25Mhz ADC clock on 100Mhz board clock. 26Mhz is max. 26 cycles for one acquision = 0.96 MSPS)
#   == 0000010000100000 = 0x0420


# Configure the Internal Xilinx ADC for continuous single channel sampling
class XADC(Elaboratable):
    def __init__(self, diff_pair):
        # continuously sample from VP/VN
        self.channel = C(0x03) 
        
        ############################################################
        # Module Output
        
        self.adc_sample_ready = Signal()
        self.adc_sample_value = Signal(12) 
        
        # Module Input
        self.vp = diff_pair.p
        self.vn = diff_pair.n
        
        ############################################################
        ## Signals from XADC sub-module
        
        # XADC: Alarms (out)
        # self.alarm = Signal(8)
        # self.ot    = Signal()
        
        # XADC: Status (out)  
        # self.channel = Signal(7)
        self.eoc     = Signal()
        # self.eos     = Signal()
        # self.busy    = Signal()

        # XADC: DRP: Dynamic Reconfiguration Port (out/in)
        # self.dwe  = Signal()
        self.den  = Signal()
        self.drdy = Signal()
        # self.dadr = Signal(7)
        # self.di   = Signal(16)
        self.do   = Signal(16)

    def elaborate(self, platform):
        m = Module()

        # 48h to 4Fh        
        m.submodules.xadc = Instance("XADC",
            # From UG480
            # [0x40,0x42] Config registers
            p_INIT_40=0x0003, p_INIT_41=0x3f0f, p_INIT_42=0x0420,
            # [0x43,0x47] Factory test registers - don't touch
            # [0x48,0x4F] Channel Sequence registers
            # p_INIT_48=0x4701, p_INIT_49=0x000f,
            # p_INIT_4A=0x4700, p_INIT_4B=0x0000,
            # p_INIT_4C=0x0000, p_INIT_4D=0x0000,
            # p_INIT_4E=0x0000, p_INIT_4F=0x0000,
            # [0x50,0x5F] Alarm registers
            # p_INIT_50=0xb5ed, p_INIT_51=0x5999,
            # p_INIT_52=0xa147, p_INIT_53=0xdddd,
            # p_INIT_54=0xa93a, p_INIT_55=0x5111,
            # p_INIT_56=0x91eb, p_INIT_57=0xae4e,
            # p_INIT_58=0x5999, p_INIT_5C=0x5111,
            
            # o_ALM       = self.alarm,
            # o_OT        = self.ot,
            
            # o_CHANNEL   = self.channel,
            o_EOC       = self.eoc,
            # o_EOS       = self.eos,
            # o_BUSY      = self.busy,
            
            i_VP        = self.vp,
            i_VN        = self.vn,
            i_VAUXP     = C(0),
            i_VAUXN     = C(0),
            
            i_CONVST    = C(0),
            i_CONVSTCLK = C(0),
            i_RESET     = ResetSignal(),
            i_DCLK      = ClockSignal(),
            i_DWE       = C(0),
            i_DEN       = self.den,
            o_DRDY      = self.drdy,
            i_DADDR     = self.channel,
            i_DI        = C(0),
            o_DO        = self.do
        )
        
        # Used for rising edge detection
        last_eoc = Signal()
        m.d.sync += [last_eoc.eq(self.eoc)]
        
        m.d.comb += [           
            # Immediately request read from DRP at end of conversion
            # Data will arrive at self.do once self.drdy is high
            # den must only be high for one DCLK (according to docs)
            self.den.eq(self.eoc & ~last_eoc),
            
            # User facing signal for new sample
            self.adc_sample_ready.eq(self.drdy)
        ]
        
        with m.If(self.drdy):
            # output is 12 MSB's of data-out at address 'channel' (0x03)
            m.d.sync += [ self.adc_sample_value.eq(self.do >> 4) ]
        
        return m
   
# def sim_xadc_1():
#     dut = XADC()
#     sim = Simulator(dut)
#     sim.add_clock(1e-6/100,domain="pixel")

#     def loopback_proc():
#         # yield dut.hold.eq(0)
#         while True:
#             yield
        
#     sim.add_sync_process(loopback_proc, domain="pixel")
    
#     os.makedirs("sim", exist_ok=True)
#     with sim.write_vcd("sim/xadc_1.vcd"):
#         sim.run_until(1e-3) # 1ms
        
# if __name__ == "__main__":
#     sim_xadc_1()