import summary
import os


def test_run():
    report = Report()
    report.makeInputFiles(report.std_tables)


class Report():
    def __init__(self):
        self.std_tables = ['bacteria', 'metals']
        self.std_docs = ['Bacteria', 'Metals']

        self.cbay_tables = ['tss_cbay', 'nutrients_cbay', 'tss_noncbay', 'nutrients_noncbay']
        self.cbay_docs = ['Total Suspended Solids in Chesapeake Bay',
                          'Nutrients in Chesapeake Bay',
                          'Total Suspended Solids outside of Chesapeake Bay',
                          'Nutrients outside of Chesapeake Bay']

        self.md_tables = ['metals_md', 'tss_md', 'nutrients_md']
        self.md_docs = ['Metals (Manufactured devices only)',
                        'TSS (Manufactured devices only)',
                        'Nutrients (Manufactured devices only)']

        self.all_tables = ['bacteria', 'metals', 'tss', 'nutrients',
                           'tss_cbay', 'nutrients_cbay',
                           'tss_noncbay', 'nutrients_noncbay',
                           'metals_md', 'tss_md', 'nutrients_md']

        self.all_docs = ['Bacteria', 'Metals', 'Total Suspended Solids', 'Nutrients',
                         'Total Suspended Solids in Chesapeake Bay',
                         'Nutrients in Chesapeake Bay',
                         'Total Suspended Solids outside of Chesapeake Bay',
                         'Nutrients outside of Chesapeake Bay',
                         'Metals (Manufactured devices only)',
                         'TSS (Manufactured devices only)',
                         'Nutrients (Manufactured devices only)']

        self.sbpat_tables = ['bacteria_sbpat', 'tss', 'nutrients', 'metals']

    def makeSBPAT_tables(self):
        for t in self.sbpat_tables:
            print('\n\nsummarizing %s for SBPAT' % t)
            summary.sbpat_stats(t)

    def makeBoxplots(self, tables):
        for t in tables:
            print('\n\nboxplot summaries for %s' % t)
            summary.paramBoxplots(t)

    def makeInputFiles(self, tables):
        for t in tables:
            print('\n\nmaking input files for %s' % t)
            summary.latexInputFile(t, regenFigs=True)

    def makeReports(self, tables, docs):
        versions = ['draft', 'final']
        for t, d in zip(tables, docs):
            for v in versions:
                print('\n\nsummarizing %s' % t)
                summary.latexReport(t, d, template=v)

    def compileReport(self, docs, version='draft'):
        os.chdir('bmp/tex')
        for d in docs:
            filename = '%s_%s.tex' % (version, d.replace(' ', ''))
            print('Compiling report %s' % filename)
            os.system('pdflatex -quiet %s' % filename)
            print('Updating references in %s' % filename)
            os.system('pdflatex -quiet %s' % filename)

        os.chdir('../..')

    def makeTables(self, tables):
        for t in tables:
            print('\n\nsummary table for %s' % t)
            summary.paramTables(t)

    def dumpData(self, tables):
        for t in tables:
            print('\n\ndumping %s table' % t)
            summary.dataDump(t)

    def fullSuite(self, tables, docs, version):
        self.dumpData(tables)
        self.makeTables(tables)
        self.makeBoxplots(tables)
        self.makeReports(tables, docs)
        self.makeInputFiles(tables)
        self.compileReport(docs, version=version)
