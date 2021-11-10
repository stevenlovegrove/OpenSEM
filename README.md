# OpenSEM Project

**Status:** Preliminary

The purpose of this project is to create a modern and open-source hardware and software platform for using vintage and custom scanning electron microscopes (SEM's). Old SEM columns can be found online for relatively little, but there is little documentation online for the enthusiast operation of such machines. Whats-more, vintage machines generally have vintage analog controls which consume more space than the SEM itself, if they even work.

## Project Goals

#### Document Interfaces for existing machines

Let's build a de-facto reference for understanding the electrical and mechanical operation and interfaces to existing machines.

* [Cambridge StereoScan 260](sem_info/cambridge_stereoscan_260/README.md)

#### Reference Power Supply Options & Designs

One of the barriers to SEM's are the numerous different supply voltages required, including accelerating voltages up to ~ 30KV. It's possible to find appropriate power supplies used online, but which are appropriate? Can we provide a modern, low-cost miniturized reference design?

#### Reference analog amplifier Options & Designs

There are various sensors which can be used in a SEM machines. These typically involve low current signals which must be buffered and amplified before digitization.

#### Flexible Reference Open Control Boards

An open and low(ish) cost design for the synchronized beam control, sensor digitization and host transfer of SEM images.

* Preliminary FPGA design based on Xilinx Arts-7 and FTDI 600 USB 3.0 controller
  [FPGA HLS Design](https://github.com/stevenlovegrove/OpenSEM/tree/main/open_sem)



## Other Enthusiast Scanning Electron Microscopes

* The most well know are the legendry Applied Sciences SEM [videos](https://www.youtube.com/watch?v=VdjYVF4a6iU)
  * Impressive, but not easy to reproduce or use, using lots of bespoke electronics
* The [3D Printed Scanning Electron Microscope Project](https://hackaday.io/project/21831-3d-printed-scanning-electron-microscope)
  * A work in progress
  * Some nice magnetic lens simulations
  * The goals of his project are similar and I would love to get in touch and see if there are oportunities to collaborate. The focus for us starts with control and software for now



## Online Resources

* Joel.co.jp has some great resources:
  * Their easy to read overview and well illustrated [SEM A to Z](https://www.jeol.co.jp/en/applications/pdf/sm/sem_atoz_all.pdf)
  * Their glossary with detailed explanations, e.g. their [Stigmata](https://www.jeol.co.jp/en/words/semterms/search_result.html?keyword=stigmator) page
* https://cmrf.research.uiowa.edu/scanning-electron-microscopy

