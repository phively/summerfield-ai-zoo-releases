# Cairn Mesh R6 Installation and Port Guide

> Synthetic test fixture. This document describes fictional hardware and is not real product guidance.

- **Publisher:** Cairn Systems Documentation
- **Applies to:** Cairn Mesh R6, firmware 4.2.1
- **Revision:** 4.2.1-R3, published 2026-08-14

## Ethernet ports

- Port 1 is a 2.5 GbE WAN port.
- Port 2 is a 1 GbE LAN port.
- A wired device negotiating at 1 GbE on port 2 is using the port's rated link speed. Typical application throughput is lower than the negotiated link rate; this guide does not define one guaranteed speed-test result.
- The R5 port layout does not apply to the R6.

## Reboot and diagnostic notes

The manufacturer provides no required reboot sequence for a speed-test discrepancy. Record the device model, firmware, port, negotiated link rate, test method, and observed result before requesting support. Do not infer a failed device from one speed-test result.
