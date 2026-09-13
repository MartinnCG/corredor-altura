# Analytical v1 release audit

**Status:** release candidate hardening  
**Analytical scope:** km 0–130  
**Unit of analysis:** 130 calibrated one-kilometre segments

## Purpose

This document defines the evidence required before tagging the current
analytical product as `v1.0`. The release freezes the existing model and
published outputs; it does not claim predictive capability or extend the
validated corridor.

## Frozen analytical contract

The release candidate is expected to preserve:

- exactly 130 ordered segment keys from `(0, 1)` through `(129, 130)`;
- a unique `(km_inicio, km_fin)` key in every canonical dataset;
- 46 columns and no blank values in the master feature table;
- exposure rankings containing every integer from 1 through 130 exactly once;
- exposure scores that are finite and remain within the documented 0–100 scale;
- exposure classes restricted to the five documented relative classes;
- exact agreement of score, ranking and class between the model output and
  operational-validation table.

These invariants are checked by
`tests/test_analytical_v1_contract.py` using only the Python standard library.

## Canonical release datasets

| Dataset | Release role |
|---|---|
| `data/processed/segmentos.csv` | Calibrated segment identity and geometry measures |
| `data/processed/features_segmentos_master.csv` | Consolidated analytical feature contract |
| `data/processed/indice_exposicion_segmentos.csv` | Published relative-exposure output |
| `data/processed/validacion_indice_exposicion.csv` | Independent operational-evidence comparison |

Spatial layers and visual products remain important deliverables, but this
initial automated gate focuses on lightweight tabular contracts that can run
reliably in GitHub Actions.

## Automated evidence

The workflow `.github/workflows/analytical-v1-quality.yml` runs the contract
suite on:

- every pull request targeting `master`;
- every push to `master`.

A passing workflow demonstrates internal consistency of the committed release
artifacts. It does not prove source accuracy, causality, operational safety or
predictive performance.

## Manual gates before tagging v1.0

- [ ] Confirm provenance and redistribution terms for every committed source.
- [ ] Confirm that the IPER-derived material is authorized for public release.
- [ ] Review GPS control points and field-derived records for location or
      operational sensitivity.
- [ ] Confirm that no personal, confidential or client-identifying information
      is present in documents, attributes or file metadata.
- [ ] Run the complete pipeline from documented inputs in a clean environment.
- [ ] Record runtime, environment and any manual QGIS steps required.
- [ ] Confirm that generated tables and spatial outputs match the committed
      release candidate.
- [ ] Create the `v1.0` tag only after automated and manual gates pass.

## Known limitations

The release retains the limitations documented in the project README:

- exposure is relative within this corridor and is not absolute risk;
- there is no target variable sufficient for predictive failure modelling;
- operational evidence is not spatially homogeneous;
- ERA5-Land and DEM resolution constrain local interpretation;
- validated analytical coverage ends at km 130.

## V2 boundary

V2 begins only after the v1 release is frozen. Its first phase should audit
architecture and reproducibility, then define data contracts, orchestration,
dataset versioning, QA/observability and repeatable deployment. New model
claims or dashboard features are not part of the v1 release gate.
