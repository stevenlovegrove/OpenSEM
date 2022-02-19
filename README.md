# OpenSEM Project

**Status:** Preliminary

The purpose of this project is to create a modern and open-source hardware and software platform for using vintage and custom scanning electron microscopes (SEM's). Let's get these powerful machines into more peoples hands and help enable their use in more fields of study and in enthusiast operation.

Vintage columns can be found at auctions and online for relatively little, but the control stations that *complete* systems come with are often inpractically large for most spaces, and significantly increase transportation and resporation cost and complexity. Can we make these machines more practical by incorporating miniturized electronics from the 21st century?

Beside imaging, scanning electron microscopes are also a fantastic tool in nano-fabrication when equiped with a few extra tools. Electron-beam lithography can be used to etch tiny features for custom silicon or micro optical designs. We aspire to enable such applications for the determined novice.

## Project Goals

#### Document Interfaces for existing machines

Provide a de-facto reference for understanding the electrical and mechanical operation and interfaces to existing machines.

* [Cambridge StereoScan 260](sem_info/cambridge_stereoscan_260/README.md)

#### Reference Power Supply Options & Designs

* Provide a shoppers reference for available power supply options and requirements.
* Control software for common power supplies to incorporate within integrated software package
* Custom, miniturized designs targeting a complete SEM, perhaps.

#### Reference analog amplifier Options & Designs

* There are various sensors which can be used in a SEM machine. These typically involve low current signals which must be buffered and amplified before digitization.

#### Flexible Reference Open Control Boards

An open and low(ish) cost design for the synchronized beam control, sensor digitization and host transfer of SEM images.

* Preliminary FPGA design based on Xilinx Arts-7 and FTDI 600 USB 3.0 controller
  [FPGA HLS Design](https://github.com/stevenlovegrove/OpenSEM/tree/main/open_sem)



## Online Resources

* The most well known are the legendry Applied Sciences SEM [videos](https://www.youtube.com/watch?v=VdjYVF4a6iU)
* The [3D Printed Scanning Electron Microscope Project](https://hackaday.io/project/21831-3d-printed-scanning-electron-microscope)

* Joel.co.jp has some great resources:
  * Their easy to read overview and well illustrated [SEM A to Z](https://www.jeol.co.jp/en/applications/pdf/sm/sem_atoz_all.pdf)
  * Their glossary with detailed explanations, e.g. their [Stigmata](https://www.jeol.co.jp/en/words/semterms/search_result.html?keyword=stigmator) page
* https://cmrf.research.uiowa.edu/scanning-electron-microscopy

