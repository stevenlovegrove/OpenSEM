# Major Components

* Vacuum System and PC Interface
  * Control pump systems
  * Control spin-down and vent
  * Monitor Pressure
* Electron Gun System and PC interface
  * Control Acceleration voltage
  * Control filament power
    * This is low voltage, but floating at kilovolts
    * Needs appropriate isolation
  * Control and Monitor Emission Current
* Coil System and PC Interface
  * Linear adjustable power supplies
    * Alignment
    * Condensor 1 & 2
    * Objective
    * Stigmata
  * Amplifier
    * X & Y Deflection
* Deflection controller and Detector Sampler
  * Low-current amplifiers for secondary and backscatter detectors
  * High-rate digitization of detector signals
  * Controlling deflection scan pattern for PC navigation and field of view control
  * Synchronized deflection, sampling and readout



# TODOs

* ~~Design & Fab Stand~~
  * ~~Weld steel cube from scrap steel pipe~~
  * ~~Powder coat~~

* ~~Vacuum Subsystem~~
  * ~~Components:~~
    * ~~Backing pump (2 stage rotary)~~
    * ~~Turbopump~~
    * ~~Turbopump ESC~~
    * ~~Solenoid Vent~~
      * ~~12V power supply~~
    * ~~Main chamber pressure sensor~~
    * ~~Controller and power~~
    * ~~70V Power supply for Turbopump~~
    * ~~24V Power supply for vent and pressure sensor~~
  * ~~Fabrication~~
    * ~~Turbo-pump to chamber mount~~
    * ~~Chamber flange for VCR1/8 Pressure Sensor~~
    * ~~Acrylic Chamber Window~~
    * ~~Controller enclosure~~
  * ~~Control~~
    * ~~RS232 Interface to turbo-pump~~
    * ~~RS232 Interface to vacuum guage~~
    * ~~Control for pump and solenoid relays~~
* ~~Electron Gun Subsystem~~
  * ~~Components:~~
    * ~~High Voltage accelerating 'High Tension' power supply~~
      ~~KiloVolts HP30R 30KV reversible supply~~
    * ~~Tungstan filament low voltage *isolated* power supply~~
      ~~Lipo and dc-dc buck convert~~
    * ~~High Voltage Controler~~
  * ~~Fabrication~~
    * ~~High Voltage connectors~~
    * ~~High Voltage enclosure and isolated user interface~~
  * ~~Control~~
    * ~~Microproprocessor interface to High Voltage supply~~
* Coil Subsystem
  * Components
    * ~~Adjustable coil power supplies~~
      ~~HP bench supply (HP 6624A), 4 channel~~
    * Deflection coil driver

  * Control
    * ~~HP-IB/IEE-488 microcontroller interface to coil power supplies~~

* Detector Subsystem
  * Secondary Electron Detector
    * Reverse Engineer wiring

  * ~~Backscatter Four Quadrand Detector~~
    * ~~Reverse Engineer existing amplifier~~
    * ~~Create split rail power supply for amplifier~~
      TODO: Reduce noise on rails

* SEM Controller and Signal Sampler
  * ~~Components~~
    * ~~FPGA fabric~~
      ~~Alchitry Au+, Xilinx Artix 7 (XC7A100T)~~
    * ~~USB3.0 highspeed data-transfer~~
      ~~Alchitry Element Ft with FTDI FT600 USB3.0 chip~~

  * Electronics
    * Sampler front-end input (to FPGA voltage levels)
    * Linear ramp circuit with bias, slope and duration control

  * FPGA design blocks
    * Deflection signal driver
      * DAC drivers for linear ramp circuit control
        *WIP*

    * ADC Samplers
      * ~~Round 1: low-speed integrated XADC module~~
      * Round 2: Highspeed multi-channel ADC

    * ~~Backscatter component maths~~
    * ~~Sample Mux~~
    * USB3.0 transfer driver
      *Operational, not polished*




