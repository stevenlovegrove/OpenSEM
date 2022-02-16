import glob
import argparse
import pprint

from tkinter import TOP

from amaranth import *
from amaranth.cli import *
from amaranth.back import verilog
from amaranth.sim import Simulator
from amaranth.build.dsl import DiffPairs

from amaranth import *


from samplemux import SampleMux
from scanning import PixelScan
from backscatter import Backscatter
from sem_board import OpenSemPlatform
from xadc import XADC
from ledbar import LedBar

# Top-level module glues everything together
class Top(Elaboratable):
    def __init__(self):
        pass
    
    def elaborate(self, platform):
        m = Module()
        
        vp = platform.request("analog_p")
        vn = platform.request("analog_n")

        # Interface to verilog module definitions
        # Not sure if we're allowed to put this here?
        # # https://lab.ktemkin.com/post/nmigen-instance/
        # for filename in glob.glob("verilog/*.v"): 
        #     platform.add_file(filename, open(filename))

        # Setup the submodules and connect their signals
        m.submodules.pixel_scan = PixelScan()
        # m.submodules.backscatter = Backscatter(12)
        # m.submodules.sample_mux = SampleMux(16, [12,12,12,12] )
        m.submodules.xadc = XADC(vp, vn)
        m.submodules.ledbar = LedBar(12,8)

        leds = Cat([platform.request("led", i) for i in range(8)])
        board_clock = platform.request(platform.default_clk)
        # board_clock = platform.request("clk100")
        
        # Three clock domains, all rising edge
        #   sync and ftdi are similar clocks speeds, possibly out of phase
        #   pixel is derived from sync, possibly the same
        m.domains.sync = ClockDomain()
        m.domains.pixel = ClockDomain()
        
        counter = Signal(26)

        m.d.comb += [
            # Let's just set the pixel clock equal to main clock for now          
            ClockSignal(domain="sync").eq(board_clock),
            ClockSignal(domain="pixel").eq(board_clock),
            
            m.submodules.pixel_scan.x_steps.eq(C(4095)),
            m.submodules.pixel_scan.y_steps.eq(C(4095)),
            
            # m.submodules.xadc.analog_pin_pos.eq(),
            # m.submodules.xadc.analog_pin_neg.eq(),
                        
            m.submodules.ledbar.value.eq(m.submodules.xadc.adc_sample_value),
            leds.eq(m.submodules.ledbar.bar),
            
            # leds.eq(counter[-8:]) # MSB's
        ]
         
        m.d.pixel += [            
            m.submodules.pixel_scan.hold.eq(0),           
            # counter.eq(counter + 1),
        ]
        
        # Count how many eoc's we're seeing
        with m.If(m.submodules.xadc.adc_sample_ready):
            m.d.pixel += [counter.eq(counter + 1)]

        return m

if __name__ == "__main__":
    design = Top()
    platform = OpenSemPlatform()
    
    parser = argparse.ArgumentParser(description='OpenSEM Top-level')
    p_action = parser.add_subparsers(dest="action")

    p_generate = p_action.add_parser("generate",
        help="generate Verilog from the design")
    p_generate.add_argument("generate_file",
        metavar="FILE", type=argparse.FileType("w"), nargs="?",
        help="write generated code to FILE")
    
    p_build = p_action.add_parser("build", 
        help="build design to binary bitstream")

    p_simulate = p_action.add_parser(
        "simulate", help="simulate the design")
    p_simulate.add_argument("-v", "--vcd-file",
        metavar="VCD-FILE", type=argparse.FileType("w"),
        help="write execution trace to VCD-FILE")
    p_simulate.add_argument("-w", "--gtkw-file",
        metavar="GTKW-FILE", type=argparse.FileType("w"),
        help="write GTKWave configuration to GTKW-FILE")
    p_simulate.add_argument("-p", "--period", dest="sync_period",
        metavar="TIME", type=float, default=1.0 / platform.default_clk_frequency,
        help="set 'sync' clock domain period to TIME (default: %(default)s)")
    p_simulate.add_argument("-c", "--clocks", dest="sync_clocks",
        metavar="COUNT", type=int, required=True,
        help="simulate for COUNT 'sync' clock periods")

    args = parser.parse_args()    
    
    match args.action:
        case "generate":
            fragment = Fragment.get(design, platform)
            output = verilog.convert(fragment, name="top", ports=(), emit_src=False)
            if args.generate_file:
                args.generate_file.write(output)
            else:
                print(output)
        case "simulate":
            fragment = Fragment.get(design, platform)
            sim = Simulator(fragment)
            sim.add_clock(args.sync_period, domain="pixel")
            with sim.write_vcd(vcd_file=args.vcd_file):
                sim.run_until(args.sync_period * args.sync_clocks, run_passive=True)
        case "build":            
            products = OpenSemPlatform().build(design, do_program=False)
        case None:
            parser.print_help()