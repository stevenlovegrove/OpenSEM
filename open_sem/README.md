# OpenSEM FPGA HLS Library

## Overview

FPGA design is more accesible than ever and we'll utilize an FPGA in our design to enable high throughput and accurate timing. I wouldn't rule out the feasibility of a stock microcontroller design, perhaps coupled with the DSP-like Cypress FX3 fabric, but we gain flexibility with the HW reconfigurability of an FPGA and I believe we can more easily hit the sampling rates that we desire.

We'll be using the High-Level-Synthesis (HLS) tool [nmigen](https://github.com/m-labs/nmigen) to synthesize a hardware design from high-level description in the Python meta description language. Recently, several HLS tools have been gaining in popularity - [CHISEL](https://www.chisel-lang.org/), [myHDL](https://www.myhdl.org/), [spinalHDL](https://github.com/SpinalHDL/SpinalHDL), [RIGEL](https://github.com/jameshegarty/rigel), [migen](https://github.com/m-labs/migen) etc. nmigen was chosen since it seems accessible, embedded within a mature and popular language, and it is under active development. I would love to hear from people with more experience on this. RIGEL looks great for any image processing blocks that we might be interested in later.

This directory contains the hardware modules for sub-components of the FPGA design which is glued together in a final system ready for synthesis within top.py (as in top-level, as is convention within the HW design community).

Contributions encouraged! Since this project is in its early phase, design, tool and rewrite discussions are welcome!



## Proposed Reference Design

#### Host Interface

Targetting a PCIe interface would be *sensible* for achieving very high sampling rates and predictable latencies, but it limits accessibility for the host computer platform. We choose to target the FTDI 600 USB 3.0 interface chip which includes a large receive and transfer FIFO and should offer a reliable 180-200MB/s streaming transfer speed (200MB/s up and 200MB/s down). Using USB 3.0 requires that all timing critical logic is implemented on the device-side platform.

12bit 2000x2000 @ 30fps ~ 170 MB/s which will be our target single-stream high-definition operating mode. This will be shared between different streams if multi-channel streaming is configured.

#### Signal Sampling (ADC)

12bit 2000x2000 @ 30fps = 120MS/s

ADC's in this range are 40USD and up. Since we are interested in multiple channels and high-precision, the MCP37211 looks interesting. It includes 16bit differential sampling and a MUX which can select between 8 analog channels. The sampling rate can also be divided between channels for simultaneous signal capture. This is a BGA package and will be more challenging to breadboard.

#### Electron Beam Control

There are surprisingly few high-speed, high precision DAC's available, and none at moderate costs as of writing to drive electron beam deflection signals directly. We have a few options:

1) Use DAC's to drive X,Y deflection signals directly. Doing so requires high bit-depth in order to support both macro views and high-magnification nano-scale views. A 10x10mm macro view would only be 152nm pixel size at max magnification for 16bit DAC for example. We really need 24bit DAC's. High-precision DAC's don't operate at the target 120MS/s speed.
2) Use lower precision DAC's for driving deflection signals at target speeds and rely on auxillary low-rate bias and gain controls for zooming and panning within the sample. The dissadvantage here is that multi-frame stitching and different kinds of jitter sampling become more complicated due to calibration issues with bias/gain response. To get our target 2000 pixel horizontal resolution, we would still need an 11bit DAC, which is still hard to find at the target sample speed.
3) User a precise linear ramp analog signal to drive the x deflection beam in a raster scan, and use high-precision but lower speed DAC's for the reset value and constant-current ramp rate. The y deflection beam can be driven directly because it is sampled much less frequently. We must use latching DAC's so that we can preload them serially and switch with accurate timing. There remains a scale calibration issue, but not a bias calibration issue. For this to work, me must use an FPGA clock signal with low jitter / skew since we will rely on this to sample the linear ramp uniformly and repeatedly. With looser timing constraints on DAC settling time, we can use high-precision and serially loaded IC's. This has scaling advantages for using fewer pins with high-bit-depth, potentially for driving multiple deflection beams (such as FIB) in the future.

If you can't tell, we're planning to try option 3 first, implemented [here](https://github.com/stevenlovegrove/OpenSEM/blob/main/open_sem/scanning.py).

## Reference BOM

* [Alchitry Au](https://alchitry.com/boards/au) FPGA baseboard
  This off-the-shelf development board is affordable ($100), compact, and features a very capable Xilinx Artix-7 FPGA. It breaks out 200 pins via a stackable design which makes it perfect for projects featuring lots of IO. There is a larger pin-compatible board (Au+, $300) for more experimental developments.
* [Alchitry Ft](https://alchitry.com/pageft) FTDI FT600 USB 3.0 daughter board
  This board snaps into the Au and provides plenty of upload bandwidth for real-time, high-definition SEM imaging.
* Custom stackable daughter-board (base capability)
  * TBD: Microchip MCP37211-200E 8-channel ADC / Mux (~$50)
    Fast pipelined sampling
  * TBD: Analog Devices MAX5134AGUE+ 16-bit 4-channel DAC (~$15)
    (this device is slow, but have no fear, there is a plan)
  * Various discretes
  * BNC to pre-amped sensors and analog power drive circuits.

