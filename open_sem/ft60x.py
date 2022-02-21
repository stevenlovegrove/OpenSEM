import os
from amaranth import *
from amaranth.sim import Simulator, Delay, Settle
from amaranth.lib.fifo import *

# Interface with FTDI FT600 and FT601 USB 3.0 Controller devices in Synchronous 245 mode
# With inspiration from the Alchitry FT600 lucid example
# FT601 definition remains untested.
class FT60X_Sync245(Elaboratable):
    def __init__(self, *, ftdi_resource, clk="sync", chip="ft600", fifo_depth_to_ft60x=128, fifo_depth_from_ft60x=8 ):        
        match chip:
            case "ft600": self.data_bytes = 2
            case "ft601": self.data_bytes = 4
            case _: raise AssertionError("Unsupported chip type")
            
         # We'll use the first (data_bytes) bits to store the validity mask, then the actual data
        self.fifo_width = (self.data_bytes) + 8*self.data_bytes
        self.ftdi = ftdi_resource
        self.clk = clk
            
        # Params
        self.fifo_depth_to_ft60x = fifo_depth_to_ft60x
        self.fifo_depth_from_ft60x = fifo_depth_from_ft60x

        # Read and write fifos (user should use 'sync' side of FIFO only. 'ftdi' side is managed by module)
        self.fifo_from_f60x = AsyncFIFOBuffered(width=self.fifo_width, depth=self.fifo_depth_from_ft60x, r_domain=clk, w_domain="ftdi")    
        self.fifo_to_f60x   = AsyncFIFOBuffered(width=self.fifo_width, depth=self.fifo_depth_to_ft60x, r_domain="ftdi", w_domain=clk)

    def elaborate(self, platform):
        m = Module()
        
        m.domains.ftdi = ClockDomain("ftdi")
        
        # Async fifo's allow us to transfer data between clock domains
        m.submodules.fifo_from_f60x = self.fifo_from_f60x
        m.submodules.fifo_to_f60x   = self.fifo_to_f60x
        
        can_pull = Signal()
        can_push = Signal()

        m.d.comb += [
            ClockSignal(domain="ftdi").eq(self.ftdi.clk),

            # ftdi side of fifos are always tied to ft_data (in/out)
            m.submodules.fifo_from_f60x.w_data.eq( Cat(self.ftdi.data.i, self.ftdi.be.i) ),
            Cat(self.ftdi.data.o, self.ftdi.be.o).eq(m.submodules.fifo_to_f60x.r_data),
            
            # Tristate set to output only when ft_wr is high
            self.ftdi.data.oe.eq(self.ftdi.wr),
            self.ftdi.be.oe.eq(self.ftdi.wr),
            self.ftdi.oe.eq(~self.ftdi.wr),
            
            # can push / pull when data is available and we have somewhere to put it
            can_pull.eq(self.ftdi.rxf & self.fifo_from_f60x.w_rdy),
            can_push.eq(self.ftdi.txe & self.fifo_to_f60x.r_rdy),
        ]
        
        with m.FSM(domain="ftdi") as fsm:
            with m.State("IDLE"):
                # no fifo reads or writes should be triggered next cycle in ftdi domain
                m.d.ftdi += [
                    m.submodules.fifo_from_f60x.w_en.eq(0),
                    m.submodules.fifo_to_f60x.r_en.eq(0)
                ]
                
                # # Prioritize reading if ft60x has data and our read fifo isn't full
                # with m.If(can_pull):                    
                #     m.d.ftdi += [
                #         # Let ft60x control bus, request read from ft60x
                #         self.ftdi.rd.eq(1),
                #         self.ftdi.wr.eq(0)
                #     ]
                #     m.next = "PULL"
                    
                # Otherwise we start writing if the ft60x isn't full and the fpga has data
                # with m.Elif(can_push):
                with m.If(can_push):
                    m.d.ftdi += [
                        # Let fpga control bus, request write from ft60x
                        self.ftdi.rd.eq(0),
                        self.ftdi.wr.eq(1),
                    ]
                    m.next = "PUSH"

            # with m.State("PULL"):
            #     # on the current rising edge, ft_rd=1 and ft60x has presented data
                
            #     m.d.ftdi += [
            #         # trigger fifo.push next cycle
            #         m.submodules.fifo_from_f60x.w_en.eq(1)
            #     ]

            #     # TODO: optimize to avoid IDLE if PUSH is possible
            #     with m.If(~can_pull):                    
            #         m.next = "IDLE"
            #         m.d.ftdi += [ self.ftdi.rd.eq(0)]
            
            with m.State("PUSH"):
                # on the current rising edge, ft_wr=1 and ft60x latched data from fifo

                m.d.ftdi += [
                    # trigger fifo.pop next cycle
                    m.submodules.fifo_to_f60x.r_en.eq(1)
                ]
                
                # Prioritize pulls if possible
                # TODO: optimize to avoid IDLE if PULL is possible
                # with m.If(~can_push | can_pull):                    
                with m.If(~can_push):                    
                    m.next = "IDLE"
                    m.d.ftdi += [ self.ftdi.wr.eq(0)]
                pass            
                          
        return m

def do_sim():
    from sem_board import OpenSemPlatform
    platform = OpenSemPlatform()
    ftdi_resource = platform.request("ft600")
    dut = FT60X_Sync245(chip="ft600", clk="sync", ftdi_resource = ftdi_resource)
    sim = Simulator(dut)
    sim.add_clock(1.0 / 100e6, domain="sync")
    sim.add_clock(1.0 / 100e6, domain="ftdi")

    def sync_loop():
        yield
        yield dut.fifo_to_f60x.w_data.eq(0x5678)
        yield dut.fifo_to_f60x.w_en.eq(1)
        yield 
        yield dut.fifo_to_f60x.w_en.eq(0)
        yield


    def ftdi_loop():
        yield
        yield ftdi_resource.txe.eq(1)
        yield ftdi_resource.data.eq(0x1234)
        yield ftdi_resource.be.eq(0b11)
        yield ftdi_resource.rxf.eq(1)
        yield
        yield ftdi_resource.rxf.eq(0)
        yield
        yield
        yield
        yield
        yield
        yield
        yield
        yield
        yield
        
        
        
    sim.add_sync_process(sync_loop, domain="sync")
    sim.add_sync_process(ftdi_loop, domain="ftdi")
    
    os.makedirs("sim", exist_ok=True)
    with sim.write_vcd("sim/ft60x.vcd"):
        sim.run()

if __name__ == "__main__":
    do_sim()
    