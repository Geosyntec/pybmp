from pkg_resources import resource_filename

import numpy as np
import pandas

import pytest
import numpy.testing as nptest

import pybmpdb
from pybmpdb import nsqd


class Test_NSQData:
    def setup(self):
        self.testfile = resource_filename('pybmpdb.tests._data', 'nsqdata.csv')

        self.data = nsqd.NSQData(datapath=self.testfile)
        self.known_landuses = np.array([
            'Commercial', 'Freeway', 'Industrial', 'Institutional',
            'Open Space', 'Residential', 'Unknown'
        ])

        self.known_columns = [
            'epa_rain_zone', 'state', 'location_code', 'station_name',
            'jurisdiction_county', 'jurisdiction_city', 'primary_landuse',
            'secondary_landuse', 'percent_impervious', 'start_date',
            'days since last rain', 'precipitation_depth_(in)', 'season',
            'parameter', 'fraction', 'units', 'res', 'qual',
            'drainage_area_acres', 'latitude', 'longitude',
        ]

        self.known_commerical_copper_shape = (329, 22)

    def test_data(self):
        assert (hasattr(self.data, 'data'))
        assert isinstance(self.data.data, pandas.DataFrame)
        assert (self.data.data.columns.tolist() == self.known_columns)

    def test_data_season(self):
        known_seasons = ['FA', 'SP', 'SU', 'WI']
        seasons = sorted(self.data.data['season'].unique().tolist())
        assert (seasons == known_seasons)
