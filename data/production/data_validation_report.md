# Panchayat Static Data — Validation Report

Source file row count: **436,653**  
Unique GPCODEs found: **239**  
Expected (per handover doc): **239**

## 1. GPCODE Uniqueness / Duplicate Mapping

- Duplicate `DATE + GPCODE` rows in raw file: **0**
- GPCODEs mapped to more than one GPNAME (ambiguous identity): **0**

## 2. Static Feature Consistency (GPNAME / BLOCK / ELEVATION / SLOPE / LANDCOVER)

- GPCODEs with date-wise mismatch in >=1 static column: **0**
  (NOT auto-resolved to a majority value — left blank in metadata and routed to
  manual review. These GPCODEs are also excluded from the production sample file.)

## 3. LANDCOVER Contract Check — allowed values {4, 10, 12, 13}

- Panchayats with a VALID landcover value: **239**
- Panchayats with an INVALID (out-of-contract) landcover value: **0**
- Panchayats with LANDCOVER missing entirely: **0**

## 3b. GPCODEs Requiring Manual Review

- Total GPCODEs with unresolved static mismatch (blank in metadata, excluded from production sample): **0**

## 4. Missing Static Values (reported only — nothing auto-filled)

- GPCODEs with one or more fully-missing static fields: **0**

## 5. RAINFALL Target Completeness (cross-check vs handover doc)

- Rows with missing RAINFALL: **3,654**
- Panchayats affected: [111755, 111773]
- Excluded from ML train/val/test only; retained in master file (handover Sec. 6).

## 6. Summary

- **Overall static data status: CLEAN**
- No values were auto-filled or guessed. Flagged GPCODEs need manual source-data correction before backend use.