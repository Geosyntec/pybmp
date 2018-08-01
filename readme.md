[![Build Status](https://travis-ci.org/Geosyntec/pybmpdb.svg?branch=master)](https://travis-ci.org/Geosyntec/pybmpdb)
[![codecov](https://codecov.io/gh/Geosyntec/pybmpdb/branch/master/graph/badge.svg)](https://codecov.io/gh/Geosyntec/pybmpdb)

# `pybmpdb`: A convenient interface between `wqio` and the International BMP Database.

## Data preparation

The data file provided with this package is, for all intents and purposes, "unprepared".
To load and prepare the data according to the procedure employed in the official analyses, use the `pybmp.summary.getSummaryData` function.

In short, `pybmp.prepare_data` does the following:

  1. Fill null result qualifiers with the "detected" qualifier ("=")
  1. Strip leaading and trailing whitespace from the remaining result qualifers
  1. Correct non-detect results to be 100% of the detection limit
  1. Normalize values in the `initialscreen`, `wqscreen`, and `catscreen` columns to either 'yes', 'no', or 'unknown'
  1. Make values in the `station` column to all lower case
  1. Normalize the `sampletype` column to either 'grab', 'composite', or 'unknown'
  1. Clean up the sample dates and times
  1. Makes of the pollutant names and fractions (e.g., dissolved, total) lower case
  1. Remove "Biofilter - " from "Biofileter - Grass Strip" and "Biofilter - Grass Swale"
  1. Assign the final `units` column as the preferred unit for each analyter per [the parameters dictionary](https://github.com/Geosyntec/pybmpdb/blob/master/pybmpdb/_parameters.py)
  1. Normalize the results based on their original units and final units per the [the units dictionary](https://github.com/Geosyntec/pybmpdb/blob/master/pybmpdb/_units.py)
  1. Remove duplicate values by selecting the maximum result, most restrictive qualifier, and first sample date based the following index columns:
      1. 'category'
      1. 'epazone'
      1. 'state'
      1. 'site'
      1. 'bmp'
      1. 'station'
      1. 'storm'
      1. 'sampletype'
      1. 'watertype'
      1. 'paramgroup'
      1. 'units'
      1. 'parameter'
      1. 'fraction'
      1. 'initialscreen'
      1. 'wqscreen'
      1. 'catscreen'
      1. 'balanced'
      1. 'bmptype'
      1. 'pdf_id'
      1. 'ws_id'
      1. 'site_id'
      1. 'bmp_id'

Then `pybmpdb.prep_for_summary` will:

  1. Select RP and WB data, combine into RP/WB, append to main dataset
  1. Select NO3 and NO2+NO3 data, combine into NOx, append to main dataset
  1. Remove data with "unknown" as a sample type
  1. Select all data where sample type is "composite", set aside as the "final" dataset
  1. Select all grab data for WB & RP BMP categories and biological parameters, append to "final" dataset
  1. Rename "PF" BMPs to "Permeable Friction Course"
  1. Then with that final dataset, go through each event and:
      1. Select (prefer) composite samples when both composite and grab samples exist
      1. Fall back to subsurface samples if an outflow sample is not available (reclassify as outflow)
      1. Fall back to reference samples in an inflow sample is not available (reclassify as inflow)
  1. Group by site ID, bmp ID, parameter, monitoring station and remove groups with fewer than 3 samples
  1. Group by bmp category, parameter, monitoring station and remove groups with fewer than 3 unique BMP IDs
  1. Pivot the monitoring stations into columns
      1. Group by site ID, bmp ID, parameter, & bmp category.
      1. Finally, remove all groups that are missing either outflow or inflow data entirely.
