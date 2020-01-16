[![Build Status](https://travis-ci.org/Geosyntec/pybmpdb.svg?branch=master)](https://travis-ci.org/Geosyntec/pybmpdb)
[![codecov](https://codecov.io/gh/Geosyntec/pybmpdb/branch/master/graph/badge.svg)](https://codecov.io/gh/Geosyntec/pybmpdb)

# `pybmpdb`: A convenient interface between `wqio` and the International BMP Database.

## Data preparation

### Intitial Prep

The data are prepared for the BMP Database in the following ways:

1. Fetch Site data from the DOT Sites endpoint (`/DOTSites`), rename columns (see column mapping section)
1. Fetch BMP Category data from the BMP Code endpoint `(/vBMPCodes)`, rename columns (see column mapping section)
1. Fetch WQ data from the raw WQ Flat File endpoint (`/WQFlatFile`), rename columns (see column mapping section)
1. Select only WQ Data where the 'webscreen' column is "y"
1. Drop any rows with nulls in the "units" column (there should be 0 rows that meet this condition)
1. Fill nulls in the 'epazone' column with -99, convert column to an integer type
1. Convert the "storm" (event) column to an integer type
1. Create a "bmpcode" column that is equal to the "bmptype" column when the "_category" column is 'Manufactured Device', otherwise use the "_catcode" column
1. Join in the BMPCodes dataset on the "bmpcode" and "category" columns
1. Drop any rows with nulls in the "ws_id" columns (there should be 0 rows that meet this condition)
1. Pipe the resulting dataset to `pybmpdb._clean_raw_data, which does the following:
    1. Fills nulls in the "qual" column with '='
    1. Drops rows with nulls in the "res" column
    1. Any leading or trailing whitespace from values in the "qual" column
    1. Standardizes values in the "wq_initialscreen" column to either 'y' or 'n'
    1. Standardizes values in the "ms_indivscreen" column to either 'y' or 'n'
    1. Standardizes values in the "wq_catscreen" column to either 'y' or 'n'
    1. Makes values in the "station" column fully lower case (e.g., 'Inflow' becomes 'inflow')
    1. Standardizes values in the "sampletype" column to either 'composite', 'grab', or 'unknown'
    1. Combines the "sampledate" and "sampletime" columns in a column called "sampledatetime"
    1. Normalize all results to the "preferred units" for each parameter ![See here for more info](https://github.com/Geosyntec/pybmpdb/blob/master/pybmpdb/_parameters.py)
    1. Creates and fills a "fraction" column with either 'total' or 'dissolved'
    1. Filter out results where the "res" column is less than 0 (there should be 0 rows that meet this condition)
    1. Checks that none of the "header" columns have null values (header columns together should uniquely define each observation and are listed below)
    1. Group the dataset by the "header" column, compute the mean of the "res" column, minimum of the "qual" column, and minimum of the "sampledatetime" column
    1. Confirm that each row has a unique combination of the header columns
1. Pipe that dataframe to `pybmpdb._prepare_for_summary`, which does the following:
    1. Combines Wetland Basin and Retention Pond data into a serparate dataset where BMP category is shown as "Retention Pond/Wetland Basin" and appended to the main dataaset
    1. NO2+NO3 and NO3 datasets are combined (with preference given to NO2+NO3) and assigned a parameter called NOx
    1. Grab samples are removed from the dataset except for:
        1. Biological data at all BMP categories
        1. All parameter groups at Retention Pond, Wetland Basin, and Wetland Basin/Retention Pond BMPs
1. Then with that dataset, go through each event and:
    1. Select (prefer) composite samples when both composite and grab samples exist
    1. Fall back to subsurface samples if an outflow sample is not available (reclassify as outflow)
    1. Fall back to reference samples in an inflow sample is not available (reclassify as inflow)
1. Save the dataset in this state as the the "flat" (unpaired) dataset
1. Pivot the dataset such that the values "station" column nest with the "res" and "qual" columns. In effect, we now have:
    1. Half as many rows
    1. Two columns for "res" and "qual" at the inflow and outflow monitoring stations
1. Drop all rows where either the "res_inflow" or "res_outflow" column is null (i.e., dropped unpaired observations)
1. Save this dataset as the "paired" dataset

These two dataset ("flat" and "paired") are merged with the Site data to include the DOT-related information then uploaded to the BMP Database as "WQRecords" and "WQPairs", respectively.

### Final Prep

Prior to the analysis for the main WQ and DOT summary report, the following steps are taken:

1. The data are read in from the `/WQRecords` endpoint
1. Non-detect values reported at 0.5 * DL are converted to the full detection limit
1. A "paramunit" column is created and filled in the format: '{parameter} ({units})'
1. A "DOT_Activity" column is created from the existing "dot_type" column, replacing 'Not Applicable' values with 'Non-DOT'
1. Group by "site", "bmp", "paramunit", "station", "Is_DOT" columns and remove groups with fewer than 3 observed events (storms)
1. Group by "category", "paramunit", "station", "Is_DOT" acolumns nd remove groups with fewer than 3 unique BMP IDs
1. Select all rows with the specific parameters and BMP catgories to be included in the analysis.

## Renaming column mappings

### WQ Data

<details>

* SiteID → site_id
* SiteName → site
* City → city
* State → state
* Country → country
* EPARainZone → epazone
* DOT_flag → dot_flag
* BMPID → bmp_id
* BMPName → bmp
* BMPCategory_Code → _catcode
* BMPCategory_Desc → _category
* BMPType → bmptype
* BMPType_Desc → bmpdesc
* MSID → ms_id
* MSName → ms
* MSType → station
* EventID → storm
* EventType → event_type
* DateSample → sampledate
* TimeSample → sampletime
* SampleMedia → watertype
* SampleType → sampletype
* WQID → wq_id
* WSID → ws_id
* ParameterName → parameter
* Value_SubHalfDL → res
* Value_Unit → units
* WQQualifier → qual
* DetectionLimit → DL
* InitialScreen_flag → wq_initialscreen
* CategoryAnalysisScreen_flag → _screenflag
* UseIndividualAnalysis_Flag → ms_indivscreen
* UseCateogoryAnalysis_Flag → _cat
* UseInCategoricalAnalysis → wq_catscreen
* UseInWebTool → webscreen
* DOT_ActivityType_flag → dot_type
* ParameterGroupCode → paramgroup

</details>

### Site Data

<details>

* SiteID → site_id
* DOT_AADT → aadt
* BMPID → bmp_id
* WSID → ws_id

</details>

### BMP Codes

<details>

* category_name → category
* category_code → bmpcode

</details>

## Header Columns

### WQ Data

<details>

* category
* epazone
* state
* site
* bmp
* station
* storm
* sampletype
* watertype
* paramgroup
* units
* parameter
* fraction
* wq_initialscreen
* ms_indivscreen
* wq_catscreen
* bmptype
* ws_id
* site_id
* bmp_id

<details>
