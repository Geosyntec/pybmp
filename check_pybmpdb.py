import sys
import matplotlib
matplotlib.use('agg')

import pybmpdb
status = pybmpdb.test(*sys.argv[1:])
sys.exit(status)