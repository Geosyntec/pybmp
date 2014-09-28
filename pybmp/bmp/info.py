__all__ = ['getUnits', 'getTexParam', 'getTexUnit',
           'getNormalization', 'getConversion']

def getUnits(param):
    '''
    Returns the standard units for a given parameter
    '''
    return parameters[param.strip()]['units']


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
    return parameters[param.strip()]['tex']


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
    return units[parameters[param.strip()]['units']]['factor']

def addParameter(name, units, tex=None):
    if tex is None:
        tex = name
    values = {
        'tex': tex,
        'units': units
    }
    parameters[name] = values
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
    '1,1,1,2-Tetrachloroethane': {
        'tex': '1,1,1,2-Tetrachloroethane',
        'units': 'ug/L'
    },
    '1,1,1-Trichloroethane': {
        'tex': '1,1,1-Trichloroethane',
        'units': 'ug/L'
    },
    '1,1,2,2-Tetrachloroethane': {
        'tex': '1,1,2,2-Tetrachloroethane',
        'units': 'ug/L'
    },
    '1,1,2-Trichloroethane': {
        'tex': '1,1,2-Trichloroethane',
        'units': 'ug/L'
    },
    '1,1-Dichloroethane': {
        'tex': '1,1-Dichloroethane',
        'units': 'ug/L'
    },
    '1,1-Dichloroethylene': {
        'tex': '1,1-Dichloroethylene',
        'units': 'ug/L'
    },
    '1,1-Dichloropropene': {
        'tex': '1,1-Dichloropropene',
        'units': 'ug/L'
    },
    '1,2,3-Trichlorobenzene': {
        'tex': '1,2,3-Trichlorobenzene',
        'units': 'ug/L'
    },
    '1,2,3-Trichloropropane': {
        'tex': '1,2,3-Trichloropropane',
        'units': 'ug/L'
    },
    '1,2,4-Trichlorobenzene': {
        'tex': '1,2,4-Trichlorobenzene',
        'units': 'ug/L'
    },
    '1,2,4-Trimethylbenzene': {
        'tex': '1,2,4-Trimethylbenzene',
        'units': 'ug/L'
    },
    '1,2-Benzanthracene': {
        'tex': '1,2-Benzanthracene',
        'units': 'ug/L'
    },
    '1,2-Dibromo-3-Chloropropane': {
        'tex': '1,2-Dibromo-3-Chloropropane',
        'units': 'ug/L'
    },
    '1,2-Dibromoethane': {
        'tex': '1,2-Dibromoethane',
        'units': 'ug/L'
    },
    '1,2-Dichlorobenzene': {
        'tex': '1,2-Dichlorobenzene',
        'units': 'ug/L'
    },
    '1,2-Dichloroethane': {
        'tex': '1,2-Dichloroethane',
        'units': 'ug/L'
    },
    '1,2-Dichloropropane': {
        'tex': '1,2-Dichloropropane',
        'units': 'ug/L'
    },
    '1,2-Diphenylhydrazine': {
        'tex': '1,2-Diphenylhydrazine',
        'units': 'ug/L'
    },
    '1,3,5-Trimethylbenzene': {
        'tex': '1,3,5-Trimethylbenzene',
        'units': 'ug/L'
    },
    '1,3-Dichlorobenzene': {
        'tex': '1,3-Dichlorobenzene',
        'units': 'ug/L'
    },
    '1,3-Dichloropropane': {
        'tex': '1,3-Dichloropropane',
        'units': 'ug/L'
    },
    '1,4-Dichlorobenzene': {
        'tex': '1,4-Dichlorobenzene',
        'units': 'ug/L'
    },
    '1-Chlorohexane': {
        'tex': '1-Chlorohexane',
        'units': 'ug/L'
    },
    '1-Methylnaphthalene': {
        'tex': '1-Methylnaphthalene',
        'units': 'ug/L'
    },
    '2,2-Dichloropropane': {
        'tex': '2,2-Dichloropropane',
        'units': 'ug/L'
    },
    "2,4'-DDD": {
        'tex': "2,4'-DDD",
        'units': 'ug/L'
    },
    "2,4'-DDE": {
        'tex': "2,4'-DDE",
        'units': 'ug/L'
    },
    "2,4'-DDT": {
        'tex': "2,4'-DDT",
        'units': 'ug/L'
    },
    '2,4,5-TP-SILVEX': {
        'tex': '2,4,5-TP-SILVEX',
        'units': 'ug/L'
    },
    '2,4,5-Trichlorophenol': {
        'tex': '2,4,5-Trichlorophenol',
        'units': 'ug/L'
    },
    '2,4,6-Trichlorophenol': {
        'tex': '2,4,6-Trichlorophenol',
        'units': 'ug/L'
    },
    '2,4-D': {
        'tex': '2,4-D',
        'units': 'ug/L'
    },
    '2,4-Dichlorophenol': {
        'tex': '2,4-Dichlorophenol',
        'units': 'ug/L'
    },
    '2,4-Dinitrophenol': {
        'tex': '2,4-Dinitrophenol',
        'units': 'ug/L'
    },
    '2,4-Dinitrotoluene': {
        'tex': '2,4-Dinitrotoluene',
        'units': 'ug/L'
    },
    '2,4-Dimethylphenol': {
        'tex': '2,4-Dimethylphenol',
        'units': 'ug/L'
    },
    '2,6-Dinitrotoluene': {
        'tex': '2,6-Dinitrotoluene',
        'units': 'ug/L'
    },
    '2-Butanone': {
        'tex': '2-Butanone',
        'units': 'ug/L'
    },
    '2-Chloroethyl Vinyl Ether': {
        'tex': '2-Chloroethyl Vinyl Ether',
        'units': 'ug/L'
    },
    '2-Chloronaphthalene': {
        'tex': '2-Chloronaphthalene',
        'units': 'ug/L'
    },
    '2-Chlorophenol': {
        'tex': '2-Chlorophenol',
        'units': 'ug/L'
    },
    '2-Chlorotoluene': {
        'tex': '2-Chlorotoluene',
        'units': 'ug/L'
    },
    '2-Hexanone': {
        'tex': '2-Hexanone',
        'units': 'ug/L'
    },
    '2-Methylnaphthalene': {
        'tex': '2-Methylnaphthalene',
        'units': 'ug/L'
    },
    '2-Nitrophenol': {
        'tex': '2-Nitrophenol',
        'units': 'ug/L'
    },
    "3,3'-Dichlorobenzidine": {
        'tex': "3,3'-Dichlorobenzidine",
        'units': 'ug/L'
    },
    "4,4'-DDD": {
        'tex': "4,4'-DDD",
        'units': 'ug/L'
    },
    "4,4'-DDE": {
        'tex': "4,4'-DDE",
        'units': 'ug/L'
    },
    "4,4'-DDT": {
        'tex': "4,4'-DDT",
        'units': 'ug/L'
    },
    '4,6-Dinitro-2-methylphenol': {
        'tex': '4,6-Dinitro-2-methylphenol',
        'units': 'ug/L'
    },
    '4,6-Dinitro-o-cresol': {
        'tex': '4,6-Dinitro-o-cresol',
        'units': 'ug/L'
    },
    '4-Bromophenyl phenyl ether': {
        'tex': '4-Bromophenyl phenyl ether',
        'units': 'ug/L'
    },
    '4-Chlorophenyl phenyl ether': {
        'tex': '4-Chlorophenyl phenyl ether',
        'units': 'ug/L'
    },
    '4-Chlorotoluene': {
        'tex': '4-Chlorotoluene',
        'units': 'ug/L'
    },
    '4-Nitrophenol': {
        'tex': '4-Nitrophenol',
        'units': 'ug/L'
    },
    '4-chloro-3-methylphenol': {
        'tex': '4-Chloro-3-methylphenol',
        'units': 'ug/L'
    },
    '4-chloro-3-methylphenol,  Dissolved': {
        'tex': 'Dissolved 4-Chloro-3-methylphenol',
        'units': 'ug/L'
    },
    '4-Hydroxy-4-methyl-2-pentanone': {
        'tex': '4-Hydroxy-4-methyl-2-pentanone',
        'units': 'ug/L'
    },
    'Acenaphthene': {
        'tex': 'Acenaphthene',
        'units': 'ug/L'
    },
    'Acenaphthene,  Dissolved': {
        'tex': 'Dissolved Acenaphthene',
        'units': 'ug/L'
    },
    'Acenaphthylene': {
        'tex': 'Acenaphthylene',
        'units': 'ug/L'
    },
    'Acenaphthylene, Suspended': {
        'tex': 'Suspended Acenaphthylene',
        'units': 'ug/L'
    },
    'Acetone': {
        'tex': 'Acetone',
        'units': 'ug/L'
    },
    'Acrolein': {
        'tex': 'Acrolein',
        'units': 'ug/L'
    },
    'Acrylonitrile': {
        'tex': 'Acrylonitrile',
        'units': 'ug/L'
    },
    'Alachlor': {
        'tex': 'Alachlor',
        'units': 'ug/L'
    },
    'Aldrin': {
        'tex': 'Aldrin',
        'units': 'ug/L'
    },
    'Alkalinity': {
        'tex': 'Alkalinity',
        'units': 'mg/L'
    },
    'Alkalinity, carbonate as CaCO3': {
        'tex': 'Alkalinity, carbonate as CaCO$_{3}$',
        'units': 'mg/L'
    },
    'Aluminum, Dissolved': {
        'tex': 'Dissolved Aluminum',
        'units': 'ug/L'
    },
    'Aluminum, Total': {
        'tex': 'Total Aluminum',
        'units': 'ug/L'
    },
    'Anthracene': {
        'tex': 'Anthracene',
        'units': 'ug/L'
    },
    'Anthracene, Suspended': {
        'tex': 'Suspended Anthracene',
        'units': 'ug/L'
    },
    'Antimony, Dissolved': {
        'tex': 'Dissolved Antimony',
        'units': 'ug/L'
    },
    'Antimony, Total': {
        'tex': 'Total Antimony',
        'units': 'ug/L'
    },
    'Aroclor 1016': {
        'tex': 'Aroclor 1016',
        'units': 'ug/L'
    },
    'Aroclor 1221': {
        'tex': 'Aroclor 1221',
        'units': 'ug/L'
    },
    'Aroclor 1232': {
        'tex': 'Aroclor 1232',
        'units': 'ug/L'
    },
    'Aroclor 1242': {
        'tex': 'Aroclor 1242',
        'units': 'ug/L'
    },
    'Aroclor 1248': {
        'tex': 'Aroclor 1248',
        'units': 'ug/L'
    },
    'Aroclor 1254': {
        'tex': 'Aroclor 1254',
        'units': 'ug/L'
    },
    'Aroclor 1260': {
        'tex': 'Aroclor 1260',
        'units': 'ug/L'
    },
    'Arsenic, Dissolved': {
        'tex': 'Dissolved Arsenic',
        'units': 'ug/L'
    },
    'Arsenic, Total': {
        'tex': 'Total Arsenic',
        'units': 'ug/L'
    },
    'Atrazine': {
        'tex': 'Atrazine',
        'units': 'ug/L'
    },
    'BHC-ALPHA': {
        'tex': 'BHC-ALPHA',
        'units': 'ug/L'
    },
    'BHC-BETA': {
        'tex': 'BHC-BETA',
        'units': 'ug/L'
    },
    'BHC-DELTA': {
        'tex': 'BHC-DELTA',
        'units': 'ug/L'
    },
    'BOD': {
        'tex': 'BOD',
        'units': 'mg/L'
    },
    'BOD, non-standard conditions': {
        'tex': 'BOD, non-standard conditions',
        'units': 'mg/L'
    },
    'Barium, Dissolved': {
        'tex': 'Dissolved Barium',
        'units': 'ug/L'
    },
    'Barium, Total': {
        'tex': 'Total Barium',
        'units': 'ug/L'
    },
    'Benz[a]anthracene': {
        'tex': 'Benz[a]anthracene',
        'units': 'ug/L'
    },
    'Benz[a]anthracene, Suspended': {
        'tex': 'Suspended Benz[a]anthracene',
        'units': 'ug/L'
    },
    'Benzene': {
        'tex': 'Benzene',
        'units': 'ug/L'
    },
    'Benzidine': {
        'tex': 'Benzidine',
        'units': 'ug/L'
    },
    'Benzo(b)fluoranthene': {
        'tex': 'Benzo(b)fluoranthene',
        'units': 'ug/L'
    },
    'Benzo(b)fluoranthene, Suspended': {
        'tex': 'Suspended Benzo(b)fluoranthene',
        'units': 'ug/L'
    },
    'Benzo[a]pyrene': {
        'tex': 'Benzo[a]pyrene',
        'units': 'ug/L'
    },
    'Benzo[a]pyrene, Suspended': {
        'tex': 'Suspended Benzo[a]pyrene',
        'units': 'ug/L'
    },
    'Benzo[ghi]perylene': {
        'tex': 'Benzo[ghi]perylene',
        'units': 'ug/L'
    },
    'Benzo[ghi]perylene, Suspended': {
        'tex': 'Suspended Benzo[ghi]perylene',
        'units': 'ug/L'
    },
    'Benzo[k]fluoranthene': {
        'tex': 'Benzo[k]fluoranthene',
        'units': 'ug/L'
    },
    'Benzo[k]fluoranthene, Suspended': {
        'tex': 'Suspended Benzo[k]fluoranthene',
        'units': 'ug/L'
    },
    'Benzoic acid': {
        'tex': 'Benzoic acid',
        'units': 'ug/L'
    },
    'Benzyl alcohol': {
        'tex': 'Benzyl alcohol',
        'units': 'ug/L'
    },
    'Beryllium, Dissolved': {
        'tex': 'Dissolved Beryllium',
        'units': 'ug/L'
    },
    'Beryllium, Total': {
        'tex': 'Total Beryllium',
        'units': 'ug/L'
    },
    'Biphenyl': {
        'tex': 'Biphenyl',
        'units': 'ug/L'
    },
    'Bis(2-chloro-1-methylethyl) ether': {
        'tex': 'Bis(2-chloro-1-methylethyl) ether',
        'units': 'ug/L'
    },
    'Bis(2-chloroethoxy)methane': {
        'tex': 'Bis(2-chloroethoxy)methane',
        'units': 'ug/L'
    },
    'Bis(2-chloroethyl) ether': {
        'tex': 'Bis(2-chloroethyl) ether',
        'units': 'ug/L'
    },
    'Bis(2-chloroisopropyl) ether': {
        'tex': 'Bis(2-chloroisopropyl) ether',
        'units': 'ug/L'
    },
    'Bis(2-ethylhexyl) phthalate': {
        'tex': 'Bis(2-ethylhexyl) phthalate',
        'units': 'ug/L'
    },
    'Bis(n-octyl)phthalate': {
        'tex': 'Bis(n-octyl)phthalate',
        'units': 'ug/L'
    },
    'Bromobenzene': {
        'tex': 'Bromobenzene',
        'units': 'ug/L'
    },
    'Bromochloroiodomethane': {
        'tex': 'Bromochloroiodomethane',
        'units': 'ug/L'
    },
    'Bromoform': {
        'tex': 'Bromoform',
        'units': 'ug/L'
    },
    'Bromomethane': {
        'tex': 'Bromomethane',
        'units': 'ug/L'
    },
    'Butyl benzyl phthalate': {
        'tex': 'Butyl benzyl phthalate',
        'units': 'ug/L'
    },
    'CBOD': {
        'tex': 'CBOD',
        'units': 'mg/L'
    },
    'CFC-11': {
        'tex': 'CFC-11',
        'units': 'ug/L'
    },
    'CFC-12': {
        'tex': 'CFC-12',
        'units': 'ug/L'
    },
    'Cadmium, Dissolved': {
        'tex': 'Dissolved Cadmium',
        'units': 'ug/L'
    },
    'Cadmium, Suspended': {
        'tex': 'Suspended Cadmium',
        'units': 'ug/L'
    },
    'Cadmium, Total': {
        'tex': 'Total Cadmium',
        'units': 'ug/L'
    },
    'Calcium as CaCO3, Total': {
        'tex': 'Total Calcium as CaCO$_{3}$',
        'units': 'mg/L'
    },
    'Calcium, Dissolved': {
        'tex': 'Dissolved Calcium',
        'units': 'mg/L'
    },
    'Calcium, Total': {
        'tex': 'Total Calcium',
        'units': 'mg/L'
    },
    'Carbofuran': {
        'tex': 'Carbofuran',
        'units': 'ug/L'
    },
    'Carbon Disulfide': {
        'tex': 'Carbon Disulfide',
        'units': 'ug/L'
    },
    'Carbon Fraction, Particulate Organic Material': {
        'tex': 'Carbon Fraction, Particulate Organic Material',
        'units': 'mg/L'
    },
    'Carbon Tetrachloride': {
        'tex': 'Carbon Tetrachloride',
        'units': 'ug/L'
    },
    'Carbon disulfide': {
        'tex': 'Carbon disulfide',
        'units': 'ug/L'
    },
    'Carbon tetrachloride': {
        'tex': 'Carbon tetrachloride',
        'units': 'ug/L'
    },
    'Chemical oxygen demand': {
        'tex': 'Chemical oxygen demand',
        'units': 'mg/L'
    },
    'Chlordane': {
        'tex': 'Chlordane',
        'units': 'ug/L'
    },
    'Chloride, Dissolved': {
        'tex': 'Dissolved Chloride',
        'units': 'mg/L'
    },
    'Chloride, Total': {
        'tex': 'Total Chloride',
        'units': 'mg/L'
    },
    'Chlorobenzene': {
        'tex': 'Chlorobenzene',
        'units': 'ug/L'
    },
    'Chlorodibromomethane': {
        'tex': 'Chlorodibromomethane',
        'units': 'ug/L'
    },
    'Chloroethane': {
        'tex': 'Chloroethane',
        'units': 'ug/L'
    },
    'Chloroform': {
        'tex': 'Chloroform',
        'units': 'ug/L'
    },
    'Chloromethane': {
        'tex': 'Chloromethane',
        'units': 'ug/L'
    },
    'Chlorotoluene': {
        'tex': 'Chlorotoluene',
        'units': 'ug/L'
    },
    'Chlorpyrifos': {
        'tex': 'Chlorpyrifos',
        'units': 'ug/L'
    },
    'Chromium(VI), Dissolved': {
        'tex': 'Dissolved Chromium(VI)',
        'units': 'ug/L'
    },
    'Chromium(VI), Total': {
        'tex': 'Total Chromium(VI)',
        'units': 'ug/L'
    },
    'Chromium, Dissolved': {
        'tex': 'Dissolved Chromium',
        'units': 'ug/L'
    },
    'Chromium, Suspended': {
        'tex': 'Suspended Chromium',
        'units': 'ug/L'
    },
    'Chromium, Total': {
        'tex': 'Total Chromium',
        'units': 'ug/L'
    },
    'Chrysene': {
        'tex': 'Chrysene',
        'units': 'ug/L'
    },
    'Chrysene, Suspended': {
        'tex': 'Suspended Chrysene',
        'units': 'ug/L'
    },
    'Cobalt, Total': {
        'tex': 'Total Cobalt',
        'units': 'ug/L'
    },
    'Copper, Dissolved': {
        'tex': 'Dissolved Copper',
        'units': 'ug/L'
    },
    'Copper, Suspended': {
        'tex': 'Suspended Copper',
        'units': 'ug/L'
    },
    'Copper, Total': {
        'tex': 'Total Copper',
        'units': 'ug/L'
    },
    'Cumene': {
        'tex': 'Cumene',
        'units': 'ug/L'
    },
    'Cyanazine': {
        'tex': 'Cyanazine',
        'units': 'ug/L'
    },
    'Cyanide': {
        'tex': 'Cyanide',
        'units': 'mg/L'
    },
    'DACONIL': {
        'tex': 'DACONIL',
        'units': 'ug/L'
    },
    'Di(2-ethylhexyl) phthalate': {
        'tex': 'Di(2-ethylhexyl) phthalate',
        'units': 'ug/L'
    },
    'Di-n-octyl phthalate': {
        'tex': 'Di-n-octyl phthalate',
        'units': 'ug/L'
    },
    'Diazinon': {
        'tex': 'Diazinon',
        'units': 'ug/L'
    },
    'Dibenz[a,h]anthracene': {
        'tex': 'Dibenz[a,h]anthracene',
        'units': 'ug/L'
    },
    'Dibenz[a,h]anthracene,  Dissolved': {
        'tex': 'Dissolved Dibenz[a,h]anthracene',
        'units': 'ug/L'
    },
    'Dibenzofuran': {
        'tex': 'Dibenzofuran',
        'units': 'ug/L'
    },
    'Dibromomethane': {
        'tex': 'Dibromomethane',
        'units': 'ug/L'
    },
    'Dibromodichloromethane': {
        'tex': 'Dibromodichloromethane',
        'units': 'ug/L'
    },
    'Dibutyl phthalate': {
        'tex': 'Dibutyl phthalate',
        'units': 'ug/L'
    },
    'Dichlorobromomethane': {
        'tex': 'Dichlorobromomethane',
        'units': 'ug/L'
    },
    'Dichlorodifluoromethane': {
        'tex': 'Dichlorodifluoromethane',
        'units': 'ug/L'
    },
    'Dichlorophenol': {
        'tex': 'Dichlorophenol',
        'units': 'ug/L'
    },
    'Dinitrophenol': {
        'tex': 'Dinitrophenol',
        'units': 'ug/L'
    },
    'Dieldrin': {
        'tex': 'Dieldrin',
        'units': 'ug/L'
    },
    'Diethyl phthalate': {
        'tex': 'Diethyl phthalate',
        'units': 'ug/L'
    },
    'Dimethyl phthalate': {
        'tex': 'Dimethyl phthalate',
        'units': 'ug/L'
    },
    'Dimethylnaphthalene': {
        'tex': 'Dimethylnaphthalene',
        'units': 'ug/L'
    },
    'Dissolved oxygen (DO)': {
        'tex': 'Dissolved oxygen (DO)',
        'units': 'mg/L'
    },
    'DRO': {
        'tex': 'DRO',
        'units': 'ug/L'
    },
    'Endosulfan I': {
        'tex': 'Endosulfan I',
        'units': 'ug/L'
    },
    'Endosulfan I (alpha)': {
        'tex': 'Endosulfan I (alpha)',
        'units': 'ug/L'
    },
    '.alpha.-Endosulfan,  Dissolved': {
        'tex': 'Dissolved, Endosulfan I (alpha)',
        'units': 'ug/L'
    },
    'Endosulfan II': {
        'tex': 'Endosulfan II',
        'units': 'ug/L'
    },
    'Endosulfan II (beta)': {
        'tex': 'Endosulfan II (beta)',
        'units': 'ug/L'
    },
    '.beta.-Endosulfan,  Dissolved': {
        'tex': 'Dissolved, Endosulfan II (beta)',
        'units': 'ug/L'
    },
    'Endosulfan sulfate': {
        'tex': 'Endosulfan sulfate',
        'units': 'ug/L'
    },
    'Endrin': {
        'tex': 'Endrin',
        'units': 'ug/L'
    },
    'Endrin aldehyde': {
        'tex': 'Endrin aldehyde',
        'units': 'ug/L'
    },
    'Endrin ketone': {
        'tex': 'Endrin ketone',
        'units': 'ug/L'
    },
    'Enterococcus': {
        'tex': 'Enterococcus',
        'units': 'MPN/100 mL'
    },
    'Escherichia coli': {
        'tex': 'Escherichia coli',
        'units': 'MPN/100 mL'
    },
    'Ethyl Methacrylate': {
        'tex': 'Ethyl Methacrylate',
        'units': 'ug/L'
    },
    'Ethylbenzene': {
        'tex': 'Ethylbenzene',
        'units': 'ug/L'
    },
    'Ethylene dibromide': {
        'tex': 'Ethylene dibromide',
        'units': 'ug/L'
    },
    'Fecal Coliform': {
        'tex': 'Fecal Coliform',
        'units': 'MPN/100 mL'
    },
    'Fecal Streptococcus Group Bacteria': {
        'tex': 'Fecal Streptococcus Group Bacteria',
        'units': 'MPN/100 mL'
    },
    'Fluoranthene': {
        'tex': 'Fluoranthene',
        'units': 'ug/L'
    },
    'Fluoranthene, Suspended': {
        'tex': 'Suspended Fluoranthene',
        'units': 'ug/L'
    },
    'Fluorene': {
        'tex': 'Fluorene',
        'units': 'ug/L'
    },
    'Fluorene, Suspended': {
        'tex': 'Suspended Fluorene',
        'units': 'ug/L'
    },
    'Fluoride, Dissolved': {
        'tex': 'Dissolved Fluoride',
        'units': 'mg/L'
    },
    'Fluoride, Total': {
        'tex': 'Total Fluoride',
        'units': 'mg/L'
    },
    'Glyphosate': {
        'tex': 'Glyphosate',
        'units': 'ug/L'
    },
    'Halon 1011': {
        'tex': 'Halon 1011',
        'units': 'ug/L'
    },
    'Hardness': {
        'tex': 'Hardness',
        'units': 'mg/L'
    },
    'Hardness, non-carbonate': {
        'tex': 'Hardness, non-carbonate',
        'units': 'mg/L'
    },
    'Heptachlor': {
        'tex': 'Heptachlor',
        'units': 'ug/L'
    },
    'Heptachlor epoxide': {
        'tex': 'Heptachlor epoxide',
        'units': 'ug/L'
    },
    'Hexachlorobenzene': {
        'tex': 'Hexachlorobenzene',
        'units': 'ug/L'
    },
    'Hexachlorobutadiene': {
        'tex': 'Hexachlorobutadiene',
        'units': 'ug/L'
    },
    'Hexachlorocyclopentadiene': {
        'tex': 'Hexachlorocyclopentadiene',
        'units': 'ug/L'
    },
    'Hexachloroethane': {
        'tex': 'Hexachloroethane',
        'units': 'ug/L'
    },
    'Hydrocarbons, total petroleum (TPH)': {
        'tex': 'Hydrocarbons, total petroleum (TPH)',
        'units': 'ug/L'
    },
    'Hydrocarbons, total petroleum, diesel range organics': {
        'tex': 'Hydrocarbons, total petroleum, diesel range organics',
        'units': 'ug/L'
    },
    'Hydrocarbons, total petroleum, gasoline range organics': {
        'tex': 'Hydrocarbons, total petroleum, gasoline range organics',
        'units': 'ug/L'
    },
    'Indeno[1,2,3-cd]pyrene': {
        'tex': 'Indeno[1,2,3-cd]pyrene',
        'units': 'ug/L'
    },
    'Indeno[1,2,3-cd]pyrene, Suspended': {
        'tex': 'Suspended Indeno[1,2,3-cd]pyrene',
        'units': 'ug/L'
    },
    'Inorganic Carbon, Total': {
        'tex': 'Total Inorganic Carbon',
        'units': 'mg/L'
    },
    'Iodomethane': {
        'tex': 'Iodomethane',
        'units': 'ug/L'
    },
    'Iron, Dissolved': {
        'tex': 'Dissolved Iron',
        'units': 'ug/L'
    },
    'Iron, Total': {
        'tex': 'Total Iron',
        'units': 'ug/L'
    },
    'Isophorone': {
        'tex': 'Isophorone',
        'units': 'ug/L'
    },
    'Isopropylbenzene': {
        'tex': 'Isopropylbenzene',
        'units': 'ug/L'
    },
    'Kjeldahl nitrogen (TKN)': {
        'tex': 'Total Kjeldahl nitrogen',
        'units': 'mg/L'
    },
    'Kjeldahl nitrogen, Dissolved': {
        'tex': 'Dissolved Kjeldahl nitrogen',
        'units': 'mg/L'
    },
    'Kjeldahl nitrogen, Suspended': {
        'tex': 'Suspended Kjeldahl nitrogen',
        'units': 'mg/L'
    },
    'Lead, Dissolved': {
        'tex': 'Dissolved Lead',
        'units': 'ug/L'
    },
    'Lead, Suspended': {
        'tex': 'Suspended Lead',
        'units': 'ug/L'
    },
    'Lead, Total': {
        'tex': 'Total Lead',
        'units': 'ug/L'
    },
    'Lindane': {
        'tex': 'Lindane',
        'units': 'ug/L'
    },
    'Lithium, Dissolved': {
        'tex': 'Dissolved Lithium',
        'units': 'ug/L'
    },
    'Magnesium, Dissolved': {
        'tex': 'Dissolved Magnesium',
        'units': 'ug/L'
    },
    'Magnesium, Total': {
        'tex': 'Total Magnesium',
        'units': 'ug/L'
    },
    'Malathion': {
        'tex': 'Malathion',
        'units': 'ug/L'
    },
    'Manganese, Dissolved': {
        'tex': 'Dissolved Manganese',
        'units': 'ug/L'
    },
    'Manganese, Total': {
        'tex': 'Total Manganese',
        'units': 'ug/L'
    },
    'Mercury, Dissolved': {
        'tex': 'Dissolved Mercury',
        'units': 'ug/L'
    },
    'Mercury, Total': {
        'tex': 'Total Mercury',
        'units': 'ug/L'
    },
    'Methoxychlor': {
        'tex': 'Methoxychlor',
        'units': 'ug/L'
    },
    'Methyl Mercury': {
        'tex': 'Methyl Mercury',
        'units': 'ug/L'
    },
    'Methyl bromide': {
        'tex': 'Methyl bromide',
        'units': 'ug/L'
    },
    'Methyl ethyl ketone': {
        'tex': 'Methyl ethyl ketone',
        'units': 'ug/L'
    },
    'Methyl isobutyl ketone': {
        'tex': 'Methyl isobutyl ketone',
        'units': 'ug/L'
    },
    'Methyl tert-butyl ether': {
        'tex': 'Methyl tert-butyl ether',
        'units': 'ug/L'
    },
    'Methylene Blue Active Substances (MBAS)': {
        'tex': 'Methylene Blue Active Substances (MBAS)',
        'units': 'ug/L'
    },
    'Methylene Chloride': {
        'tex': 'Methylene Chloride',
        'units': 'ug/L'
    },
    'Methylnaphthalene': {
        'tex': 'Methylnaphthalene',
        'units': 'ug/L'
    },
    'Molybdenum, Total': {
        'tex': 'Total Molybdenum',
        'units': 'ug/L'
    },
    'N-Nitrosodi-n-propylamine': {
        'tex': 'N-Nitrosodi-n-propylamine',
        'units': 'ug/L'
    },
    'N-Nitrosodimethylamine': {
        'tex': 'N-Nitrosodimethylamine',
        'units': 'ug/L'
    },
    'N-Nitrosodiphenylamine': {
        'tex': 'N-Nitrosodiphenylamine',
        'units': 'ug/L'
    },
    'Naphthalene': {
        'tex': 'Naphthalene',
        'units': 'ug/L'
    },
    'Naphthalene,  Dissolved': {
        'tex': 'Dissolved Naphthalene',
        'units': 'ug/L'
    },
    'Naphthalene, Suspended': {
        'tex': 'Suspended Naphthalene',
        'units': 'ug/L'
    },
    'Nickel, Dissolved': {
        'tex': 'Dissolved Nickel',
        'units': 'ug/L'
    },
    'Nickel, Total': {
        'tex': 'Total Nickel',
        'units': 'ug/L'
    },
    'Nitrobenzene': {
        'tex': 'Nitrobenzene',
        'units': 'ug/L'
    },
    'Nitrogen, Nitrate (NO3) as N': {
        'tex': 'Nitrogen, Nitrate (NO$_{3}$) as N',
        'units': 'mg/L'
    },
    'Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N': {
        'tex': 'Nitrogen, Nitrite (NO$_{2}$) + Nitrate (NO$_{3}$) as N',
        'units': 'mg/L'
    },
    'Nitrogen, Nitrite (NO2) as N': {
        'tex': 'Nitrogen, Nitrite (NO$_{2}$) as N',
        'units': 'mg/L'
    },
    'Nitrogen, NOx as N': {
        'tex': 'Nitrogen, NO$_{x}$ as N',
        'units': 'mg/L'
    },
    'Nitrogen, Total': {
        'tex': 'Total Nitrogen',
        'units': 'mg/L'
    },
    'Nitrogen, ammonia as N': {
        'tex': 'Nitrogen, ammonia as N',
        'units': 'mg/L'
    },
    'Nitrogen, ammonium (NH4) as N': {
        'tex': 'Nitrogen, ammonium (NH4) as N',
        'units': 'mg/L'
    },
    'Nitrogen, ammonium (NH4) as NH4': {
        'tex': 'Nitrogen, ammonium (NH$_{4}$) as NH$_{4}$',
        'units': 'mg/L'
    },
    'Nitrogen, unionized ammonia (NH3) as N': {
        'tex': 'Nitrogen, unionized ammonia (NH$_{3}$) as N',
        'units': 'mg/L'
    },
    'Oil Range Organics': {
        'tex': 'Oil Range Organics',
        'units': 'ug/L'
    },
    'Oil and Grease': {
        'tex': 'Oil and Grease',
        'units': 'mg/L'
    },
    'Organic Nitrogen, Dissolved': {
        'tex': 'Dissolved Organic Nitrogen',
        'units': 'mg/L'
    },
    'Organic Nitrogen, Total': {
        'tex': 'Total Organic Nitrogen',
        'units': 'mg/L'
    },
    'Organic carbon, Dissolved': {
        'tex': 'Dissolved Organic carbon',
        'units': 'mg/L'
    },
    'Organic carbon, Total': {
        'tex': 'Total Organic carbon',
        'units': 'mg/L'
    },
    'ORO': {
        'tex': 'ORO',
        'units': 'ug/L'
    },
    'Oxidation reduction potential (ORP)': {
        'tex': 'Oxidation reduction potential (ORP)',
        'units': 'mV'
    },
    'p-Isopropyltoluene': {
        'tex': 'p-Isopropyltoluene',
        'units': 'ug/L'
    },
    "p,p'-DDE": {
        'tex': "p,p'-DDE",
        'units': 'ug/L'
    },
    'PBP': {
        'tex': 'PBP',
        'units': 'ug/L'
    },
    'Pentachlorophenol': {
        'tex': 'Pentachlorophenol',
        'units': 'ug/L'
    },
    'Pentachlorophenol,  Dissolved': {
        'tex': 'Dissolved Pentachlorophenol',
        'units': 'ug/L'
    },
    'Phenanthrene': {
        'tex': 'Phenanthrene',
        'units': 'ug/L'
    },
    'Phenanthrene,  Dissolved': {
        'tex': 'Dissolved Phenanthrene',
        'units': 'ug/L'
    },
    'Phenanthrene, Suspended': {
        'tex': 'Suspended Phenanthrene',
        'units': 'ug/L'
    },
    'Phenol': {
        'tex': 'Phenol',
        'units': 'ug/L'
    },
    'Phenols': {
        'tex': 'Phenols',
        'units': 'ug/L'
    },
    'Phosphate-phosphorus': {
        'tex': 'Phosphate-phosphorus',
        'units': 'mg/L'
    },
    'Phosphorus as P, Dissolved': {
        'tex': 'Dissolved Phosphorus as P',
        'units': 'mg/L'
    },
    'Phosphorus as P, Suspended': {
        'tex': 'Suspended Phosphorus as P',
        'units': 'mg/L'
    },
    'Phosphorus as P, Total': {
        'tex': 'Total Phosphorus as P',
        'units': 'mg/L'
    },
    'Phosphorus as PO4, Total': {
        'tex': 'Total Phosphorus as PO4',
        'units': 'mg/L'
    },
    'Phosphorus, Particulate Organic': {
        'tex': 'Phosphorus, Particulate Organic',
        'units': 'mg/L'
    },
    'Phosphorus, Soluble Reactive (SRP)': {
        'tex': 'Phosphorus, Soluble Reactive (SRP)',
        'units': 'mg/L'
    },
    'Phosphorus, organic as P, Dissolved': {
        'tex': 'Dissolved Phosphorus, organic as P',
        'units': 'mg/L'
    },
    'Phosphorus, orthophosphate as P': {
        'tex': 'Phosphorus, orthophosphate as P',
        'units': 'mg/L'
    },
    'Phosphorus, orthophosphate as P, Dissolved': {
        'tex': 'Dissolved Phosphorus, orthophosphate as P',
        'units': 'mg/L'
    },
    'Phosphorus, orthophosphate as P, Suspended': {
        'tex': 'Suspended Phosphorus, Orthophosphate as P',
        'units': 'mg/L'
    },
    'Phosphorus, orthophosphate as PO4': {
        'tex': 'Phosphorus, Orthophosphate as PO$_{4}$',
        'units': 'mg/L'
    },
    'Polycyclic aromatic hydrocarbons': {
        'tex': 'Polycyclic Aromatic Hydrocarbons',
        'units': 'ug/L'
    },
    'Potassium, Dissolved': {
        'tex': 'Dissolved Potassium',
        'units': 'mg/L'
    },
    'Potassium, Total': {
        'tex': 'Total Potassium',
        'units': 'mg/L'
    },
    'Prometryn': {
        'tex': 'Prometryn',
        'units': 'ug/L'
    },
    'Pyrene': {
        'tex': 'Pyrene',
        'units': 'ug/L'
    },
    'Pyrene, Suspended': {
        'tex': 'Suspended Pyrene',
        'units': 'ug/L'
    },
    'RELATIVE TOXICITY (I 25% REDUCTION)': {
        'tex': 'RELATIVE TOXICITY (I 25% REDUCTION)',
        'units': '%'
    },
    'SSC-Total Coarse Fraction (>63um)': {
        'tex': 'SSC-Total Coarse Fraction ($>63$ \\si[per-mode=symbol]{\\micro\\meter})',
        'units': 'mg/L'
    },
    'SSC-Total Fine Fraction (<63um)': {
        'tex': 'SSC-Total Fine Fraction (<63 \\si[per-mode=symbol]{\\micro\\meter})',
        'units': 'mg/L'
    },
    'SSC-Total Particulate Solids': {
        'tex': 'SSC-Total Particulate Solids',
        'units': 'mg/L'
    },
    'Sand': {
        'tex': 'Sand',
        'units': 'mg/L'
    },
    'Sec-Butylbenzene': {
        'tex': 'Sec-Butylbenzene',
        'units': 'ug/L'
    },
    'Selenium, Dissolved': {
        'tex': 'Dissolved Selenium',
        'units': 'ug/L'
    },
    'Selenium, Total': {
        'tex': 'Total Selenium',
        'units': 'ug/L'
    },
    'Settleable solids': {
        'tex': 'Settleable Solids',
        'units': 'mg/L'
    },
    'Silt': {
        'tex': 'Silt',
        'units': 'mg/L'
    },
    'Silver, Dissolved': {
        'tex': 'Dissolved Silver',
        'units': 'ug/L'
    },
    'Silver, Total': {
        'tex': 'Total Silver',
        'units': 'ug/L'
    },
    'Simazine': {
        'tex': 'Simazine',
        'units': 'ug/L'
    },
    'Sodium, Dissolved': {
        'tex': 'Dissolved Sodium',
        'units': 'mg/L'
    },
    'Sodium, Total': {
        'tex': 'Total Sodium',
        'units': 'mg/L'
    },
    'Specific conductance': {
        'tex': 'Specific Conductance',
        'units': 'umhos/cm'
    },
    'Styrene': {
        'tex': 'Styrene',
        'units': 'ug/L'
    },
    'Sulfate, Dissolved': {
        'tex': 'Dissolved Sulfate',
        'units': 'mg/L'
    },
    'Sulfate, Total': {
        'tex': 'Total Sulfate',
        'units': 'mg/L'
    },
    'Sulfide, Total': {
        'tex': 'Total Sulfide',
        'units': 'mg/L'
    },
    'Surfactants': {
        'tex': 'Surfactants',
        'units': 'ug/L'
    },
    'Suspended Sediment Concentration (SSC)': {
        'tex': 'Suspended Sediment Concentration',
        'units': 'mg/L'
    },
    'Temperature, water': {
        'tex': 'Temperature, water',
        'units': 'deg C'
    },
    'Tetrachloroethane': {
        'tex': 'Tetrachloroethane',
        'units': 'ug/L'
    },
    'Tetrachloroethylene': {
        'tex': 'Tetrachloroethylene',
        'units': 'ug/L'
    },
    'Thallium, Dissolved': {
        'tex': 'Dissolved Thallium',
        'units': 'ug/L'
    },
    'Thallium, Total': {
        'tex': 'Total Thallium',
        'units': 'ug/L'
    },
    'Toluene': {
        'tex': 'Toluene',
        'units': 'ug/L'
    },
    'Total Coliform': {
        'tex': 'Total Coliform',
        'units': 'MPN/100 mL'
    },
    'Total dissolved solids': {
        'tex': 'Total Dissolved Solids',
        'units': 'mg/L'
    },
    'Total solids': {
        'tex': 'Total Solids',
        'units': 'mg/L'
    },
    'Total suspended solids': {
        'tex': 'Total Suspended Solids',
        'units': 'mg/L'
    },
    'Total volatile solids': {
        'tex': 'Total volatile solids',
        'units': 'mg/L'
    },
    'Toxaphene': {
        'tex': 'Toxaphene',
        'units': 'ug/L'
    },
    'Tribromomethane': {
        'tex': 'Tribromomethane',
        'units': 'ug/L'
    },
    'Trichloroethane': {
        'tex': 'Trichloroethane',
        'units': 'ug/L'
    },
    'Trichloroethylene': {
        'tex': 'Trichloroethylene',
        'units': 'ug/L'
    },
    'Trichlorofuoromethane': {
        'tex': 'Trichlorofuoromethane',
        'units': 'ug/L'
    },
    'Trichlorotrifluoroethane': {
        'tex': 'Trichlorotrifluoroethane',
        'units': 'ug/L'
    },
    'Trihalomethanes': {
        'tex': 'Trihalomethanes',
        'units': 'ug/L'
    },
    'True Color': {
        'tex': 'True Color',
        'units': 'ADMI Value'
    },
    'True color': {
        'tex': 'True Color',
        'units': 'ADMI Value'
    },
    'Turbidity': {
        'tex': 'Turbidity',
        'units': 'NTU'
    },
    'Vanadium, Total': {
        'tex': 'Total Vanadium',
        'units': 'ug/L'
    },
    'Vinyl Acetate': {
        'tex': 'Vinyl Acetate',
        'units': 'ug/L'
    },
    'Vinyl Chloride': {
        'tex': 'Vinyl Chloride',
        'units': 'ug/L'
    },
    'Zinc, Dissolved': {
        'tex': 'Dissolved Zinc',
        'units': 'ug/L'
    },
    'Xylenes, Total': {
        'tex': 'Total Xylenes',
        'units': 'ug/L'
    },
    'Zinc, Suspended': {
        'tex': 'Suspended Zinc',
        'units': 'ug/L'
    },
    'Zinc, Total': {
        'tex': 'Total Zinc',
        'units': 'ug/L'
    },
    'alpha-chlordane': {
        'tex': 'alpha-chlordane',
        'units': 'ug/L'
    },
    'cis-1,2-Dichloroethylene': {
        'tex': 'cis-1,2-Dichloroethylene',
        'units': 'ug/L'
    },
    'cis-1,3-Dichloropropene': {
        'tex': 'cis-1,3-Dichloropropene',
        'units': 'ug/L'
    },
    'di-n-Butyl phthalate': {
        'tex': 'di-n-Butyl phthalate',
        'units': 'ug/L'
    },
    'gamma-chlordane': {
        'tex': 'gamma-chlordane',
        'units': 'ug/L'
    },
    'm-Dichlorobenzene': {
        'tex': 'm-Dichlorobenzene',
        'units': 'ug/L'
    },
    'm-Nitroaniline': {
        'tex': 'm-Nitroaniline',
        'units': 'ug/L'
    },
    'm-Xylene': {
        'tex': 'm-Xylene',
        'units': 'ug/L'
    },
    'n-Butylbenzene': {
        'tex': 'n-Butylbenzene',
        'units': 'ug/L'
    },
    'n-Propylbenzene': {
        'tex': 'n-Propylbenzene',
        'units': 'ug/L'
    },
    'o-Chlorotoluene': {
        'tex': 'o-Chlorotoluene',
        'units': 'ug/L'
    },
    'o-Dichlorobenzene': {
        'tex': 'o-Dichlorobenzene',
        'units': 'ug/L'
    },
    'o-Xylene': {
        'tex': 'o-Xylene',
        'units': 'ug/L'
    },
    'p-Bromophenyl phenyl ether': {
        'tex': 'p-Bromophenyl phenyl ether',
        'units': 'ug/L'
    },
    'p-Chlorophenyl phenyl ether': {
        'tex': 'p-Chlorophenyl phenyl ether',
        'units': 'ug/L'
    },
    'p-Chlorotoluene': {
        'tex': 'p-Chlorotoluene',
        'units': 'ug/L'
    },
    'p-Cymene': {
        'tex': 'p-Cymene',
        'units': 'ug/L'
    },
    'p-Dichlorobenzene': {
        'tex': 'p-Dichlorobenzene',
        'units': 'ug/L'
    },
    'p-Nitrophenol': {
        'tex': 'p-Nitrophenol',
        'units': 'ug/L'
    },
    'p-Xylene': {
        'tex': 'p-Xylene',
        'units': 'ug/L'
    },
    'pH': {
        'tex': 'pH',
        'units': 'SU'
    },
    'protons': {
        'tex': 'Protons (Hydrogen Ions)',
        'units': 'mg/L'
    },
    'tert-Butylbenzene': {
        'tex': 'tert-Butylbenzene',
        'units': 'ug/L'
    },
    'total petroleum hydrocarbons, motor oil range': {
        'tex': 'total petroleum hydrocarbons, motor oil range',
        'units': 'ug/L'
    },
    'trans-1,2-dichloroethylene': {
        'tex': 'trans-1,2-dichloroethylene',
        'units': 'ug/L'
    },
    'trans-1,3-dichloropropene': {
        'tex': 'trans-1,3-dichloropropene',
        'units': 'ug/L'
    },
    'trans-1,4-Dichloro-2-butene': {
        'tex': 'trans-1,4-Dichloro-2-butene',
        'units': 'ug/L'
    },
    'Dibenzo[b,k]fluoranthene': {
        'tex': 'Dibenzo[b,k]fluoranthene',
        'units': 'ug/L'
    },
    'Dichlobenil': {
        'tex': 'Dichlobenil',
        'units': 'ug/L'
    },
    'Prometon': {
        'tex': 'Prometon',
        'units': 'ug/L'
    },
    'Total volatile solids, non-filterable': {
        'tex': 'Total volatile solids, non-filterable',
        'units': 'ug/L'
    },
    'Benzo(b/j)fluoranthene': {
        'tex': 'Benzo(b/j)fluoranthene',
        'units': 'ug/L'
    },
    'Bismuth': {
        'tex': 'Bismuth',
        'units': 'ug/L'
    },
    'Boron': {
        'tex': 'Boron',
        'units': 'ug/L'
    },
    'Lithium, Total': {
        'tex': 'Lithium, Total',
        'units': 'ug/L'
    },
    'Silicon': {
        'tex': 'Silicon',
        'units': 'ug/L'
    },
    'Strontium': {
        'tex': 'Strontium',
        'units': 'ug/L'
    },
    'Tellurium': {
        'tex': 'Tellurium',
        'units': 'ug/L'
    },
    'Tin, Total': {
        'tex': 'Tin, Total',
        'units': 'ug/L'
    },
    'Titanium, Total': {
        'tex': 'Titanium, Total',
        'units': 'ug/L'
    },
    'Tungsten': {
        'tex': 'Tungsten',
        'units': 'ug/L'
    },
    'Uranium': {
        'tex': 'Uranium',
        'units': 'ug/L'
    },
    'Zirconium': {
        'tex': 'Zirconium',
        'units': 'ug/L'
    },
    'Cesium': {
        'tex': 'Cesium',
        'units': 'ug/L'
    },
    'Rubidium': {
        'tex': 'Rubidium',
        'units': 'ug/L'
    },
    '1,2-Dibromo-3-chloropropane': {
        'tex': '1,2-Dibromo-3-chloropropane',
        'units': 'ug/L'
    },
    'sec-Butylbenzene': {
        'tex': 'sec-Butylbenzene',
        'units': 'ug/L'
    },
    'trans-1,2-Dichloroethylenetrans-1,2-dichloroethylene': {
        'tex': 'trans-1,2-Dichloroethylenetrans-1,2-dichloroethylene',
        'units': 'ug/L'
    },
    '2,4,5-T': {
        'tex': '2,4,5-T',
        'units': 'ug/L'
    },
    '2,4-DB': {
        'tex': '2,4-DB',
        'units': 'ug/L'
    },
    'Dalapon': {
        'tex': 'Dalapon',
        'units': 'ug/L'
    },
    'Dicamba': {
        'tex': 'Dicamba',
        'units': 'ug/L'
    },
    'Dichlorprop': {
        'tex': 'Dichlorprop',
        'units': 'ug/L'
    },
    'MCPA': {
        'tex': 'MCPA',
        'units': 'ug/L'
    },
    'Mecoprop': {
        'tex': 'Mecoprop',
        'units': 'ug/L'
    },
    'Sulfur': {
        'tex': 'Sulfur',
        'units': 'ug/L'
    },
    'm,p-Xylenes': {
        'tex': 'm,p-Xylenes',
        'units': 'ug/L'
    },
    'Silica': {
        'tex': 'Silica',
        'units': 'ug/L'
    },
    'Nitrogen, Dissolved': {
        'tex': 'Nitrogen, Dissolved',
        'units': 'ug/L'
    },
    '2-Chloroethyl vinyl ether': {
        'tex': '2-Chloroethyl vinyl ether',
        'units': 'ug/L'
    },
    'Ethyl methacrylate': {
        'tex': 'Ethyl methacrylate',
        'units': 'ug/L'
    },
    'meta & para Xylene mix': {
        'tex': 'meta & para Xylene mix',
        'units': 'ug/L'
    },
    'Temperature, air': {
        'tex': 'Temperature, air',
        'units': 'ug/L'
    },
    'Gasoline range organics': {
        'tex': 'Gasoline range organics',
        'units': 'ug/L'
    },
    'Particle Size, Percent > 50 microns': {
        'tex': 'Particle Size, Percent > 50 microns',
        'units': 'ug/L'
    },
    'Chlorophyll a, uncorrected for pheophytin': {
        'tex': 'Chlorophyll a, uncorrected for pheophytin',
        'units': 'ug/L'
    },
    '1-Methylphenanthrene': {
        'tex': '1-Methylphenanthrene',
        'units': 'ug/L'
    },
    '2,6-Dimethylnaphthalene': {
        'tex': '2,6-Dimethylnaphthalene',
        'units': 'ug/L'
    },
    'Benzo[e]pyrene': {
        'tex': 'Benzo[e]pyrene',
        'units': 'ug/L'
    },
    'Bifenthrin by NCI': {
        'tex': 'Bifenthrin by NCI',
        'units': 'ug/L'
    },
    'Cobalt, Dissolved': {
        'tex': 'Cobalt, Dissolved',
        'units': 'ug/L'
    },
    'Cyfluthrin by NCI': {
        'tex': 'Cyfluthrin by NCI',
        'units': 'ug/L'
    },
    'Cypermethrin': {
        'tex': 'Cypermethrin',
        'units': 'ug/L'
    },
    'Dibenzothiophene': {
        'tex': 'Dibenzothiophene',
        'units': 'ug/L'
    },
    'Esfenvalerate': {
        'tex': 'Esfenvalerate',
        'units': 'ug/L'
    },
    'Fenvalerate': {
        'tex': 'Fenvalerate',
        'units': 'ug/L'
    },
    'L-Cyhalothrin by NCI': {
        'tex': 'L-Cyhalothrin by NCI',
        'units': 'ug/L'
    },
    'Molybdenum, Dissolved': {
        'tex': 'Molybdenum, Dissolved',
        'units': 'ug/L'
    },
    'Permethrin': {
        'tex': 'Permethrin',
        'units': 'ug/L'
    },
    'Tin, Dissolved': {
        'tex': 'Tin, Dissolved',
        'units': 'ug/L'
    },
    'Titanium, Dissolved': {
        'tex': 'Titanium, Dissolved',
        'units': 'ug/L'
    },
    'Vanadium, Dissolved': {
        'tex': 'Vanadium, Dissolved',
        'units': 'ug/L'
    },
    'Cypermethrin by NCI': {
        'tex': 'Cypermethrin by NCI',
        'units': 'ug/L'
    },
    'Bicarbonate': {
        'tex': 'Bicarbonate',
        'units': 'ug/L'
    }
}


