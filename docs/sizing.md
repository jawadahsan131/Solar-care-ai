# Solar sizing estimates

The sizing engine uses the user's appliance list and hourly schedule. It does not
use machine learning. Watts mean running input power, kW means kilowatts, and
kWh means energy.

- Daily energy is the sum of quantity × watts × duty factor × the fraction of
  each hour the appliance is on.
- Night energy uses the same calculation for hours 18:00–06:59; day energy is
  the remaining hours.
- Peak load uses running watts and the hourly schedule without duty factors,
  plus the largest single-unit startup surge.
- Inverter size is the next standard size at or above peak load with a 25%
  margin.
- On-grid panels use daily kWh divided by peak-sun-hours × system efficiency.
- Hybrid panels add a 10% margin; the battery covers essential running load for
  the configured outage duration.
- Off-grid panels add a 15% cloud margin; the battery covers night energy for
  the configured autonomy period.

These are planning estimates, not an installation design. Real appliance labels,
site conditions, battery limits, and local electrical requirements must be
checked by a qualified installer.
