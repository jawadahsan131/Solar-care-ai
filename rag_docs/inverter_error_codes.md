# Inverter Error Codes — Pakistan Household Guide

Reference document compiled from public sources. Not an official manufacturer manual. Always confirm against the physical inverter label and the brand's official support.

## Before you start

In Pakistan, inverter faults are often linked to extreme summer heat, dust, voltage fluctuation, weak grid supply, overloaded wiring, and batteries working hard during load-shedding. Before looking at a code, note these details:

- Inverter brand and full model number, for example `Growatt SPF 5000 ES` or `Inverex Nitrox 6 kW`.
- Exact code or message on the display or mobile app.
- Time it appeared: during load-shedding, at night, in strong sun, or when a heavy appliance started.
- Whether lights dimmed, a breaker tripped, or the inverter restarted.
- Whether the battery, cables, or inverter feel unusually hot.

**Safe homeowner checks only:** confirm breakers are on, reduce heavy loads, check that battery terminals are tight and clean, keep ventilation clear, and restart once only if the inverter manual allows it.

**Never do these:** open the inverter or battery, touch DC panel cables, bypass a breaker or protection device, pour water on electrical equipment, or keep resetting a repeated fault.

## Emergency red flags

Stop using the system and call a qualified solar installer or electrician immediately if you see:

- Burning smell, smoke, melted plastic, sparking, or discoloured wiring.
- Hot cables, hot battery terminals, or a hot inverter casing.
- Swollen, leaking, bulging, or unusually noisy battery.
- Electric shock, tingling from taps or metalwork, or water near electrical equipment.
- Repeated breaker tripping, especially after rain or a storm.
- An error that returns immediately after restart.

Photograph the inverter model, error code, and installation area before calling for help. Do not keep resetting the system.

## Growatt — SPF series

SPF models are commonly off-grid or hybrid inverters. The two-digit codes below are documented in Growatt SPF TL HVM manuals; exact behaviour can vary by model and firmware.

| Code | Meaning | Likely causes | Safe first checks | Call a pro if | Category |
|---|---|---|---|---|---|
| 01 | Fan is locked or not running | Dust blocking vents; fan failure; poor ventilation; hot room | Keep vents clear and ensure free airflow; do not open the unit | Fault persists, inverter is hot, or fan noise is abnormal | Inverter internal |
| 02 | Over temperature | Pakistani summer heat; direct sunlight; blocked ventilation; overload; fan issue | Move heat sources away; reduce AC, pump, iron, or microwave load; improve ventilation | Fault repeats or casing is hot | Inverter internal / appliance load |
| 03 | Battery voltage too high | Overcharged battery; wrong battery type/voltage setting; faulty battery or BMS | Check terminals are tight; confirm battery type and voltage setting from installation documents | Battery is swollen, hot, leaking, or smells unusual | Battery |
| 04 | Battery voltage too low | Deep discharge after long load-shedding; weak/old battery; loose terminals; excessive night use | Tighten and clean terminals; switch off non-essential loads; allow daytime charging | Battery does not recover, is damaged, or voltage remains very low | Battery |
| 05 | Output short circuit / over temperature | Short in house wiring; faulty appliance; overloaded output; internal fault | Turn off all output loads; restart with lights and fans only; add appliances one at a time | Fault returns with no load, or wiring shows heat damage | Inverter internal / household wiring |
| 06 | Output voltage too high | Inverter regulation issue; unstable output; wiring fault | Disconnect sensitive appliances such as TV, router, and computers | Fault persists with loads disconnected | Inverter internal |
| 07 | Overload time out | Too many appliances running; motor/compressor surge; undersized inverter | Turn off AC, water pump, iron, microwave, and freezer; restart essentials one by one | Fault repeats at normal household load | Inverter internal / appliance load |
| 08 | Bus voltage too high | Internal DC-bus fault; PV/input condition on some models | Switch off loads; do not open the inverter or alter DC wiring | Any repeat, burning smell, or tripping | Inverter internal / panel |
| 09 | Bus soft start failed | Internal start-up fault | Restart once only if the manual permits | Fault returns after one restart | Inverter internal |
| 51 | Over current or surge | Sudden heavy load; AC/pump compressor start; short circuit; internal fault | Disconnect heavy appliances; restart with essential loads only | Fault repeats, breaker trips, or cables become hot | Inverter internal / appliance load |
| 52 | Bus voltage too low | Weak battery/input supply; poor DC connection; internal issue | Check battery terminals are tight; reduce loads; allow battery charging | Fault persists after charging and tightening terminals | Battery / inverter internal |
| 53 | Inverter soft start failed | Internal start-up fault | Restart once only | Fault returns; do not keep resetting | Inverter internal |
| 55 | Over DC voltage in AC output | Internal conversion or output-control fault | Disconnect sensitive electronics; do not keep resetting | Any repeat; risk to appliances | Inverter internal |
| 56 | Battery connection open | Loose, corroded, broken battery cable/terminal; battery breaker off | With the inverter off, check terminals and cables are tight, clean, and undamaged | Cables are hot, damaged, or the fault remains | Battery / wiring |
| 57 | Current sensor failed | Internal sensing-component fault | Restart once only; record model and code | Fault persists | Inverter internal |
| 58 | Output voltage too low | Heavy overload; weak battery; internal output issue | Reduce loads; check battery terminals; allow charging | Fault persists after load reduction and charging | Battery / inverter internal |
| 60 | Negative power fault | Unexpected reverse power flow or control fault | Switch off non-essential loads; do not modify wiring | Fault repeats | Inverter internal |
| 80 | CAN fault | Communication fault between inverter and lithium battery/BMS | Reseat the battery communication cable; restart inverter and battery in the order given by manuals | Fault persists, battery app is offline, or battery is hot | Communication / battery |
| 81 | Host loss | Communication loss with battery or host device | Check communication cable seating; restart equipment in the correct order | Fault persists | Communication / battery |

**Additional codes not confidently documented.** Growatt SPF variants use different code tables. Always use the manual for the exact model.

### Pakistan-specific note

During long load-shedding, do not keep adding heavy loads after a low-battery warning. Let the battery recover with solar or grid charging before running AC, pump, iron, or freezer loads again.

### Sources consulted

- Growatt official downloads: https://en.growatt.com/support/download/manual-quick-guide
- Growatt SPF TL HVM user manual fault reference: https://shidenergy.com/wp-content/uploads/2026/06/manual_growatt_spf_tl_hvm.pdf
- Growatt error-code overview compiled from official manuals: https://solarleyte.com/posts/growatt-inverter-error-codes

## Growatt — MIN series

MIN models are commonly grid-tied or hybrid inverters and often use three-digit codes. The exact set differs across MIN, MIN-X, MIN-XH, and newer hybrid models.

| Code | Meaning | Likely causes | Safe first checks | Call a pro if | Category |
|---|---|---|---|---|---|
| 101 | Grid voltage too high | Weak/unstable local grid; loose grid connection; wrong grid setting | Confirm the main grid breaker is on; ask the installer to verify grid settings | Fault repeats, especially during evening voltage swings | Grid |
| 102 | Grid voltage too low | Weak grid supply; loose connection; incorrect grid setting | Confirm grid breaker is on; check whether neighbours also have low voltage | Fault repeats or house lights dim | Grid |
| 103 | Grid frequency out of range | Grid frequency instability; wrong country/grid setting | Do not change grid settings yourself; note the time of fault | Fault repeats | Grid |
| 104 | Grid lost / no grid | Load-shedding, utility outage, tripped grid breaker, loose AC cable | Confirm grid breaker is on; check whether the area has power | Power is present but the inverter still reports no grid | Grid / wiring |
| 105 | Grid fault | Abnormal grid voltage/current or wiring issue | Switch off the inverter AC breaker only if it is safe and clearly labelled | Fault repeats after grid returns | Grid / wiring |
| 106 | Islanding protection | Inverter detects an unsafe grid condition and disconnects | Wait for stable grid supply; never bypass anti-islanding protection | Fault repeats when grid is stable | Grid / inverter internal |
| 107 | DC injection too high | Inverter output-control or internal fault | Do not keep resetting; record code and time | Any repeat | Inverter internal |
| 108 | Leakage current too high | Moisture, damaged DC/AC wiring, panel insulation issue, internal fault | Keep away from wet equipment; do not touch panels or cables | Any repeat, especially after rain or burning smell | Panel / wiring / inverter internal |
| 109 | Insulation resistance too low | Wet/damaged DC wiring, degraded panel insulation, internal issue | Do not touch panels or DC cables; keep area dry | Fault repeats after dry weather | Panel / wiring / inverter internal |
| 110 | PV voltage too high | Too many panels in series; wrong string design; cold-weather voltage rise | Do not add or rearrange panels yourself | Any repeat; risk of equipment damage | Panel / inverter internal |
| 111 | PV voltage too low | Insufficient sunlight, shading, panel/string fault, loose DC connection | Check for obvious shading or heavy dust from ground level; do not climb the roof | Fault persists in good sunlight | Panel / wiring |
| 112 | PV input configuration error | Strings connected incorrectly or incompatible PV arrangement | Do not change DC wiring yourself | Any occurrence | Panel / wiring |
| 201 | Communication fault | Inverter-to-monitoring or internal communication issue | Restart the inverter once; check Wi‑Fi/router if the app is affected | Fault persists | Communication |
| 202 | EEPROM fault | Internal memory/component fault | Record code and model; do not open unit | Any occurrence | Inverter internal |
| 301 | Over temperature | Heat, poor ventilation, overload, or fan issue | Improve airflow; reduce heavy loads | Fault repeats or unit is hot | Inverter internal |
| 302 | Temperature sensor fault | Internal sensor or control-board issue | Restart once only | Fault persists | Inverter internal |
| 402 | GFCI / residual-current fault | Leakage current, moisture, wiring insulation issue, internal fault | Do not touch panels, DC cables, or wet equipment | Any occurrence; potential shock risk | Panel / wiring / inverter internal |
| 404 | DSP data mismatch | Internal control/sampling fault | Restart once only | Fault persists | Inverter internal |
| 405 | EEPROM fault | Internal memory fault | Record code; do not open unit | Any occurrence | Inverter internal |
| 408 | DSP/M3 communication abnormal | Internal communication fault | Restart once only | Fault persists | Inverter internal |
| 409 | Bus over voltage | Internal DC-bus overvoltage; sometimes PV/input related | Do not open the inverter; do not alter PV wiring | Any occurrence | Inverter internal / panel |
| 411 | Over temperature | Heat, ventilation, overload, or fan issue | Improve airflow; reduce loads | Fault repeats | Inverter internal |
| 414 | Relay fault | Internal relay or grid-connection issue | Do not bypass protection | Any occurrence | Inverter internal / grid |
| 417 | Bus sample fault | Internal measurement/control fault | Restart once only | Fault persists | Inverter internal |
| 420 | Relay fault | Internal relay or grid-connection issue | Do not bypass protection | Any occurrence | Inverter internal / grid |

**Meaning varies; commonly reported as above.** A code on one Growatt MIN model may not mean the same thing on another. Confirm the exact model and manual.

### Pakistan-specific note

Frequent `101`, `102`, `103`, or `104` faults during evening hours can point to local grid-voltage problems rather than a panel issue. Do not ask anyone to change grid-protection settings without utility/installer approval.

### Sources consulted

- Growatt MIN 2.5–6K TL-X user manual: https://enertik.com/wp-content/uploads/sites/1/documentos/manuales/manual_growatt_min.pdf
- Growatt official downloads: https://en.growatt.com/support/download/manual-quick-guide
- Growatt MIN/MOD/MID error-code index compiled from manuals: https://en.pvgroup.pl/wiedza/growatt/kody-bledow-growatt-min-mod/
- Growatt error-code overview compiled from official manuals: https://solarleyte.com/posts/growatt-inverter-error-codes

## Inverex — Aerox, Nitrox, Veyron series

Inverex models vary substantially. Some use numbered codes and others display text messages. The following are commonly reported Inverex-family codes, but meanings can differ by model and firmware. Use this for triage, not as a model-specific manual.

| Code | Meaning | Likely causes | Safe first checks | Call a pro if | Category |
|---|---|---|---|---|---|
| 01 | Fan is locked or not running | Dust, blocked vents, fan failure | Keep vents clear; do not open the unit | Fault persists or unit is hot | Inverter internal |
| 02 | Over temperature | Heat, poor ventilation, overload, fan issue | Reduce heavy loads; improve airflow | Fault repeats or burning smell | Inverter internal |
| 03 | Battery voltage too high | Overcharge, wrong battery setting, faulty battery/BMS | Check terminals are tight; confirm battery type/setting with documentation | Battery swollen, hot, leaking, or smelly | Battery |
| 04 | Battery voltage too low | Deep discharge, aged/faulty battery, poor terminals, excessive night use | Tighten/clean terminals; reduce loads; allow solar charging | Battery will not recover or is damaged | Battery |
| 05 | Output short circuit / over temperature | Short circuit, overloaded output, internal fault | Turn off loads; restart with essentials only | Fault returns with no load | Inverter internal / household wiring |
| 06 | Output voltage abnormal | Internal regulation issue or severe output fault | Disconnect sensitive appliances | Fault persists | Inverter internal |
| 07 | Overload time out | Too much load or motor/compressor surge | Turn off AC, pump, iron, microwave; add loads slowly | Fault repeats at normal load | Inverter internal / appliance load |
| 08 | Bus voltage too high | Internal DC-bus fault; PV/input issue on some models | Do not open the unit or alter DC wiring | Any repeat | Inverter internal / panel |
| 09 | Bus soft start failed | Internal start-up fault | Restart once only if manual permits | Fault returns | Inverter internal |
| 11 | Main relay failed | Internal relay or output-control fault | Do not bypass protection | Any occurrence | Inverter internal |
| 51 | Over current or surge | Sudden heavy load, motor start, short circuit | Disconnect heavy appliances; restart essentials only | Fault repeats or wiring is hot | Inverter internal / appliance load |
| 52 | Bus voltage too low | Weak battery/input, poor DC connection, internal issue | Check battery terminals; reduce loads; charge battery | Fault persists | Battery / inverter internal |
| 53 | Inverter soft start failed | Internal start-up fault | Restart once only | Fault returns | Inverter internal |
| 55 | Over DC voltage in AC output | Internal conversion/output-control fault | Disconnect sensitive electronics | Any occurrence | Inverter internal |
| 56 | Battery connection open | Loose, broken, or corroded battery cable/terminal | With power off, check terminals and cables are tight and clean | Cables hot/damaged or fault remains | Battery / wiring |
| 57 | Current sensor failed | Internal sensing fault | Restart once only | Fault persists | Inverter internal |
| 58 | Output voltage too low | Overload, weak battery, internal output issue | Reduce loads; charge battery | Fault persists | Battery / inverter internal |
| 60 | Negative power fault | Unexpected reverse power flow or control fault | Switch off non-essential loads | Fault repeats | Inverter internal |
| 80 | CAN communication fault | Battery/BMS communication cable or settings issue | Reseat communication cable; restart per manual | Fault persists or battery app offline | Communication / battery |
| 81 | Host loss | Communication loss with battery/host device | Check cable seating; restart in correct order | Fault persists | Communication / battery |

**Meaning varies; commonly reported as above.** Aerox, Nitrox, and Veyron are different Inverex product families. A code on one model may not mean the same thing on another.

### Pakistan-specific note

If faults appear mainly when the WAPDA/grid supply returns after load-shedding, do not repeatedly restart the inverter. Voltage spikes and unstable return supply can trigger protection; have the installer check protection settings, earthing, and wiring.

### Sources consulted

- Inverex Nitrox 6 kW user manual, fault-information section: https://www.scribd.com/document/726131645/Inverex-Nitrox-6kw-User-Manual
- Comparable hybrid-inverter fault-code table used to identify commonly reported Inverex-family codes: https://fr.scribd.com/document/340353733/UPS-Manual

## Solis — S6 series

Solis S6 inverters commonly display an alarm message with a four-digit code. Many are inverter-protection faults that require an installer rather than a homeowner reset.

| Code | Meaning | Likely causes | Safe first checks | Call a pro if | Category |
|---|---|---|---|---|---|
| 1011 — UN-G-V | Grid voltage abnormal / utility voltage out of range | Weak or unstable grid; loose AC connection; wrong grid setting | Confirm grid breaker is on; check whether the wider area has power problems | Fault repeats when grid is normal | Grid |
| 1014 — Backfeed-Iac | Backfeed / abnormal AC current condition | Grid or wiring issue; internal protection event | Do not modify wiring; note code and time | Any occurrence | Grid / wiring / inverter internal |
| 1015 — NO-Grid | No grid detected | Load-shedding, utility outage, tripped grid breaker, loose AC cable | Confirm grid breaker is on; check whether neighbours have power | Grid is present but fault remains | Grid / wiring |
| 1031 — INI-FAULT | AD zero drift over limit / initialisation fault | Internal measurement or control-board issue | Restart once only if safe | Fault persists | Inverter internal |
| 1035 — RelayChk-FAIL | Relay check failed | Internal relay or grid-connection protection issue | Do not bypass protection | Any occurrence | Inverter internal / grid |
| 1037 — DCInj-FAULT | DC injection current exceeds limit | Internal output-control fault | Do not keep resetting; disconnect sensitive appliances | Any occurrence | Inverter internal |
| 1041 — ARC-FAULT | Arc-fault / primary-secondary DSP communication abnormal | Internal communication or arc-detection event; wiring issue | Keep clear of the inverter; do not open it | Any occurrence; potential fire risk | Inverter internal / wiring |
| 1057 — Overload Fault | Connected load exceeds inverter limit | Too many appliances; motor/compressor surge; undersized inverter | Turn off heavy loads; restart essentials one at a time | Fault repeats at normal load | Inverter internal / appliance load |

**Additional codes not confidently documented.** Solis S6 alarm tables differ by model, region, and firmware. The Solis service centre provides a full alarm-code overview, but homeowners should not attempt internal repairs.

### Pakistan-specific note

`1011` and `1015` are common during load-shedding, weak grid periods, or when the grid returns after an outage. If the code disappears when normal grid supply returns, it is usually a grid condition rather than a panel problem—but repeated occurrences still need an installer check.

### Sources consulted

- Solis S6-GR1P user manual: https://www.solisinverters.com/uploads/file/Solis_Manual_S6-GR1P(2,5-6)K-S_FN_EUR_V1,1(20240429).pdf
- Solis S6-EH3P user manual: https://roshanex.pk/wp-content/uploads/2026/11/Solis_Manual_S6-EH3P(75-125)K10-NV-YD-H_EUR_V1120260716.pdf
- Solis S6-EH3P user manual, 5–18 kW variant: https://roshanex.pk/wp-content/uploads/2026/11/Solis_Manual_S6-EH3P8-18K02-NV-YD-L_EUR_V1320260820.pdf
- Solis service knowledge base, alarm/error messages: https://solis-service.solisinverters.com/en/support/solutions
- Solis troubleshooting page: https://solis-service.solisinverters.com/en/support/solutions/44000061714
