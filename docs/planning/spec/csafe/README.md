# PM5 CSAFE Specification — Machine-Readable YAML

Machine-readable extraction of the **Concept2 PM CSAFE Communication Definition**,
Revision 0.25 (2023-03-23), 161 pages.

## Source Document

**Title:** PM5 CSAFECommunicationDefinition_0.pdf \
**Revision:** 0.25 \
**Date:** March 23, 2023 \
**Pages:** 161
**Source**:* [Concept2 PM5 CSAFE Communication Definition](https://www.concept2.com/support/software-development)

## Files

| File | Lines | Section | Content |
| --- | ---: | --- | --- |
| `enums.yaml` | 672 | Appendix A (pp93-103) | 28 enumerated types, 350 values, 2 constant groups |
| `ble_services.yaml` | 1,786 | §2 (pp5-24) | 5 BLE GATT services, 27 characteristics, field-level byte layouts |
| `protocol.yaml` | 448 | §3-4 (pp25-34) | CSAFE framing, byte stuffing, checksums, timing constraints |
| `commands_public.yaml` | 1,522 | §5-6 (pp35-44) | 86 public CSAFE commands (short + long) |
| `commands_c2.yaml` | 1,560 | §7-9 (pp45-75) | 182 Concept2 proprietary commands |
| `data_formats.yaml` | 1,166 | §2 (pp5-24) | BLE notification data struct layouts (byte-level) |
| `workout_setup.yaml` | 1,420 | §10 (pp76-92) | Workout programming sequences with sample byte vectors |
| `formulas.yaml` | 405 | Appendix B-C (pp104-109) | Pace/watts/calorie conversions, data representation rules |
| `errors.yaml` | 1,307 | Appendix D (pp110-160) | 747 error codes across 78 modules |
| **Total** | **10,286** | | |

## Usage

All files use standard YAML and can be loaded with any YAML parser:

```python
import yaml

with open("docs/planning/spec/csafe/enums.yaml") as f:
    enums = yaml.safe_load(f)

# Access a specific enum
stroke_state = enums["enums"]["StrokeState"]
for name, value in stroke_state["values"].items():
    print(f"{name} = {value}")
```

## Known Discrepancies

**Error code duplicates** — 74 error names appear twice in the spec with different
numeric values, representing the same logical error on different PM hardware
generations (PM3/PM4 range ~1-2600 vs PM5/nRF52 range ~10000-12000). Second
occurrences are suffixed with `__V2` in `errors.yaml`.
