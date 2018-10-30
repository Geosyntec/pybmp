import sys
import matplotlib
from matplotlib import style

matplotlib.use('agg')
style.use('classic')

import pybmpdb

if '--strict' in sys.argv:
    sys.argv.remove('--strict')
    tester = pybmpdb.teststrict
else:
    tester = pybmpdb.test

sys.exit(tester(*sys.argv[1:]))
