__all__ = ['getUnits', 'getTexParam', 'getTexUnit',
           'getNormalization', 'getConversion']

def getUnits(param):
    '''
    Returns the standard units for a given parameter
    '''
    return parameters[param.strip().lower()]['units']


def getTexUnit(unit):
    '''
    Returns a LaTeX representation of the standard units for
    a given parameter
    '''
    return units[unit.strip()]['tex']


def getTexParam(param):
    '''
    Returns a LaTeX representation of the name of a parameter
    '''
    return parameters[param.strip().lower()]['tex']


def getNormalization(unit):
    '''
    Returns the factor by which you should multiply a result
    to normalize the given units to the base units for that
    quantity (e.g., ng/L -> g/L)
    '''
    if unit is None:
        return 1
    else:
        return units[unit.strip()]['factor']

def getConversion(param):
    '''
    Returns the factor by which you should divide a *normalized*
    result to convert to the standard units for that parameter
    (e.g., g/L -> ug/L for Dissolved Lead)
    '''
    return units[parameters[param.strip().lower()]['units']]['factor']

def addParameter(name, units, tex=None):
    if tex is None:
        tex = name
    values = {
        'tex': tex,
        'units': units
    }
    parameters[name.lower()] = values
    return parameters

def addUnit(name, factor, texname=None, unicodename=None):
    if texname is None:
        texname = name

    if unicodename is None:
        unicodename = None

    values = {
        'factor': factor,
        'tex': texname,
        'unicode': unicodename
    }
    units[name] = values
    return units


units = {
    '%': {
        'factor': 1,
        'tex': r'\si{\percent}',
        'unicode': '%'
    },
    '#/100mL': {
        'factor': 1,
        'tex': r'\#\SI[per-mode=symbol]{\per100\milli\liter}',
        'unicode': 'MPN/100 mL'
    },
    '10/ml': {
        'factor': 100,
        'tex': r'\SI[per-mode=symbol]{10}{\per\milli\liter}',
        'unicode': '10/mL'
    },
    'MPN/100 mL': {
        'factor': 1,
        'tex': r'MPN\si[per-mode=symbol]{\per100\milli\liter}',
        'unicode': 'MPN/100 mL'
    },
    'MPN/100mL': {
        'factor': 1,
        'tex': r'MPN\si[per-mode=symbol]{\per100\milli\liter}',
        'unicode': 'MPN/100 mL'
    },
    'CFU/100 mL': {
        'factor': 1,
        'tex': r'CFU\si[per-mode=symbol]{\per100\milli\liter}',
        'unicode': 'CFU/100 mL'
    },
    'CFU/100mL': {
        'factor': 1,
        'tex': r'CFU\si[per-mode=symbol]{\per100\milli\liter}',
        'unicode': 'CFU/100 mL'
    },
    'NTU': {
        'factor': 1,
        'tex': r'NTU',
        'unicode': 'NTU'
    },
    'PCU': {
        'factor': 1,
        'tex': r'PCU',
        'unicode': 'PCU'
    },
    'su': {
        'factor': 1,
        'tex': r'',
        'unicode': 'SU'
    },
    'SU': {
        'factor': 1,
        'tex': r'',
        'unicode': 'SU'
    },
    'mL/L': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\milli\liter\per\liter}',
        'unicode': 'mL/L'
    },
    'ml/L': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\milli\liter\per\liter}',
        'unicode': 'mL/L'
    },
    'mV': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\milli\volt}',
        'unicode': 'mV'
    },
    'kg/L': {
        'factor': 1000,
        'tex': r'\si[per-mode=symbol]{\kilo\gram\per\liter}',
        'unicode': 'kg/L'
    },
    'g/L': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\gram\per\liter}',
        'unicode': 'g/L'
    },
    'mg/L': {
        'factor': 0.001,
        'tex': r'\si[per-mode=symbol]{\milli\gram\per\liter}',
        'unicode': 'mg/L'
    },
    'mg/l': {
        'factor': 0.001,
        'tex': r'\si[per-mode=symbol]{\milli\gram\per\liter}',
        'unicode': 'mg/L'
    },
    'MG/L': {
        'factor': 0.001,
        'tex': r'\si[per-mode=symbol]{\milli\gram\per\liter}',
        'unicode': 'mg/L'
    },
    'ug/L': {
        'factor': 0.000001,
        'tex': r'\si[per-mode=symbol]{\micro\gram\per\liter}',
        'unicode': u'\xb5g/L'
    },
    'µg/L': {
        'factor': 0.000001,
        'tex': r'\si[per-mode=symbol]{\micro\gram\per\liter}',
        'unicode': u'\xb5g/L'
    },
    'ug/l': {
        'factor': 0.000001,
        'tex': r'\si[per-mode=symbol]{\micro\gram\per\liter}',
        'unicode': u'\xb5g/L'
    },
    'UG/L': {
        'factor': 0.000001,
        'tex': r'\si[per-mode=symbol]{\micro\gram\per\liter}',
        'unicode': u'\xb5g/L'
    },
    'ng/L': {
        'factor': 0.000000001,
        'tex': r'\si[per-mode=symbol]{\nano\gram\per\liter}',
        'unicode': 'ng/L'
    },
    u'\xb0C': {
        'factor': 1,
        'tex': r'\si{\degreeCelsius}',
        'unicode': u'\xb0C'
    },
    'deg C': {
        'factor': 1,
        'tex': r'\si{\degreeCelsius}',
        'unicode': u'\xb0C'
    },
    'degC': {
        'factor': 1,
        'tex': r'\si{\degreeCelsius}',
        'unicode': u'\xb0C'
    },
    u'\xb5mhos/cm': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\micro\siemens\per\centi\meter}',
        'unicode': u'\xb5S/cm'
    },
    'umhos/cm': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\micro\siemens\per\centi\meter}',
        'unicode': u'\xb5S/cm'
    },
    u'\xb5S/cm': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\micro\siemens\per\centi\meter}',
        'unicode': u'\xb5S/cm'
    },
    'uS/cm': {
        'factor': 1,
        'tex': r'\si[per-mode=symbol]{\micro\siemens\per\centi\meter}',
        'unicode': u'\xb5S/cm'
    },
    'ADMI value': {
        'factor': 1,
        'tex': r'ADMI Value',
        'unicode': 'ADMI Value'
    },
    'ADMI Value': {
        'factor': 1,
        'tex': r'ADMI Value',
        'unicode': 'ADMI Value'
    },
    'kg': {
        'factor': 1,
        'tex': r'kg',
        'unicode': 'kg'
    },
    'mg/m3': {
        'factor': 1,
        'tex':r'\si[per-mode=symbol]{\milli\grams\per\meter\cubed}',
        'unicode': 'kg'
    }
}

parameters = {
    '1,1,1,2-tetrachloroethane': {
        'tex': '1,1,1,2-Tetrachloroethane',
        'units': 'ug/L'
    },
    '1,1,1-trichloroethane': {
        'tex': '1,1,1-Trichloroethane',
        'units': 'ug/L'
    },
    '1,1,2,2-tetrachloroethane': {
        'tex': '1,1,2,2-Tetrachloroethane',
        'units': 'ug/L'
    },
    '1,1,2-trichloroethane': {
        'tex': '1,1,2-Trichloroethane',
        'units': 'ug/L'
    },
    '1,1-dichloroethane': {
        'tex': '1,1-Dichloroethane',
        'units': 'ug/L'
    },
    '1,1-dichloroethylene': {
        'tex': '1,1-Dichloroethylene',
        'units': 'ug/L'
    },
    '1,1-dichloropropene': {
        'tex': '1,1-Dichloropropene',
        'units': 'ug/L'
    },
    '1,2,3-trichlorobenzene': {
        'tex': '1,2,3-Trichlorobenzene',
        'units': 'ug/L'
    },
    '1,2,3-trichloropropane': {
        'tex': '1,2,3-Trichloropropane',
        'units': 'ug/L'
    },
    '1,2,4-trichlorobenzene': {
        'tex': '1,2,4-Trichlorobenzene',
        'units': 'ug/L'
    },
    '1,2,4-trimethylbenzene': {
        'tex': '1,2,4-Trimethylbenzene',
        'units': 'ug/L'
    },
    '1,2-benzanthracene': {
        'tex': '1,2-Benzanthracene',
        'units': 'ug/L'
    },
    '1,2-dibromo-3-chloropropane': {
        'tex': '1,2-Dibromo-3-Chloropropane',
        'units': 'ug/L'
    },
    '1,2-dibromoethane': {
        'tex': '1,2-Dibromoethane',
        'units': 'ug/L'
    },
    '1,2-dichlorobenzene': {
        'tex': '1,2-Dichlorobenzene',
        'units': 'ug/L'
    },
    '1,2-dichloroethane': {
        'tex': '1,2-Dichloroethane',
        'units': 'ug/L'
    },
    '1,2-dichloropropane': {
        'tex': '1,2-Dichloropropane',
        'units': 'ug/L'
    },
    '1,2-diphenylhydrazine': {
        'tex': '1,2-Diphenylhydrazine',
        'units': 'ug/L'
    },
    '1,3,5-trimethylbenzene': {
        'tex': '1,3,5-Trimethylbenzene',
        'units': 'ug/L'
    },
    '1,3-dichlorobenzene': {
        'tex': '1,3-Dichlorobenzene',
        'units': 'ug/L'
    },
    '1,3-dichloropropane': {
        'tex': '1,3-Dichloropropane',
        'units': 'ug/L'
    },
    '1,4-dichlorobenzene': {
        'tex': '1,4-Dichlorobenzene',
        'units': 'ug/L'
    },
    '1-chlorohexane': {
        'tex': '1-Chlorohexane',
        'units': 'ug/L'
    },
    '1-methylnaphthalene': {
        'tex': '1-Methylnaphthalene',
        'units': 'ug/L'
    },
    '2,2-dichloropropane': {
        'tex': '2,2-Dichloropropane',
        'units': 'ug/L'
    },
    "2,4'-ddd": {
        'tex': "2,4'-DDD",
        'units': 'ug/L'
    },
    "2,4'-dde": {
        'tex': "2,4'-DDE",
        'units': 'ug/L'
    },
    "2,4'-ddt": {
        'tex': "2,4'-DDT",
        'units': 'ug/L'
    },
    '2,4,5-tp-silvex': {
        'tex': '2,4,5-TP-SILVEX',
        'units': 'ug/L'
    },
    '2,4,5-trichlorophenol': {
        'tex': '2,4,5-Trichlorophenol',
        'units': 'ug/L'
    },
    '2,4,6-trichlorophenol': {
        'tex': '2,4,6-Trichlorophenol',
        'units': 'ug/L'
    },
    '2,4-d': {
        'tex': '2,4-D',
        'units': 'ug/L'
    },
    '2,4-dichlorophenol': {
        'tex': '2,4-Dichlorophenol',
        'units': 'ug/L'
    },
    '2,4-dinitrophenol': {
        'tex': '2,4-Dinitrophenol',
        'units': 'ug/L'
    },
    '2,4-dinitrotoluene': {
        'tex': '2,4-Dinitrotoluene',
        'units': 'ug/L'
    },
    '2,4-dimethylphenol': {
        'tex': '2,4-Dimethylphenol',
        'units': 'ug/L'
    },
    '2,6-dinitrotoluene': {
        'tex': '2,6-Dinitrotoluene',
        'units': 'ug/L'
    },
    '2-butanone': {
        'tex': '2-Butanone',
        'units': 'ug/L'
    },
    '2-chloroethyl vinyl ether': {
        'tex': '2-Chloroethyl Vinyl Ether',
        'units': 'ug/L'
    },
    '2-chloronaphthalene': {
        'tex': '2-Chloronaphthalene',
        'units': 'ug/L'
    },
    '2-chlorophenol': {
        'tex': '2-Chlorophenol',
        'units': 'ug/L'
    },
    '2-chlorotoluene': {
        'tex': '2-Chlorotoluene',
        'units': 'ug/L'
    },
    '2-hexanone': {
        'tex': '2-Hexanone',
        'units': 'ug/L'
    },
    '2-methylnaphthalene': {
        'tex': '2-Methylnaphthalene',
        'units': 'ug/L'
    },
    '2-nitrophenol': {
        'tex': '2-Nitrophenol',
        'units': 'ug/L'
    },
    "3,3'-dichlorobenzidine": {
        'tex': "3,3'-Dichlorobenzidine",
        'units': 'ug/L'
    },
    "4,4'-ddd": {
        'tex': "4,4'-DDD",
        'units': 'ug/L'
    },
    "4,4'-dde": {
        'tex': "4,4'-DDE",
        'units': 'ug/L'
    },
    "4,4'-ddt": {
        'tex': "4,4'-DDT",
        'units': 'ug/L'
    },
    '4,6-dinitro-2-methylphenol': {
        'tex': '4,6-Dinitro-2-methylphenol',
        'units': 'ug/L'
    },
    '4,6-dinitro-o-cresol': {
        'tex': '4,6-Dinitro-o-cresol',
        'units': 'ug/L'
    },
    '4-bromophenyl phenyl ether': {
        'tex': '4-Bromophenyl Phenyl Ether',
        'units': 'ug/L'
    },
    '4-chlorophenyl phenyl ether': {
        'tex': '4-Chlorophenyl Phenyl Ether',
        'units': 'ug/L'
    },
    '4-chlorotoluene': {
        'tex': '4-Chlorotoluene',
        'units': 'ug/L'
    },
    '4-nitrophenol': {
        'tex': '4-Nitrophenol',
        'units': 'ug/L'
    },
    '4-chloro-3-methylphenol': {
        'tex': '4-Chloro-3-Methylphenol',
        'units': 'ug/L'
    },
    '4-chloro-3-methylphenol,  dissolved': {
        'tex': 'Dissolved 4-Chloro-3-Methylphenol',
        'units': 'ug/L'
    },
    '4-hydroxy-4-methyl-2-pentanone': {
        'tex': '4-Hydroxy-4-Methyl-2-Pentanone',
        'units': 'ug/L'
    },
    'acenaphthene': {
        'tex': 'Acenaphthene',
        'units': 'ug/L'
    },
    'acenaphthene,  dissolved': {
        'tex': 'Dissolved Acenaphthene',
        'units': 'ug/L'
    },
    'acenaphthylene': {
        'tex': 'Acenaphthylene',
        'units': 'ug/L'
    },
    'acenaphthylene, suspended': {
        'tex': 'Suspended Acenaphthylene',
        'units': 'ug/L'
    },
    'acetone': {
        'tex': 'Acetone',
        'units': 'ug/L'
    },
    'acrolein': {
        'tex': 'Acrolein',
        'units': 'ug/L'
    },
    'acrylonitrile': {
        'tex': 'Acrylonitrile',
        'units': 'ug/L'
    },
    'alachlor': {
        'tex': 'Alachlor',
        'units': 'ug/L'
    },
    'aldrin': {
        'tex': 'Aldrin',
        'units': 'ug/L'
    },
    'alkalinity': {
        'tex': 'Alkalinity',
        'units': 'mg/L'
    },
    'alkalinity, carbonate as caco3': {
        'tex': 'Alkalinity, Carbonate as CaCO$_{3}$',
        'units': 'mg/L'
    },
    'aluminum, dissolved': {
        'tex': 'Dissolved Aluminum',
        'units': 'ug/L'
    },
    'aluminum, total': {
        'tex': 'Total Aluminum',
        'units': 'ug/L'
    },
    'anthracene': {
        'tex': 'Anthracene',
        'units': 'ug/L'
    },
    'anthracene, suspended': {
        'tex': 'Suspended Anthracene',
        'units': 'ug/L'
    },
    'antimony, dissolved': {
        'tex': 'Dissolved Antimony',
        'units': 'ug/L'
    },
    'antimony, total': {
        'tex': 'Total Antimony',
        'units': 'ug/L'
    },
    'aroclor 1016': {
        'tex': 'Aroclor 1016',
        'units': 'ug/L'
    },
    'aroclor 1221': {
        'tex': 'Aroclor 1221',
        'units': 'ug/L'
    },
    'aroclor 1232': {
        'tex': 'Aroclor 1232',
        'units': 'ug/L'
    },
    'aroclor 1242': {
        'tex': 'Aroclor 1242',
        'units': 'ug/L'
    },
    'aroclor 1248': {
        'tex': 'Aroclor 1248',
        'units': 'ug/L'
    },
    'aroclor 1254': {
        'tex': 'Aroclor 1254',
        'units': 'ug/L'
    },
    'aroclor 1260': {
        'tex': 'Aroclor 1260',
        'units': 'ug/L'
    },
    'arsenic, dissolved': {
        'tex': 'Dissolved Arsenic',
        'units': 'ug/L'
    },
    'arsenic, total': {
        'tex': 'Total Arsenic',
        'units': 'ug/L'
    },
    'dissolved arsenic': {
        'tex': 'Dissolved Arsenic',
        'units': 'ug/L'
    },
    'total arsenic': {
        'tex': 'Total Arsenic',
        'units': 'ug/L'
    },
    'atrazine': {
        'tex': 'Atrazine',
        'units': 'ug/L'
    },
    'bhc-alpha': {
        'tex': 'BHC-ALPHA',
        'units': 'ug/L'
    },
    'bhc-beta': {
        'tex': 'BHC-BETA',
        'units': 'ug/L'
    },
    'bhc-delta': {
        'tex': 'BHC-DELTA',
        'units': 'ug/L'
    },
    'bod': {
        'tex': 'Biological Oxygen Demand',
        'units': 'mg/L'
    },
    'bod, dissolved': {
        'tex': 'Biological Oxygen Demand (dissolved)',
        'units': 'mg/L'
    },
    'bod, non-standard conditions': {
        'tex': 'Biological Oxygen Demand (non-standard conditions)',
        'units': 'mg/L'
    },
    'barium, dissolved': {
        'tex': 'Dissolved Barium',
        'units': 'ug/L'
    },
    'barium, total': {
        'tex': 'Total Barium',
        'units': 'ug/L'
    },
    'benz[a]anthracene': {
        'tex': 'Benz[a]anthracene',
        'units': 'ug/L'
    },
    'benz[a]anthracene, suspended': {
        'tex': 'Suspended Benz[a]anthracene',
        'units': 'ug/L'
    },
    'benzene': {
        'tex': 'Benzene',
        'units': 'ug/L'
    },
    'benzidine': {
        'tex': 'Benzidine',
        'units': 'ug/L'
    },
    'benzo(b)fluoranthene': {
        'tex': 'Benzo(b)fluoranthene',
        'units': 'ug/L'
    },
    'benzo(b)fluoranthene, suspended': {
        'tex': 'Suspended Benzo(b)fluoranthene',
        'units': 'ug/L'
    },
    'benzo[a]pyrene': {
        'tex': 'Benzo[a]pyrene',
        'units': 'ug/L'
    },
    'benzo[a]pyrene, suspended': {
        'tex': 'Suspended Benzo[a]pyrene',
        'units': 'ug/L'
    },
    'benzo[ghi]perylene': {
        'tex': 'Benzo[ghi]perylene',
        'units': 'ug/L'
    },
    'benzo[ghi]perylene, suspended': {
        'tex': 'Suspended Benzo[ghi]perylene',
        'units': 'ug/L'
    },
    'benzo[k]fluoranthene': {
        'tex': 'Benzo[k]fluoranthene',
        'units': 'ug/L'
    },
    'benzo[k]fluoranthene, suspended': {
        'tex': 'Suspended Benzo[k]fluoranthene',
        'units': 'ug/L'
    },
    'benzoic acid': {
        'tex': 'Benzoic acid',
        'units': 'ug/L'
    },
    'benzyl alcohol': {
        'tex': 'Benzyl Alcohol',
        'units': 'ug/L'
    },
    'beryllium, dissolved': {
        'tex': 'Dissolved Beryllium',
        'units': 'ug/L'
    },
    'beryllium, total': {
        'tex': 'Total Beryllium',
        'units': 'ug/L'
    },
    'biphenyl': {
        'tex': 'Biphenyl',
        'units': 'ug/L'
    },
    'bis(2-chloro-1-methylethyl) ether': {
        'tex': 'Bis(2-chloro-1-methylethyl) Ether',
        'units': 'ug/L'
    },
    'bis(2-chloroethoxy)methane': {
        'tex': 'Bis(2-chloroethoxy)methane',
        'units': 'ug/L'
    },
    'bis(2-chloroethyl) ether': {
        'tex': 'Bis(2-chloroethyl) Ether',
        'units': 'ug/L'
    },
    'bis(2-chloroisopropyl) ether': {
        'tex': 'Bis(2-chloroisopropyl) Ether',
        'units': 'ug/L'
    },
    'bis(2-ethylhexyl) phthalate': {
        'tex': 'Bis(2-ethylhexyl) Phthalate',
        'units': 'ug/L'
    },
    'bis(n-octyl)phthalate': {
        'tex': 'Bis(n-octyl)phthalate',
        'units': 'ug/L'
    },
    'bromobenzene': {
        'tex': 'Bromobenzene',
        'units': 'ug/L'
    },
    'bromochloroiodomethane': {
        'tex': 'Bromochloroiodomethane',
        'units': 'ug/L'
    },
    'bromoform': {
        'tex': 'Bromoform',
        'units': 'ug/L'
    },
    'bromomethane': {
        'tex': 'Bromomethane',
        'units': 'ug/L'
    },
    'butyl benzyl phthalate': {
        'tex': 'Butyl Benzyl Phthalate',
        'units': 'ug/L'
    },
    'cbod': {
        'tex': 'Chemical-Biological Oxygen Demand',
        'units': 'mg/L'
    },
    'cfc-11': {
        'tex': 'CFC-11',
        'units': 'ug/L'
    },
    'cfc-12': {
        'tex': 'CFC-12',
        'units': 'ug/L'
    },
    'cadmium, dissolved': {
        'tex': 'Dissolved Cadmium',
        'units': 'ug/L'
    },
    'cadmium, suspended': {
        'tex': 'Suspended Cadmium',
        'units': 'ug/L'
    },
    'cadmium, total': {
        'tex': 'Total Cadmium',
        'units': 'ug/L'
    },
    'dissolved cadmium': {
        'tex': 'Dissolved Cadmium',
        'units': 'ug/L'
    },
    'suspended cadmium': {
        'tex': 'Suspended Cadmium',
        'units': 'ug/L'
    },
    'total cadmium': {
        'tex': 'Total Cadmium',
        'units': 'ug/L'
    },
    'calcium as caco3, total': {
        'tex': 'Total Calcium as CaCO$_{3}$',
        'units': 'mg/L'
    },
    'calcium, dissolved': {
        'tex': 'Dissolved Calcium',
        'units': 'mg/L'
    },
    'calcium, total': {
        'tex': 'Total Calcium',
        'units': 'mg/L'
    },
    'carbofuran': {
        'tex': 'Carbofuran',
        'units': 'ug/L'
    },
    'carbon disulfide': {
        'tex': 'Carbon Disulfide',
        'units': 'ug/L'
    },
    'carbon fraction, particulate organic material': {
        'tex': 'Carbon Fraction, Particulate Organic Material',
        'units': 'mg/L'
    },
    'carbon tetrachloride': {
        'tex': 'Carbon Tetrachloride',
        'units': 'ug/L'
    },
    'carbon disulfide': {
        'tex': 'Carbon Disulfide',
        'units': 'ug/L'
    },
    'carbon tetrachloride': {
        'tex': 'Carbon Tetrachloride',
        'units': 'ug/L'
    },
    'chemical oxygen demand': {
        'tex': 'Chemical Oxygen Demand',
        'units': 'mg/L'
    },
    'chemical oxygen demand, high level': {
        'tex': 'Chemical Oxygen Demand (high level)',
        'units': 'mg/L'
    },
    'chemical oxygen demand, low level': {
        'tex': 'Chemical Oxygen Demand (low level)',
        'units': 'mg/L'
    },
    'chemical oxygen demand, low level, filtered': {
        'tex': 'Chemical Oxygen Demand (low level, filtered)',
        'units': 'mg/L'
    },
    'chemical oxygen demand, soluble': {
        'tex': 'Chemical Oxygen Demand (soluble)',
        'units': 'mg/L'
    },
    'chlordane': {
        'tex': 'Chlordane',
        'units': 'ug/L'
    },
    'chloride, dissolved': {
        'tex': 'Dissolved Chloride',
        'units': 'mg/L'
    },
    'chloride, total': {
        'tex': 'Total Chloride',
        'units': 'mg/L'
    },
    'chlorobenzene': {
        'tex': 'Chlorobenzene',
        'units': 'ug/L'
    },
    'chlorodibromomethane': {
        'tex': 'Chlorodibromomethane',
        'units': 'ug/L'
    },
    'chloroethane': {
        'tex': 'Chloroethane',
        'units': 'ug/L'
    },
    'chloroform': {
        'tex': 'Chloroform',
        'units': 'ug/L'
    },
    'chloromethane': {
        'tex': 'Chloromethane',
        'units': 'ug/L'
    },
    'chlorotoluene': {
        'tex': 'Chlorotoluene',
        'units': 'ug/L'
    },
    'chlorpyrifos': {
        'tex': 'Chlorpyrifos',
        'units': 'ug/L'
    },
    'chromium(vi), dissolved': {
        'tex': 'Dissolved Chromium(VI)',
        'units': 'ug/L'
    },
    'chromium(vi), total': {
        'tex': 'Total Chromium(VI)',
        'units': 'ug/L'
    },
    'chromium, dissolved': {
        'tex': 'Dissolved Chromium',
        'units': 'ug/L'
    },
    'chromium, suspended': {
        'tex': 'Suspended Chromium',
        'units': 'ug/L'
    },
    'chromium, total': {
        'tex': 'Total Chromium',
        'units': 'ug/L'
    },
    'dissolved chromium': {
        'tex': 'Dissolved Chromium',
        'units': 'ug/L'
    },
    'suspended chromium': {
        'tex': 'Suspended Chromium',
        'units': 'ug/L'
    },
    'total chromium': {
        'tex': 'Total Chromium',
        'units': 'ug/L'
    },
    'chrysene': {
        'tex': 'Chrysene',
        'units': 'ug/L'
    },
    'chrysene, suspended': {
        'tex': 'Suspended Chrysene',
        'units': 'ug/L'
    },
    'cobalt, total': {
        'tex': 'Total Cobalt',
        'units': 'ug/L'
    },
    'copper, dissolved': {
        'tex': 'Dissolved Copper',
        'units': 'ug/L'
    },
    'copper, suspended': {
        'tex': 'Suspended Copper',
        'units': 'ug/L'
    },
    'copper, total': {
        'tex': 'Total Copper',
        'units': 'ug/L'
    },
    'dissolved copper': {
        'tex': 'Dissolved Copper',
        'units': 'ug/L'
    },
    'suspended copper': {
        'tex': 'Suspended Copper',
        'units': 'ug/L'
    },
    'total copper': {
        'tex': 'Total Copper',
        'units': 'ug/L'
    },
    'cumene': {
        'tex': 'Cumene',
        'units': 'ug/L'
    },
    'cyanazine': {
        'tex': 'Cyanazine',
        'units': 'ug/L'
    },
    'cyanide': {
        'tex': 'Cyanide',
        'units': 'mg/L'
    },
    'daconil': {
        'tex': 'DACONIL',
        'units': 'ug/L'
    },
    'di(2-ethylhexyl) phthalate': {
        'tex': 'Di(2-ethylhexyl) Phthalate',
        'units': 'ug/L'
    },
    'di-n-octyl phthalate': {
        'tex': 'Di-n-octyl Phthalate',
        'units': 'ug/L'
    },
    'diazinon': {
        'tex': 'Diazinon',
        'units': 'ug/L'
    },
    'dibenz[a,h]anthracene': {
        'tex': 'Dibenz[a,h]anthracene',
        'units': 'ug/L'
    },
    'dibenz[a,h]anthracene,  dissolved': {
        'tex': 'Dissolved Dibenz[a,h]anthracene',
        'units': 'ug/L'
    },
    'dibenzofuran': {
        'tex': 'Dibenzofuran',
        'units': 'ug/L'
    },
    'dibromomethane': {
        'tex': 'Dibromomethane',
        'units': 'ug/L'
    },
    'dibromodichloromethane': {
        'tex': 'Dibromodichloromethane',
        'units': 'ug/L'
    },
    'dibutyl phthalate': {
        'tex': 'Dibutyl Phthalate',
        'units': 'ug/L'
    },
    'dichlorobromomethane': {
        'tex': 'Dichlorobromomethane',
        'units': 'ug/L'
    },
    'dichlorodifluoromethane': {
        'tex': 'Dichlorodifluoromethane',
        'units': 'ug/L'
    },
    'dichlorophenol': {
        'tex': 'Dichlorophenol',
        'units': 'ug/L'
    },
    'dinitrophenol': {
        'tex': 'Dinitrophenol',
        'units': 'ug/L'
    },
    'dieldrin': {
        'tex': 'Dieldrin',
        'units': 'ug/L'
    },
    'diethyl phthalate': {
        'tex': 'Diethyl Phthalate',
        'units': 'ug/L'
    },
    'dimethyl phthalate': {
        'tex': 'Dimethyl Phthalate',
        'units': 'ug/L'
    },
    'dimethylnaphthalene': {
        'tex': 'Dimethylnaphthalene',
        'units': 'ug/L'
    },
    'dissolved oxygen (do)': {
        'tex': 'Dissolved Oxygen (DO)',
        'units': 'mg/L'
    },
    'dro': {
        'tex': 'DRO',
        'units': 'ug/L'
    },
    'endosulfan i': {
        'tex': 'Endosulfan I',
        'units': 'ug/L'
    },
    'endosulfan i (alpha)': {
        'tex': 'Endosulfan I (alpha)',
        'units': 'ug/L'
    },
    '.alpha.-endosulfan,  dissolved': {
        'tex': 'Dissolved, Endosulfan I (alpha)',
        'units': 'ug/L'
    },
    'endosulfan ii': {
        'tex': 'Endosulfan II',
        'units': 'ug/L'
    },
    'endosulfan ii (beta)': {
        'tex': 'Endosulfan II (beta)',
        'units': 'ug/L'
    },
    '.beta.-endosulfan,  dissolved': {
        'tex': 'Dissolved, Endosulfan II (beta)',
        'units': 'ug/L'
    },
    'endosulfan sulfate': {
        'tex': 'Endosulfan sulfate',
        'units': 'ug/L'
    },
    'endrin': {
        'tex': 'Endrin',
        'units': 'ug/L'
    },
    'endrin aldehyde': {
        'tex': 'Endrin Aldehyde',
        'units': 'ug/L'
    },
    'endrin ketone': {
        'tex': 'Endrin Ketone',
        'units': 'ug/L'
    },
    'enterococcus': {
        'tex': 'Enterococcus',
        'units': 'MPN/100 mL'
    },
    'escherichia coli': {
        'tex': 'Escherichia coli',
        'units': 'MPN/100 mL'
    },
    'ethyl methacrylate': {
        'tex': 'Ethyl Methacrylate',
        'units': 'ug/L'
    },
    'ethylbenzene': {
        'tex': 'Ethylbenzene',
        'units': 'ug/L'
    },
    'ethylene dibromide': {
        'tex': 'Ethylene Dibromide',
        'units': 'ug/L'
    },
    'fecal coliform': {
        'tex': 'Fecal Coliform',
        'units': 'MPN/100 mL'
    },
    'fecal streptococcus group bacteria': {
        'tex': 'Fecal Streptococcus Group Bacteria',
        'units': 'MPN/100 mL'
    },
    'fluoranthene': {
        'tex': 'Fluoranthene',
        'units': 'ug/L'
    },
    'fluoranthene, suspended': {
        'tex': 'Suspended Fluoranthene',
        'units': 'ug/L'
    },
    'fluorene': {
        'tex': 'Fluorene',
        'units': 'ug/L'
    },
    'fluorene, suspended': {
        'tex': 'Suspended Fluorene',
        'units': 'ug/L'
    },
    'fluoride, dissolved': {
        'tex': 'Dissolved Fluoride',
        'units': 'mg/L'
    },
    'fluoride, total': {
        'tex': 'Total Fluoride',
        'units': 'mg/L'
    },
    'glyphosate': {
        'tex': 'Glyphosate',
        'units': 'ug/L'
    },
    'halon 1011': {
        'tex': 'Halon 1011',
        'units': 'ug/L'
    },
    'hardness': {
        'tex': 'Hardness',
        'units': 'mg/L'
    },
    'hardness, non-carbonate': {
        'tex': 'Hardness, non-carbonate',
        'units': 'mg/L'
    },
    'heptachlor': {
        'tex': 'Heptachlor',
        'units': 'ug/L'
    },
    'heptachlor epoxide': {
        'tex': 'Heptachlor Epoxide',
        'units': 'ug/L'
    },
    'hexachlorobenzene': {
        'tex': 'Hexachlorobenzene',
        'units': 'ug/L'
    },
    'hexachlorobutadiene': {
        'tex': 'Hexachlorobutadiene',
        'units': 'ug/L'
    },
    'hexachlorocyclopentadiene': {
        'tex': 'Hexachlorocyclopentadiene',
        'units': 'ug/L'
    },
    'hexachloroethane': {
        'tex': 'Hexachloroethane',
        'units': 'ug/L'
    },
    'hydrocarbons, total petroleum (tph)': {
        'tex': 'Hydrocarbons, Total Petroleum (TPH)',
        'units': 'ug/L'
    },
    'hydrocarbons, total petroleum, diesel range organics': {
        'tex': 'Hydrocarbons, Total Petroleum, diesel range organics',
        'units': 'ug/L'
    },
    'hydrocarbons, total petroleum, gasoline range organics': {
        'tex': 'Hydrocarbons, Total Petroleum, gasoline range organics',
        'units': 'ug/L'
    },
    'indeno[1,2,3-cd]pyrene': {
        'tex': 'Indeno[1,2,3-cd]pyrene',
        'units': 'ug/L'
    },
    'indeno[1,2,3-cd]pyrene, suspended': {
        'tex': 'Suspended Indeno[1,2,3-cd]pyrene',
        'units': 'ug/L'
    },
    'inorganic carbon, total': {
        'tex': 'Total Inorganic Carbon',
        'units': 'mg/L'
    },
    'iodomethane': {
        'tex': 'Iodomethane',
        'units': 'ug/L'
    },
    'iron, dissolved': {
        'tex': 'Dissolved Iron',
        'units': 'ug/L'
    },
    'iron, total': {
        'tex': 'Total Iron',
        'units': 'ug/L'
    },
    'dissolved iron': {
        'tex': 'Dissolved Iron',
        'units': 'ug/L'
    },
    'total iron': {
        'tex': 'Total Iron',
        'units': 'ug/L'
    },
    'isophorone': {
        'tex': 'Isophorone',
        'units': 'ug/L'
    },
    'isopropylbenzene': {
        'tex': 'Isopropylbenzene',
        'units': 'ug/L'
    },
    'kjeldahl nitrogen (tkn)': {
        'tex': 'Total Kjeldahl Nitrogen',
        'units': 'mg/L'
    },
    'total kjeldahl nitrogen': {
        'tex': 'Total Kjeldahl Nitrogen',
        'units': 'mg/L'
    },
    'kjeldahl nitrogen, dissolved': {
        'tex': 'Dissolved Kjeldahl Nitrogen',
        'units': 'mg/L'
    },
    'kjeldahl nitrogen, suspended': {
        'tex': 'Suspended Kjeldahl Nitrogen',
        'units': 'mg/L'
    },
    'lead, dissolved': {
        'tex': 'Dissolved Lead',
        'units': 'ug/L'
    },
    'lead, suspended': {
        'tex': 'Suspended Lead',
        'units': 'ug/L'
    },
    'lead, total': {
        'tex': 'Total Lead',
        'units': 'ug/L'
    },
    'dissolved lead': {
        'tex': 'Dissolved Lead',
        'units': 'ug/L'
    },
    'suspended lead': {
        'tex': 'Suspended Lead',
        'units': 'ug/L'
    },
    'total lead': {
        'tex': 'Total Lead',
        'units': 'ug/L'
    },
    'lindane': {
        'tex': 'Lindane',
        'units': 'ug/L'
    },
    'lithium, dissolved': {
        'tex': 'Dissolved Lithium',
        'units': 'ug/L'
    },
    'magnesium, dissolved': {
        'tex': 'Dissolved Magnesium',
        'units': 'ug/L'
    },
    'magnesium, total': {
        'tex': 'Total Magnesium',
        'units': 'ug/L'
    },
    'malathion': {
        'tex': 'Malathion',
        'units': 'ug/L'
    },
    'manganese, dissolved': {
        'tex': 'Dissolved Manganese',
        'units': 'ug/L'
    },
    'manganese, total': {
        'tex': 'Total Manganese',
        'units': 'ug/L'
    },
    'mercury, dissolved': {
        'tex': 'Dissolved Mercury',
        'units': 'ug/L'
    },
    'mercury, total': {
        'tex': 'Total Mercury',
        'units': 'ug/L'
    },
    'methoxychlor': {
        'tex': 'Methoxychlor',
        'units': 'ug/L'
    },
    'methyl mercury': {
        'tex': 'Methyl Mercury',
        'units': 'ug/L'
    },
    'methyl bromide': {
        'tex': 'Methyl bromide',
        'units': 'ug/L'
    },
    'methyl ethyl ketone': {
        'tex': 'Methyl Ethyl Ketone',
        'units': 'ug/L'
    },
    'methyl isobutyl ketone': {
        'tex': 'Methyl Isobutyl Ketone',
        'units': 'ug/L'
    },
    'methyl tert-butyl ether': {
        'tex': 'Methyl Tertiary Butyl Ether',
        'units': 'ug/L'
    },
    'methylene blue active substances (mbas)': {
        'tex': 'Methylene Blue Active Substances (MBAS)',
        'units': 'ug/L'
    },
    'methylene chloride': {
        'tex': 'Methylene Chloride',
        'units': 'ug/L'
    },
    'methylnaphthalene': {
        'tex': 'Methylnaphthalene',
        'units': 'ug/L'
    },
    'molybdenum, total': {
        'tex': 'Total Molybdenum',
        'units': 'ug/L'
    },
    'n-nitrosodi-n-propylamine': {
        'tex': 'N-Nitrosodi-n-Propylamine',
        'units': 'ug/L'
    },
    'n-nitrosodimethylamine': {
        'tex': 'N-Nitrosodimethylamine',
        'units': 'ug/L'
    },
    'n-nitrosodiphenylamine': {
        'tex': 'N-Nitrosodiphenylamine',
        'units': 'ug/L'
    },
    'naphthalene': {
        'tex': 'Naphthalene',
        'units': 'ug/L'
    },
    'naphthalene,  dissolved': {
        'tex': 'Dissolved Naphthalene',
        'units': 'ug/L'
    },
    'naphthalene, suspended': {
        'tex': 'Suspended Naphthalene',
        'units': 'ug/L'
    },
    'nickel, dissolved': {
        'tex': 'Dissolved Nickel',
        'units': 'ug/L'
    },
    'nickel, total': {
        'tex': 'Total Nickel',
        'units': 'ug/L'
    },
    'dissolved nickel': {
        'tex': 'Dissolved Nickel',
        'units': 'ug/L'
    },
    'total nickel': {
        'tex': 'Total Nickel',
        'units': 'ug/L'
    },
    'nitrobenzene': {
        'tex': 'Nitrobenzene',
        'units': 'ug/L'
    },
    'nitrogen, nitrate (no3) as n': {
        'tex': 'Nitrogen, Nitrate (NO$_{3}$) as N',
        'units': 'mg/L'
    },
    'nitrogen, nitrate (no$_{3}$) as n': {
        'tex': 'Nitrogen, Nitrate (NO$_{3}$) as N',
        'units': 'mg/L'
    },
    'nitrogen, nitrite (no2) + nitrate (no3) as n': {
        'tex': 'Nitrogen, Nitrite (NO$_{2}$) + Nitrate (NO$_{3}$) as N',
        'units': 'mg/L'
    },
    'nitrogen, nitrite (no$_{2}$) + nitrate (no$_{3}$) as n': {
        'tex': 'Nitrogen, Nitrite (NO$_{2}$) + Nitrate (NO$_{3}$) as N',
        'units': 'mg/L'
    },
    'nitrogen, nitrite (no2) as n': {
        'tex': 'Nitrogen, Nitrite (NO$_{2}$) as N',
        'units': 'mg/L'
    },
    'nitrogen, nitrite (no$_{2}$) as n': {
        'tex': 'Nitrogen, Nitrite (NO$_{2}$) as N',
        'units': 'mg/L'
    },
    'nitrogen, nox as n': {
        'tex': 'Nitrogen, NO$_{x}$ as N',
        'units': 'mg/L'
    },
    'nitrogen, no$_{x}$ as n': {
        'tex': 'Nitrogen, NO$_{x}$ as N',
        'units': 'mg/L'
    },
    'nitrogen, total': {
        'tex': 'Total Nitrogen',
        'units': 'mg/L'
    },
    'total nitrogen': {
        'tex': 'Total Nitrogen',
        'units': 'mg/L'
    },
    'nitrogen, ammonia as n': {
        'tex': 'Nitrogen, Ammonia as N',
        'units': 'mg/L'
    },
    'nitrogen, ammonium (nh4) as n': {
        'tex': 'Nitrogen, Ammonium (NH4) as N',
        'units': 'mg/L'
    },
    'nitrogen, ammonium (nh4) as nh4': {
        'tex': 'Nitrogen, Ammonium (NH$_{4}$) as NH$_{4}$',
        'units': 'mg/L'
    },
    'nitrogen, unionized ammonia (nh3) as n': {
        'tex': 'Nitrogen, Unionized Ammonia (NH$_{3}$) as N',
        'units': 'mg/L'
    },
    'oil range organics': {
        'tex': 'Oil Range Organics',
        'units': 'ug/L'
    },
    'oil and grease': {
        'tex': 'Oil and Grease',
        'units': 'mg/L'
    },
    'organic nitrogen, dissolved': {
        'tex': 'Dissolved Organic Nitrogen',
        'units': 'mg/L'
    },
    'organic nitrogen, total': {
        'tex': 'Total Organic Nitrogen',
        'units': 'mg/L'
    },
    'organic carbon, dissolved': {
        'tex': 'Dissolved Organic carbon',
        'units': 'mg/L'
    },
    'organic carbon, total': {
        'tex': 'Total Organic carbon',
        'units': 'mg/L'
    },
    'oro': {
        'tex': 'ORO',
        'units': 'ug/L'
    },
    'oxidation reduction potential (orp)': {
        'tex': 'Oxidation Reduction Potential (ORP)',
        'units': 'mV'
    },
    'p-isopropyltoluene': {
        'tex': 'p-Isopropyltoluene',
        'units': 'ug/L'
    },
    "p,p'-dde": {
        'tex': "p,p'-DDE",
        'units': 'ug/L'
    },
    'pbp': {
        'tex': 'PBP',
        'units': 'ug/L'
    },
    'pentachlorophenol': {
        'tex': 'Pentachlorophenol',
        'units': 'ug/L'
    },
    'pentachlorophenol,  dissolved': {
        'tex': 'Dissolved Pentachlorophenol',
        'units': 'ug/L'
    },
    'phenanthrene': {
        'tex': 'Phenanthrene',
        'units': 'ug/L'
    },
    'phenanthrene,  dissolved': {
        'tex': 'Dissolved Phenanthrene',
        'units': 'ug/L'
    },
    'phenanthrene, suspended': {
        'tex': 'Suspended Phenanthrene',
        'units': 'ug/L'
    },
    'phenol': {
        'tex': 'Phenol',
        'units': 'ug/L'
    },
    'phenols': {
        'tex': 'Phenols',
        'units': 'ug/L'
    },
    'phosphate-phosphorus': {
        'tex': 'Phosphate-Phosphorus',
        'units': 'mg/L'
    },
    'phosphorus as p, dissolved': {
        'tex': 'Dissolved Phosphorus as P',
        'units': 'mg/L'
    },
    'dissolved phosphorus as p': {
        'tex': 'Dissolved Phosphorus as P',
        'units': 'mg/L'
    },
    'phosphorus as p, suspended': {
        'tex': 'Suspended Phosphorus as P',
        'units': 'mg/L'
    },
    'phosphorus as p, total': {
        'tex': 'Total Phosphorus as P',
        'units': 'mg/L'
    },
    'total phosphorus as p': {
        'tex': 'Total Phosphorus as P',
        'units': 'mg/L'
    },
    'phosphorus as po4, total': {
        'tex': 'Total Phosphorus as PO4',
        'units': 'mg/L'
    },
    'phosphorus, particulate organic': {
        'tex': 'Phosphorus, Particulate Organic',
        'units': 'mg/L'
    },
    'phosphorus, soluble reactive (srp)': {
        'tex': 'Phosphorus, Soluble Reactive (SRP)',
        'units': 'mg/L'
    },
    'phosphorus, organic as p, dissolved': {
        'tex': 'Dissolved Phosphorus, organic as P',
        'units': 'mg/L'
    },
    'dissolved phosphorus, organic as p': {
        'tex': 'Dissolved Phosphorus, organic as P',
        'units': 'mg/L'
    },
    'phosphorus, orthophosphate as p': {
        'tex': 'Phosphorus, Orthophosphate as P',
        'units': 'mg/L'
    },
    'phosphorus, orthophosphate as p, dissolved': {
        'tex': 'Dissolved Phosphorus, Orthophosphate as P',
        'units': 'mg/L'
    },
    'phosphorus, orthophosphate as p, suspended': {
        'tex': 'Suspended Phosphorus, Orthophosphate as P',
        'units': 'mg/L'
    },
    'phosphorus, orthophosphate as po4': {
        'tex': 'Phosphorus, Orthophosphate as PO$_{4}$',
        'units': 'mg/L'
    },
    'polycyclic aromatic hydrocarbons': {
        'tex': 'Polycyclic Aromatic Hydrocarbons',
        'units': 'ug/L'
    },
    'potassium, dissolved': {
        'tex': 'Dissolved Potassium',
        'units': 'mg/L'
    },
    'potassium, total': {
        'tex': 'Total Potassium',
        'units': 'mg/L'
    },
    'prometryn': {
        'tex': 'Prometryn',
        'units': 'ug/L'
    },
    'pyrene': {
        'tex': 'Pyrene',
        'units': 'ug/L'
    },
    'pyrene, suspended': {
        'tex': 'Suspended Pyrene',
        'units': 'ug/L'
    },
    'relative toxicity (i 25% reduction)': {
        'tex': 'RELATIVE TOXICITY (I 25\% REDUCTION)',
        'units': '%'
    },
    'relative toxicity (i 25% reduction), filtered': {
        'tex': 'RELATIVE TOXICITY (I 25\% REDUCTION, filtered)',
        'units': '%'
    },
    'ssc-total coarse fraction (>63um)': {
        'tex': 'SSC-Total Coarse Fraction ($>63$ \\si[per-mode=symbol]{\\micro\\meter})',
        'units': 'mg/L'
    },
    'ssc-total fine fraction (<63um)': {
        'tex': 'SSC-Total Fine Fraction (<63 \\si[per-mode=symbol]{\\micro\\meter})',
        'units': 'mg/L'
    },
    'ssc-total particulate solids': {
        'tex': 'SSC-Total Particulate Solids',
        'units': 'mg/L'
    },
    'sand': {
        'tex': 'Sand',
        'units': 'mg/L'
    },
    'sec-butylbenzene': {
        'tex': 'Sec-Butylbenzene',
        'units': 'ug/L'
    },
    'selenium, dissolved': {
        'tex': 'Dissolved Selenium',
        'units': 'ug/L'
    },
    'selenium, total': {
        'tex': 'Total Selenium',
        'units': 'ug/L'
    },
    'settleable solids': {
        'tex': 'Settleable Solids',
        'units': 'mg/L'
    },
    'silt': {
        'tex': 'Silt',
        'units': 'mg/L'
    },
    'silver, dissolved': {
        'tex': 'Dissolved Silver',
        'units': 'ug/L'
    },
    'silver, total': {
        'tex': 'Total Silver',
        'units': 'ug/L'
    },
    'simazine': {
        'tex': 'Simazine',
        'units': 'ug/L'
    },
    'sodium, dissolved': {
        'tex': 'Dissolved Sodium',
        'units': 'mg/L'
    },
    'sodium, total': {
        'tex': 'Total Sodium',
        'units': 'mg/L'
    },
    'specific conductance': {
        'tex': 'Specific Conductance',
        'units': 'umhos/cm'
    },
    'styrene': {
        'tex': 'Styrene',
        'units': 'ug/L'
    },
    'sulfate, dissolved': {
        'tex': 'Dissolved Sulfate',
        'units': 'mg/L'
    },
    'sulfate, total': {
        'tex': 'Total Sulfate',
        'units': 'mg/L'
    },
    'sulfide, total': {
        'tex': 'Total Sulfide',
        'units': 'mg/L'
    },
    'surfactants': {
        'tex': 'Surfactants',
        'units': 'ug/L'
    },
    'suspended sediment concentration (ssc)': {
        'tex': 'Suspended Sediment Concentration',
        'units': 'mg/L'
    },
    'temperature, water': {
        'tex': 'Temperature, water',
        'units': 'deg C'
    },
    'tetrachloroethane': {
        'tex': 'Tetrachloroethane',
        'units': 'ug/L'
    },
    'tetrachloroethylene': {
        'tex': 'Tetrachloroethylene',
        'units': 'ug/L'
    },
    'thallium, dissolved': {
        'tex': 'Dissolved Thallium',
        'units': 'ug/L'
    },
    'thallium, total': {
        'tex': 'Total Thallium',
        'units': 'ug/L'
    },
    'toluene': {
        'tex': 'Toluene',
        'units': 'ug/L'
    },
    'total coliform': {
        'tex': 'Total Coliform',
        'units': 'MPN/100 mL'
    },
    'total dissolved solids': {
        'tex': 'Total Dissolved Solids',
        'units': 'mg/L'
    },
    'total solids': {
        'tex': 'Total Solids',
        'units': 'mg/L'
    },
    'total suspended solids': {
        'tex': 'Total Suspended Solids',
        'units': 'mg/L'
    },
    'total volatile solids': {
        'tex': 'Total Volatile Solids',
        'units': 'mg/L'
    },
    'total volatile solids, filterable': {
        'tex': 'Total Volatile Solids (filterable)',
        'units': 'mg/L'
    },
    'toxaphene': {
        'tex': 'Toxaphene',
        'units': 'ug/L'
    },
    'tribromomethane': {
        'tex': 'Tribromomethane',
        'units': 'ug/L'
    },
    'trichloroethane': {
        'tex': 'Trichloroethane',
        'units': 'ug/L'
    },
    'trichloroethylene': {
        'tex': 'Trichloroethylene',
        'units': 'ug/L'
    },
    'trichlorofuoromethane': {
        'tex': 'Trichlorofuoromethane',
        'units': 'ug/L'
    },
    'trichlorotrifluoroethane': {
        'tex': 'Trichlorotrifluoroethane',
        'units': 'ug/L'
    },
    'trihalomethanes': {
        'tex': 'Trihalomethanes',
        'units': 'ug/L'
    },
    'true color': {
        'tex': 'True Color',
        'units': 'ADMI Value'
    },
    'true color': {
        'tex': 'True Color',
        'units': 'ADMI Value'
    },
    'true color, filtered': {
        'tex': 'Filtered True Color',
        'units': 'ADMI Value'
    },
    'true color, filtered': {
        'tex': 'Filtered True Color',
        'units': 'ADMI Value'
    },
    'turbidity': {
        'tex': 'Turbidity',
        'units': 'NTU'
    },
    'turbidity, filtered': {
        'tex': 'Filtered Turbidity',
        'units': 'NTU'
    },
    'vanadium, total': {
        'tex': 'Total Vanadium',
        'units': 'ug/L'
    },
    'vinyl acetate': {
        'tex': 'Vinyl Acetate',
        'units': 'ug/L'
    },
    'vinyl chloride': {
        'tex': 'Vinyl Chloride',
        'units': 'ug/L'
    },
    'xylenes, total': {
        'tex': 'Total Xylenes',
        'units': 'ug/L'
    },
    'zinc, dissolved': {
        'tex': 'Dissolved Zinc',
        'units': 'ug/L'
    },
    'zinc, suspended': {
        'tex': 'Suspended Zinc',
        'units': 'ug/L'
    },
    'zinc, total': {
        'tex': 'Total Zinc',
        'units': 'ug/L'
    },
    'dissolved zinc': {
        'tex': 'Dissolved Zinc',
        'units': 'ug/L'
    },
    'suspended zinc': {
        'tex': 'Suspended Zinc',
        'units': 'ug/L'
    },
    'total zinc': {
        'tex': 'Total Zinc',
        'units': 'ug/L'
    },
    'alpha-chlordane': {
        'tex': 'alpha-chlordane',
        'units': 'ug/L'
    },
    'cis-1,2-dichloroethylene': {
        'tex': 'cis-1,2-Dichloroethylene',
        'units': 'ug/L'
    },
    'cis-1,3-dichloropropene': {
        'tex': 'cis-1,3-Dichloropropene',
        'units': 'ug/L'
    },
    'di-n-butyl phthalate': {
        'tex': 'di-n-Butyl Phthalate',
        'units': 'ug/L'
    },
    'gamma-chlordane': {
        'tex': 'Gamma-Chlordane',
        'units': 'ug/L'
    },
    'm-dichlorobenzene': {
        'tex': 'm-Dichlorobenzene',
        'units': 'ug/L'
    },
    'm-nitroaniline': {
        'tex': 'm-Nitroaniline',
        'units': 'ug/L'
    },
    'm-xylene': {
        'tex': 'm-Xylene',
        'units': 'ug/L'
    },
    'n-butylbenzene': {
        'tex': 'n-Butylbenzene',
        'units': 'ug/L'
    },
    'n-propylbenzene': {
        'tex': 'n-Propylbenzene',
        'units': 'ug/L'
    },
    'o-chlorotoluene': {
        'tex': 'o-Chlorotoluene',
        'units': 'ug/L'
    },
    'o-dichlorobenzene': {
        'tex': 'o-Dichlorobenzene',
        'units': 'ug/L'
    },
    'o-xylene': {
        'tex': 'o-Xylene',
        'units': 'ug/L'
    },
    'p-bromophenyl phenyl ether': {
        'tex': 'p-Bromophenyl Phenyl Ether',
        'units': 'ug/L'
    },
    'p-chlorophenyl phenyl ether': {
        'tex': 'p-Chlorophenyl Phenyl Ether',
        'units': 'ug/L'
    },
    'p-chlorotoluene': {
        'tex': 'p-Chlorotoluene',
        'units': 'ug/L'
    },
    'p-cymene': {
        'tex': 'p-Cymene',
        'units': 'ug/L'
    },
    'p-dichlorobenzene': {
        'tex': 'p-Dichlorobenzene',
        'units': 'ug/L'
    },
    'p-nitrophenol': {
        'tex': 'p-Nitrophenol',
        'units': 'ug/L'
    },
    'p-xylene': {
        'tex': 'p-Xylene',
        'units': 'ug/L'
    },
    'ph': {
        'tex': 'pH',
        'units': 'SU'
    },
    'protons': {
        'tex': 'Protons (Hydrogen Ions)',
        'units': 'mg/L'
    },
    'tert-butylbenzene': {
        'tex': 'Tertiary Butylbenzene',
        'units': 'ug/L'
    },
    'total petroleum hydrocarbons, motor oil range': {
        'tex': 'Total Petroleum Hydrocarbons (motor oil range)',
        'units': 'ug/L'
    },
    'trans-1,2-dichloroethylene': {
        'tex': 'trans-1,2-Dichloroethylene',
        'units': 'ug/L'
    },
    'trans-1,3-dichloropropene': {
        'tex': 'trans-1,3-Dichloropropene',
        'units': 'ug/L'
    },
    'trans-1,4-dichloro-2-butene': {
        'tex': 'trans-1,4-Dichloro-2-butene',
        'units': 'ug/L'
    },
    'dibenzo[b,k]fluoranthene': {
        'tex': 'Dibenzo[b,k]fluoranthene',
        'units': 'ug/L'
    },
    'dichlobenil': {
        'tex': 'Dichlobenil',
        'units': 'ug/L'
    },
    'prometon': {
        'tex': 'Prometon',
        'units': 'ug/L'
    },
    'total volatile solids, non-filterable': {
        'tex': 'Total Volatile Solids (non-filterable)',
        'units': 'ug/L'
    },
    'benzo(b/j)fluoranthene': {
        'tex': 'Benzo(b/j)fluoranthene',
        'units': 'ug/L'
    },
    'bismuth': {
        'tex': 'Bismuth',
        'units': 'ug/L'
    },
    'boron': {
        'tex': 'Boron',
        'units': 'ug/L'
    },
    'lithium, total': {
        'tex': 'Lithium, Total',
        'units': 'ug/L'
    },
    'silicon': {
        'tex': 'Silicon',
        'units': 'ug/L'
    },
    'strontium': {
        'tex': 'Strontium',
        'units': 'ug/L'
    },
    'tellurium': {
        'tex': 'Tellurium',
        'units': 'ug/L'
    },
    'tin, total': {
        'tex': 'Tin, Total',
        'units': 'ug/L'
    },
    'titanium, total': {
        'tex': 'Titanium, Total',
        'units': 'ug/L'
    },
    'tungsten': {
        'tex': 'Tungsten',
        'units': 'ug/L'
    },
    'uranium': {
        'tex': 'Uranium',
        'units': 'ug/L'
    },
    'zirconium': {
        'tex': 'Zirconium',
        'units': 'ug/L'
    },
    'cesium': {
        'tex': 'Cesium',
        'units': 'ug/L'
    },
    'rubidium': {
        'tex': 'Rubidium',
        'units': 'ug/L'
    },
    '1,2-dibromo-3-chloropropane': {
        'tex': '1,2-Dibromo-3-Chloropropane',
        'units': 'ug/L'
    },
    'sec-butylbenzene': {
        'tex': 'sec-Butylbenzene',
        'units': 'ug/L'
    },
    'trans-1,2-dichloroethylenetrans-1,2-dichloroethylene': {
        'tex': 'trans-1,2-Dichloroethylenetrans-1,2-Dichloroethylene',
        'units': 'ug/L'
    },
    '2,4,5-t': {
        'tex': '2,4,5-T',
        'units': 'ug/L'
    },
    '2,4-db': {
        'tex': '2,4-DB',
        'units': 'ug/L'
    },
    'dalapon': {
        'tex': 'Dalapon',
        'units': 'ug/L'
    },
    'dicamba': {
        'tex': 'Dicamba',
        'units': 'ug/L'
    },
    'dichlorprop': {
        'tex': 'Dichlorprop',
        'units': 'ug/L'
    },
    'mcpa': {
        'tex': 'MCPA',
        'units': 'ug/L'
    },
    'mecoprop': {
        'tex': 'Mecoprop',
        'units': 'ug/L'
    },
    'sulfur': {
        'tex': 'Sulfur',
        'units': 'ug/L'
    },
    'm,p-xylenes': {
        'tex': 'm,p-Xylenes',
        'units': 'ug/L'
    },
    'silica': {
        'tex': 'Silica',
        'units': 'ug/L'
    },
    'nitrogen, dissolved': {
        'tex': 'Nitrogen, Dissolved',
        'units': 'ug/L'
    },
    '2-chloroethyl vinyl ether': {
        'tex': '2-Chloroethyl vinyl ether',
        'units': 'ug/L'
    },
    'ethyl methacrylate': {
        'tex': 'Ethyl methacrylate',
        'units': 'ug/L'
    },
    'meta & para xylene mix': {
        'tex': 'meta & para Xylene mix',
        'units': 'ug/L'
    },
    'temperature, air': {
        'tex': 'Temperature, air',
        'units': 'ug/L'
    },
    'gasoline range organics': {
        'tex': 'Gasoline range organics',
        'units': 'ug/L'
    },
    'particle size, percent > 50 microns': {
        'tex': 'Particle Size, Percent > 50 microns',
        'units': 'ug/L'
    },
    'chlorophyll a, uncorrected for pheophytin': {
        'tex': 'Chlorophyll A (uncorrected for pheophytin)',
        'units': 'ug/L'
    },
    '1-methylphenanthrene': {
        'tex': '1-Methylphenanthrene',
        'units': 'ug/L'
    },
    '2,6-dimethylnaphthalene': {
        'tex': '2,6-Dimethylnaphthalene',
        'units': 'ug/L'
    },
    'benzo[e]pyrene': {
        'tex': 'Benzo[e]pyrene',
        'units': 'ug/L'
    },
    'bifenthrin by nci': {
        'tex': 'Bifenthrin by NCI',
        'units': 'ug/L'
    },
    'cobalt, dissolved': {
        'tex': 'Cobalt, Dissolved',
        'units': 'ug/L'
    },
    'cyfluthrin by nci': {
        'tex': 'Cyfluthrin by NCI',
        'units': 'ug/L'
    },
    'cypermethrin': {
        'tex': 'Cypermethrin',
        'units': 'ug/L'
    },
    'dibenzothiophene': {
        'tex': 'Dibenzothiophene',
        'units': 'ug/L'
    },
    'esfenvalerate': {
        'tex': 'Esfenvalerate',
        'units': 'ug/L'
    },
    'fenvalerate': {
        'tex': 'Fenvalerate',
        'units': 'ug/L'
    },
    'l-cyhalothrin by nci': {
        'tex': 'L-Cyhalothrin by NCI',
        'units': 'ug/L'
    },
    'molybdenum, dissolved': {
        'tex': 'Molybdenum, Dissolved',
        'units': 'ug/L'
    },
    'permethrin': {
        'tex': 'Permethrin',
        'units': 'ug/L'
    },
    'tin, dissolved': {
        'tex': 'Tin, Dissolved',
        'units': 'ug/L'
    },
    'titanium, dissolved': {
        'tex': 'Titanium, Dissolved',
        'units': 'ug/L'
    },
    'vanadium, dissolved': {
        'tex': 'Vanadium, Dissolved',
        'units': 'ug/L'
    },
    'cypermethrin by nci': {
        'tex': 'Cypermethrin by NCI',
        'units': 'ug/L'
    },
    'bicarbonate': {
        'tex': 'Bicarbonate',
        'units': 'ug/L'
    }
}


