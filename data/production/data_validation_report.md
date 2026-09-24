# 📊 Panchayat Static Data & Target Validation Report
**Project:** Smart Panchayat Climate & Weather Downscaling (SIH 2026)
**District:** Dhanbad, Jharkhand | **Target Region:** 10 Administrative Blocks
**Generated:** Production Validation Pipeline

---

## 1. Dataset Overview

| Metric | Value | Expected / Contract |
| :--- | :--- | :--- |
| **Total Rows** | `436,653` | 436,653 rows (239 Panchayats × 1,827 days) |
| **Total Columns** | `13` | 13 columns |
| **Date Range** | `2020-01-01` to `2024-12-31` | 5 full years (2020-01-01 to 2024-12-31) |
| **Total Unique Dates** | `1,827` days | 1,827 calendar days |
| **Unique GPCODEs** | `239` | 239 Gram Panchayats |
| **Unique GPNAMEs** | `233` | 233 unique strings |
| **Administrative Blocks** | `10` | `['Baghmara', 'Baliapur', 'Dhanbad', 'Egarkund', 'Govindpur', 'Kaliasol', 'Nirsa', 'Purvi Tundi', 'Topchanchi', 'Tundi']` |

### Columns Audited
`DATE, GPCODE, GPNAME, BLOCK, RAINFALL, REFERENCE_RAINFALL, TEMPERATURE, HUMIDITY, WIND, ET, ELEVATION, SLOPE, LANDCOVER`

## 2. Identity & Primary Key Integrity

- **Duplicate `DATE + GPCODE` combinations:** `0` (Passed)
- **Full duplicate rows:** `0` (Passed)
- **GPCODE mapped to multiple GPNAMEs:** `0` (Passed)

> [!NOTE]
> **Homonymous Panchayat Names (6 instances across different blocks):**
> Several Panchayats share identical names across distinct administrative blocks. `GPCODE` serves as the sole immutable primary key:
> - **KANCHANPUR**: `111745` (Baghmara), `111833` (Govindpur)
> - **KARMATAND**: `111796` (Baliapur), `111834` (Govindpur)
> - **MOHLIDIH**: `111762` (Baghmara), `112026` (Purvi Tundi)
> - **PRADHANKHANTA**: `111800` (Baliapur), `112005` (Topchanchi)
> - **RAGHUNATHPUR**: `111772` (Baghmara), `112029` (Purvi Tundi)
> - **RATANPUR**: `111847` (Govindpur), `112032` (Tundi)

## 3. Static Feature Consistency

Verification that `GPNAME`, `BLOCK`, `ELEVATION`, `SLOPE`, and `LANDCOVER` remain perfectly invariant across all 1,827 daily timestamps per GPCODE:

- **Static mismatches detected:** `0`
- **Missing static fields:** `0`

## 4. LANDCOVER Contract Validation

The frozen ML model contract strictly permits only LANDCOVER classes: `{4, 10, 12, 13}`.

- **Valid LANDCOVER Panchayats:** `239` / `239`
- **Invalid (Out-of-Contract) LANDCOVER:** `0`
- **Missing LANDCOVER:** `0`

| LANDCOVER Code | Description / Class | Panchayat Count | Percentage |
| :--- | :--- | :--- | :--- |
| `4` | Valid Contract Class | 1 | 0.42% |
| `10` | Valid Contract Class | 13 | 5.44% |
| `12` | Valid Contract Class | 203 | 84.94% |
| `13` | Valid Contract Class | 22 | 9.21% |

## 5. Rainfall Target Completeness (`RAINFALL`)

Audit of the supervised prediction target (`RAINFALL`) in `master_dataset_v2.csv`:

- **Total Missing `RAINFALL` Rows:** `3,654` (0.837% of total records)
- **Affected Panchayats:** `2` Panchayats

| GPCODE | GPNAME | BLOCK | Missing Dates Count | Coverage Missing |
| :--- | :--- | :--- | :--- | :--- |
| `111755` | MAHESHPUR 2 | Baghmara | 1,827 | 100.0% (All 5 Years) |
| `111773` | RAJGANJ | Baghmara | 1,827 | 100.0% (All 5 Years) |

> [!IMPORTANT]
> As per project specifications, these 2 Panchayats (`111755` MAHESHPUR 2 and `111773` RAJGANJ) are retained untouched in `master_dataset_v2.csv`.
> They are excluded from ML model evaluation/training partitions, and their static metadata remains completely intact.

## 6. Final Status & Summary

### **Production Metadata Status: `CLEAN`**

- **Total Panchayats:** `239`
- **Clean Panchayats:** `239` (100.0%)
- **Static Mismatches:** `0`
- **Invalid LANDCOVER:** `0`
- **Missing LANDCOVER:** `0`
- **Missing Static Fields:** `0`
- **Duplicate DATE+GPCODE:** `0`
- **Missing RAINFALL Rows:** `3,654` (restricted to 2 identified Panchayats)

**Conclusion:** All 239 Panchayats possess verified, invariant, and contract-compliant static metadata ready for backend ingestion.
