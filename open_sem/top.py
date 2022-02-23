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
from pwm import PWM

# Top-level module glues everything together
class Top(Elaboratable):
    def __init__(self):
        pass
    
    def elaborate(self, platform):
        m = Module()
        
        #params
        period = 1.0/100e6
        dac_cap=1e-7
        dac_res=[1e3]
        
        # Get references to external signals
        leds = Cat([platform.request("led", i) for i in range(8)])
        dac_scan_y0 = platform.request("R1E3")
        dac_scan_y1 = platform.request("R1E5")
        
        # Setup the submodules and connect their signals
        # m.submodules.pixel_scan = PixelScan()
        # m.submodules.backscatter = Backscatter(12)
        # m.submodules.sample_mux = SampleMux(16, [12,12,12,12] )
        m.submodules.xadc = XADC(
            platform.request("analog_secondary_electron"),
        )
        m.submodules.ft600 = FT60X_Sync245(
            ftdi_resource = platform.request("ft600"),
        )
        m.submodules.dac = DAC(
            delta_time=period, capacitor=dac_cap, resistors=dac_res,
            output_pwm=dac_scan_y0
        )
        m.submodules.pwm = PWM()
        m.submodules.pwm.pwm = dac_scan_y1
               
        # Three clock domains, all rising edge
        #   sync and ftdi are similar clocks speeds, possibly out of phase
        #   pixel is derived from sync, possibly the same
        # m.domains.sync = ClockDomain("sync")
        # m.domains.pixel = ClockDomain("pixel")
        
        # One cycle at 100Mhz is 10ns.
        # Bit n flips at [2**n * 1e-8] second intervals
        # 0-7   bits: 10ns, 20ns, 40ns, 80ns, 160ns, 320ns, 640ns, 1.280us,
        # 8-15  bits: 2.56us, 5.12us, 10.24us, 20.48us, 40.96us, 81.92us, 163.84us, 327.68us,
        # 16-23 bits: 655.36us, 1.31072ms, 2.62144ms, 5.24288ms, 10.48576ms, 20.97152ms, 41.94304ms, 83.88608ms,
        # 24-31 bits: 167.77216ms, 335.54432ms, 671.08864ms, 1.34217728s, 2.68435456s, 5.36870912s, 10.73741824s, 21.47483648s
        # 32-39 bits: 42.94967296s, 85.89934592s, 171.79869184s, 343.59738368s, 687.19476736s, 1374.38953472s, 2748.77906944s, 5497.55813888s
        counter_bits = 16 #26
        counter = Signal(counter_bits+1)
        sawtooth_int = Mux( ~counter[counter_bits], counter[:counter_bits], C(2**counter_bits-1) - counter[:counter_bits] )[:counter_bits] # each ramp lasts 671.08864ms
        
        m.submodules.ledbar = LedBar(counter_bits,8)
        
        m.d.comb += [
            # Let's just set the pixel clock equal to main clock for now          
            # ClockSignal(domain="sync").eq(board_clock),
            # ClockSignal(domain="pixel").eq(board_clock),
            
            # m.submodules.pixel_scan.x_steps.eq(C(4095)),
            # m.submodules.pixel_scan.y_steps.eq(C(4095)),
            
            m.submodules.ledbar.value.eq(sawtooth_int),
            # m.submodules.ledbar.value.eq(m.submodules.xadc.adc_sample_value),
            
            
            # m.submodules.dac.input.eq(sawtooth)
            # m.submodules.dac.input.eq(SignalFixedPoint(1,19,signed=True,constant=0.5))
        ]
        
        m.d.sync += [            
            counter.eq(counter + 1),
            
            m.submodules.dac.input.eq( SignalFixedPoint(value=sawtooth_int, frac_bits=sawtooth_int.shape().width) ),
            m.submodules.pwm.input.eq( sawtooth_int[-16:]),
            
            # m.submodules.pixel_scan.hold.eq(0),     
            leds.eq(m.submodules.ledbar.bar),
        ]
        
        with m.If(m.submodules.xadc.adc_sample_ready):
            m.d.sync += [
                # Stream counter out over USB
                m.submodules.ft600.fifo_to_f60x.w_data.eq( Cat( m.submodules.xadc.adc_sample_value, C(0000), C(11) ) ),
                m.submodules.ft600.fifo_to_f60x.w_en.eq(1)
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
            sim.add_clock(args.sync_period)
            with sim.write_vcd(vcd_file=args.vcd_file):
                sim.run_until(args.sync_period * args.sync_clocks, run_passive=True)
        case "build":            
            products = platform.build(design, do_program=False)
        case None:
            parser.print_help()