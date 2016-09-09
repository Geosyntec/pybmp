[![Build Status](https://travis-ci.org/Geosyntec/pybmpdb.svg?branch=master)](https://travis-ci.org/Geosyntec/pybmpdb)
[![Coverage Status](https://coveralls.io/repos/Geosyntec/pybmpdb/badge.svg?branch=master&service=github)](https://coveralls.io/github/Geosyntec/pybmpdb?branch=master)

# `pybmpdb`: A convenient interface between `wqio` and the International BMP Database.

## Data preparation

The data file provided with this package is, for all intents and purposes, "unprepared".
To load and prepare the data according to the procedure employed in the official analyses, use the `pybmp.summary.getSummaryData` function.

In short, `pybmp.summary.getSummaryData` does the following:

  1. Load the raw data
  1. Select NO3 and NO2+NO3 data, combine into NOx, append to main dataset
  1. Select RP and WB data, combine into RP/WB, append to main dataset
  1. Remove data with “unknown” as a sample type
  1. Select all data where sample type is “composite”, set aside as the “final” dataset
  1. Select all grab data for WB, RP, and paramgroup = “Biological”, append to “final” dataset 
  1. Then with that final dataset, go through each event and:
    1. Select (prefer) composite samples when both composite and grab samples exist
    1. Fall back to subsurface samples if an outflow sample is not available (reclassify as outflow)
    1. Fall back to reference samples in an inflow sample is not available (reclassify as inflow)
    1. Group by site ID, bmp ID, parameter, monitoring station and remove groups with fewer than 3 samples
    1. Group by bmp category, parameter, monitoring station and remove groups with fewer than 3 unique BMP IDs
    1. Pivot the monitoring stations into columns, then Group by site ID, bmp ID, parameter, & bmp category. Finally then remove all groups that are missing either outflow or inflow data entirely.

