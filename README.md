# GemStone-Profiler Automate
----------------------------
This project automates the process of running experiments on Arm-based development boards. It executes a set of given workloads on any specified core mask and CPU frequency (frequency of multiple clusters can be set independently) while simultaneously recording hardware Performance Monitoring Counters (PMCs), as well as temperature, voltage and power if the platform supports this. It supports both ARMv7 and ARMv8 architectures. 

More details available at [GemStone](https://gemstone.ecs.soton.ac.uk)

This project works alongside GemStone-Profiler Logger, which handles the logging of PMCs and other variables from the device under test. 

## Dependencies
---------------
+ GemStone-Profiler Logger
+ cpufrequtils
+ Python 2.7, numpy, pandas

## Getting Started
------------------
TODO

## Authors
----------
Matthew Walker - [University of Southampton](https://www.southampton.ac.uk)

## License
----------
This project is licensed under the 3-clause BSD license. See LICENSE.md for details.

