"""Behavioral tests, using source text only: no SDKs required."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from invoice_splitter_claim_audit.audit import audit, claims_in, evidence_in
from invoice_splitter_claim_audit.phrases import INVOICESPLITTER, NOINVOICESPLITTER, GENERIC_NAMES
from invoice_splitter_claim_audit.__main__ import main


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def run_cli(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = main(args)
            except SystemExit as error:
                code = error.code
        return code, output.getvalue()

    def test_vocabulary_sizes(self):
        for vocabulary, count in ((INVOICESPLITTER, 50), (NOINVOICESPLITTER, 24), (GENERIC_NAMES, 24)):
            self.assertEqual(len(vocabulary), count)
            self.assertEqual(len(set(vocabulary)), count)

    def test_no_source_asymmetry(self):
        self.put('README.md', 'split invoices')
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'HIGH')
        self.put('README.md', 'does not split invoices')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')

    def test_denial_conflict_and_family_deduplication(self):
        self.put('README.md', 'no invoice splitting\n\nno invoice splitter')
        self.put('app.py', 'service.split_invoices()')
        result = audit(self.root)
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['rule'], 'documented-no-invoice-splitter-claim-false')

    def test_positive_family_deduplication(self):
        self.put('README.md', 'split invoices\n\ninvoice splitter')
        self.assertEqual(len(audit(self.root)['findings']), 1)

    def test_same_module_required(self):
        self.put('README.md', 'split invoices')
        self.put('a.py', 'from mindee import Client\nc = Client()')
        self.put('b.py', 'import mindee\nc.parse(InvoiceSplitterV1, x)')
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'HIGH')

    def test_document_selection(self):
        self.put('nested/README.md', 'split invoices')
        self.put('other.md', 'split invoices')
        self.assertEqual(audit(self.root)['claims'], [])
        self.put('nested/docs/note.md', 'split invoices')
        self.assertEqual(len(audit(self.root)['claims']), 1)

    def test_ignore_component_prefix(self):
        self.put('docs/a.md', 'split invoices')
        self.put('docs-extra/a.py', 's.split_invoices()')
        self.assertEqual(audit(self.root, ['docs'])['claims'], [])
        self.assertEqual(len(audit(self.root, ['docs'])['evidence']), 1)

    def test_symlinks(self):
        target = self.put('fixtures/real.py', 's.split_invoices()')
        (self.root / 'linked.py').symlink_to(target)
        (self.root / 'linked-dir').symlink_to(target.parent, target_is_directory=True)
        self.assertEqual(audit(self.root)['evidence'], [])

    def test_missing_root(self):
        self.assertEqual(self.run_cli(['audit', str(self.root / 'missing')])[0], 1)

    def test_cli_usage(self):
        for args in ([], ['wrong'], ['audit', '--unknown'], ['audit', '--fail-on', 'HIGH'], ['audit', '--ignore', 'a', 'b', 'c']):
            self.assertEqual(self.run_cli(args)[0], 1)

    def test_cli_json_high_pass_and_verbose(self):
        self.put('README.md', 'split invoices')
        code, output = self.run_cli(['audit', str(self.root), '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)['findings'][0]['rule'], 'documented-invoice-splitter-claim-false')
        self.put('app.py', 's.split_invoices()')
        code, output = self.run_cli(['audit', str(self.root), '--verbose'])
        self.assertEqual(code, 0)
        self.assertIn('app.py', output)

    def test_medium_threshold(self):
        self.put('README.md', 'split invoices')
        self.put('tests/test_app.py', 's.split_invoices()')
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'MEDIUM')
        self.assertEqual(self.run_cli(['audit', str(self.root)])[0], 0)
        self.assertEqual(self.run_cli(['audit', str(self.root), '--fail-on', 'medium'])[0], 2)

    def test_version(self):
        self.assertEqual(self.run_cli(['--version']), (0, '0.1.0\n'))

    def test_default_root(self):
        import os
        before = os.getcwd()
        try:
            os.chdir(self.root)
            self.assertEqual(self.run_cli(['audit'])[0], 0)
        finally:
            os.chdir(before)

    def test_fences(self):
        for fence in ('```', '~~~', '````', '~~~~'):
            for indent in ('', ' ', '  ', '   '):
                text = indent + fence + 'text\nsplit invoices\n' + indent + fence
                self.assertEqual(claims_in(text, 'README.md'), [])
        self.assertEqual(len(claims_in('`split invoices`', 'README.md')), 1)

    def test_fence_length_and_type(self):
        self.assertEqual(claims_in('````\nsplit invoices\n```\n~~~\nsplit invoices', 'x'), [])

    def test_normalization_paragraphs_boundaries(self):
        self.assertEqual(claims_in("DOESN'T SPLIT-INVOICES", 'x')[0]['family'], 'NOINVOICESPLITTER')
        self.assertEqual(claims_in('split\n invoices', 'x')[0]['phrase'], 'split invoices')
        self.assertEqual(claims_in('split\n\ninvoices', 'x'), [])
        self.assertEqual(claims_in('resplit invoicesx', 'x'), [])
        self.assertEqual(claims_in('split invoice documents', 'x')[0]['phrase'], 'split invoice documents')

    def test_curly_contraction(self):
        self.assertEqual(claims_in("doesn’t split invoices", 'x')[0]['family'], 'NOINVOICESPLITTER')

    def test_dead_code_counts(self):
        self.assertTrue(evidence_in('if False:\n    s.split_invoices()'))

    def test_readme_self_audit(self):
        readme = Path(__file__).resolve().parents[1] / 'README.md'
        self.assertEqual(claims_in(readme.read_text(), 'README.md'), [])
        text = readme.read_text()
        for phrase in INVOICESPLITTER + NOINVOICESPLITTER:
            self.assertIn(phrase, text)

    def test_no_source_execution(self):
        self.put('README.md', 'split invoices')
        self.put('app.py', 'raise RuntimeError("must never execute")\ns.split_invoices()')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')


def add_case(name, fn):
    setattr(AuditTests, 'test_' + name, fn)


def positive_case(phrase):
    def test(self):
        found = claims_in(phrase, 'README.md')
        self.assertEqual([(c['family'], c['phrase']) for c in found], [('INVOICESPLITTER', phrase)])
    return test


def negative_case(phrase):
    def test(self):
        found = claims_in(phrase, 'README.md')
        self.assertEqual([(c['family'], c['phrase']) for c in found], [('NOINVOICESPLITTER', phrase)])
    return test


for i, phrase in enumerate(INVOICESPLITTER):
    add_case('positive_phrase_%02d' % i, positive_case(phrase))
for i, phrase in enumerate(NOINVOICESPLITTER):
    add_case('negative_phrase_%02d' % i, negative_case(phrase))


def evidence_case(source, expected):
    def test(self):
        self.assertEqual(bool(evidence_in(source)), expected, source)
    return test


for route in GENERIC_NAMES:
    for label, source, expected in (
        ('attribute', 'service.' + route + '()', True),
        ('import', 'from sdk import ' + route + '\n' + route + '()', True),
        ('alias', 'from sdk import ' + route + ' as go\ngo()', True),
        ('bare', route + '()', False),
        ('shadow', 'def ' + route + '(): pass\nservice.' + route + '()', False),
        ('assignment', 'from sdk import ' + route + ' as go\ngo = other\ngo()', False),
        ('annotated', 'from sdk import ' + route + ' as go\ngo: object = other\ngo()', False),
        ('with', 'from sdk import ' + route + ' as go\nwith context() as go:\n go()', False),
        ('async_with', 'from sdk import ' + route + ' as go\nasync def f():\n async with context() as go:\n  go()', False),
    ):
        add_case('generic_' + route + '_' + label, evidence_case(source, expected))

mindee_cases = [
 ('import mindee\nc=mindee.Client()\nc.parse(InvoiceSplitterV1, x)', True),
 ('from mindee import Client as C\nc=C()\nc.parse(product.InvoiceSplitterV1, x)', True),
 ('from mindee import Client\nClient()\na.parse(product_class=mindee.product.invoice_splitter.InvoiceSplitterV1)', True),
 ('from mindee import Client\nClient()\na.parse(mindee.product.InvoiceSplitterV1)', True),
 ('from mindee.v1 import product\nfrom mindee import Client\nClient()\na.parse(product.InvoiceSplitterV1)', True),
 ('import mindee\nc.parse(InvoiceSplitterV1)', False),
 ('import mindee\nmindee.Client()', False),
 ('Client()\nx.parse(InvoiceSplitterV1)', False),
 ('from mindee import Client\nClient=other\nClient()\nx.parse(InvoiceSplitterV1)', False),
 ('from mindee import Client\nwith manager() as Client:\n Client()\nx.parse(InvoiceSplitterV1)', False),
 ('import mindee\nmindee=other\nmindee.Client()\nx.parse(InvoiceSplitterV1)', False),
 ('from mindee import Client\ndef Client(): pass\nClient()\nx.parse(InvoiceSplitterV1)', False),
 ('import mindee\nmindee.Client()\ndef parse(): pass\nx.parse(InvoiceSplitterV1)', False),
 ('import mindee\nmindee.Client()\nInvoiceSplitterV1=other\nx.parse(InvoiceSplitterV1)', False),
 ('import mindee\nmindee.Client()\nx.parse("InvoiceSplitterV1")', False),
]
for i, (source, expected) in enumerate(mindee_cases):
    add_case('mindee_%02d' % i, evidence_case(source, expected))

OTHER_PRODUCTS = '''InvoiceV4 ReceiptV5 FinancialDocumentV1 PassportV1 BankCheckV1 BankAccountDetailsV1 BankAccountDetailsV2 PayslipV2 PayslipV3 NutritionFactsLabelV1 HealthcareCardV1 BusinessCardV1 CustomV1 GeneratedV1 BillOfLadingV1 ResumeV1 DeliveryNoteV1 DriverLicenseV1 IdCardV1 InternationalIdV2 CarteGriseV1 EnergyBillV1 MaterialCertificateV1 BarcodeReaderV1 CropperV1 MultiReceiptsDetectorV1 UsMailV2 UsMailV3 InvoiceSplitterV2 TypeInvoiceSplitterV1'''.split()
for product in OTHER_PRODUCTS:
    add_case('other_product_' + product, evidence_case('import mindee\nc=mindee.Client()\nc.parse(product.' + product + ', x)', False))

for route in ('split_and_process_pdf', 'split_and_process_pdf_url'):
    for i, prefix in enumerate(('import veryfi', 'import veryfi as v', 'from veryfi import Client', 'from veryfi._documents import PDFSplit')):
        add_case('veryfi_' + route + '_%d' % i, evidence_case(prefix + '\nc.' + route + '()', True))
    add_case('veryfi_ungated_' + route, evidence_case('c.' + route + '()', False))
    add_case('veryfi_shadow_' + route, evidence_case('import veryfi\nclass C:\n def ' + route + '(self): pass\nc.' + route + '()', False))

NOT_CALLS = '''process_any_document process_any_document_url process_document process_document_url process_w2_document process_w9_document process_w8_document split_and_process_w2 split_and_process_w2_url process_check process_check_url process_check_with_remittance process_check_with_remittance_url process_bank_statement_document process_bank_statement_document_url process_bussines_card_document process_bussines_card_document_url classify_document get_business_cards get_business_card delete_business_card get_pdf get_documents_from_pdf process_invoice_splitter process_invoice_splitter_url begin_analyze_document batch_process_documents analyze_document analyze_expense analyze_id start_document_analysis get_expense_analysis split_pdf split_document pdf_splitter document_splitter split_documents extract_text image_to_string read_csv read_excel read_pdf convert_into extract_table extract_tables find_table find_tables extract'''.split()
for route in NOT_CALLS:
    add_case('excluded_call_' + route, evidence_case('import veryfi, mindee, boto3\nx.' + route + '("prebuilt-invoice")', False))

OTHER_SOURCES = [
 'import mindee, veryfi, boto3\nfrom azure.ai import documentintelligence\nfrom google.cloud import documentai',
 '"service.split_invoices()"\n# service.split_invoices()',
 's.split_invoices', 's.split_invoices(',
 'import subprocess\nsubprocess.run(["mindee", "split_invoices"])',
 'import requests\nrequests.post("https://api.edenai.run/v3/universal-ai", json={"model":"invoice_splitter"})',
 'import requests\nrequests.post("https://api.veryfi.com/api/v8/partner/documents")',
 'import requests\nrequests.post("https://app.nanonets.com/api/v2/OCR/Model/opaque/LabelFile/")',
 'import requests\nrequests.post("https://app.docsumo.com/api/v1/eevee/apikey/upload/")',
 'from llama_parse import LlamaParse\nLlamaParse().load_data("batch.pdf")',
 'from mindee import ClientV2\nClientV2().enqueue_and_get_inference(model_id="opaque")',
 'import re\nre.findall("Invoice", text)\nwriter.add_page(page)',
 'from pypdf import PdfReader, PdfWriter\nr=PdfReader("x")\nw=PdfWriter()\nw.add_page(r.pages[0])',
 'import pdfplumber\nwith pdfplumber.open("x") as pdf:\n for p in pdf.pages: p.extract_text()',
 'import fitz\nd=fitz.open("x")\nx=d.load_page(0)\nx.get_text()',
 'writer.append(reader, pages=(0, 3))\nbookmarks=reader.outline',
 'from sdk import split_invoices as go\ndef go(): pass\ngo()',
 'import sdk as go\nwith ctx() as go:\n go.split_invoices()',
]
for i, source in enumerate(OTHER_SOURCES):
    add_case('excluded_source_%02d' % i, evidence_case(source, False))

for i, name in enumerate(('fixtures/app.py', 'docs/app.py', 'examples/app.py', 'a/fixtures/app.py')):
    def test(self, name=name):
        self.put(name, 's.split_invoices()')
        self.assertEqual(audit(self.root)['evidence'], [])
    add_case('excluded_path_%d' % i, test)
for i, name in enumerate(('tests/app.py', 'test_app.py', 'app_test.py', 'nested/tests/a.py')):
    def test(self, name=name):
        self.put('README.md', 'split invoices')
        self.put(name, 's.split_invoices()')
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'MEDIUM')
    add_case('test_path_%d' % i, test)

if __name__ == '__main__':
    unittest.main()
