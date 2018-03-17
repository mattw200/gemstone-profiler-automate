# GemStone-Profiler Automate

This project automates the process of running experiments on Arm-based development boards. 
It executes a set of given workloads on any specified core mask and CPU frequency 
 (frequency of multiple clusters can be set independently) while simultaneously 
 recording hardware Performance Monitoring Counters (PMCs), as well as temperature, 
 voltage and power if the platform supports this. 
 It supports both the ARMv7 and ARMv8 architectures. 

More details available at [GemStone](http://gemstone.ecs.soton.ac.uk)

This project works alongside [GemStone-Profiler Logger](https://github.com/mattw200/gemstone-profiler-logger), 
which handles the logging of PMCs and other variables 
from the device under test. 

## Dependencies

+ GemStone-Profiler Logger
+ cpufrequtils
+ Python 2.7, numpy, pandas

## Getting Started

For detailed usage instructions, check out the [GemStone Profiler Automate Tutorial](http://gemstone.ecs.soton.ac.uk/gemstone-website/gemstone/tutorial-gemstone-profiler-automate.html).

## Authors

[Matthew J. Walker](mailto:mw9g09@ecs.soton.ac.uk) - [University of Southampton](https://www.southampton.ac.uk)

This project supports the paper:
>M. J. Walker, S. Bischoff, S. Diestelhorst, G V. Merrett, and B M. Al-Hashimi,
>["Hardware-Validated CPU Performance and Energy Modelling"](http://www.ispass.org/ispass2018/),
>in IEEE International Symposium on Performance Analysis of Systems and Software (ISPASS), 
> Belfast, Northern Ireland, UK, April, 2018 [Accepted]

This work is supported by [Arm Research](https://developer.arm.com/research), 
[EPSRC](https://www.epsrc.ac.uk), and the [PRiME Project](http://www.prime-project.org).


## License

This project is licensed under the 3-clause BSD license. See LICENSE.md for details.
