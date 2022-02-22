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
from fixed_point import SignalFixedPoint


from samplemux import SampleMux
from scanning import PixelScan
from backscatter import Backscatter
from sem_board import OpenSemPlatform
from xadc import XADC
from ft60x import FT60X_Sync245
from ledbar import LedBar
from dac import DAC

# Top-level module glues everything together
class Top(Elaboratable):
    def __init__(self):
        pass
    
    def elaborate(self, platform):
        m = Module()
        
        #params
        period = 1.0/100e6
        dac_cap=1e-7
        dac_res=[1e2, 1e5]
        
        # Get references to external signals
        board_clock = platform.request(platform.default_clk)
        leds = Cat([platform.request("led", i) for i in range(8)])

        # Setup the submodules and connect their signals
        m.submodules.pixel_scan = PixelScan()
        # m.submodules.backscatter = Backscatter(12)
        # m.submodules.sample_mux = SampleMux(16, [12,12,12,12] )
        m.submodules.xadc = XADC(
            platform.request("analog_secondary_electron"),
        )
        m.submodules.ft600 = FT60X_Sync245(
            ftdi_resource = platform.request("ft600"),
        )
        # m.submodules.dac = DAC(
        #     delta_time=period, capacitor=dac_cap, resistors=dac_res,
        #     output_pwm=platform.request("dac_scan_y")
        # )
        
        m.submodules.ledbar = LedBar(12,8)

        
        # Three clock domains, all rising edge
        #   sync and ftdi are similar clocks speeds, possibly out of phase
        #   pixel is derived from sync, possibly the same
        m.domains.sync = ClockDomain("sync")
        m.domains.pixel = ClockDomain("pixel")
        
        counter = Signal(21)
        # sawtooth_int = Mux( counter[-1], counter[:20], C(0xfffff) - counter[:20] )
        # sawtooth = SignalFixedPoint(0,20)
        
        m.d.comb += [
            # Let's just set the pixel clock equal to main clock for now          
            ClockSignal(domain="sync").eq(board_clock),
            ClockSignal(domain="pixel").eq(board_clock),
            
            m.submodules.pixel_scan.x_steps.eq(C(4095)),
            m.submodules.pixel_scan.y_steps.eq(C(4095)),
            
            m.submodules.ledbar.value.eq(m.submodules.xadc.adc_sample_value),
            leds.eq(m.submodules.ledbar.bar),
            
            # sawtooth.s.eq(sawtooth_int),
            # m.submodules.dac.input.eq(sawtooth)
            # m.submodules.dac.input.eq(SignalFixedPoint(1,19,signed=True,constant=0.5))
        ]
        
        with m.If(m.submodules.xadc.adc_sample_ready):
            m.d.sync += [
                # Stream counter out over USB
                m.submodules.ft600.fifo_to_f60x.w_data.eq( Cat( m.submodules.xadc.adc_sample_value, C(0000), C(11) ) ),
                m.submodules.ft600.fifo_to_f60x.w_en.eq(1)
            ]
         
        m.d.pixel += [            
            m.submodules.pixel_scan.hold.eq(0),     
            counter.eq(counter +1),
            platform.request("dac_scan_y").eq(counter[0:2])
        ]
        
        return m

if __name__ == "__main__":
    platform = OpenSemPlatform()
    design = Top()
    
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
            products = platform.build(design, do_program=False)
        case None:
            parser.print_help()