# Documentation claim auditor

An offline static auditor comparing documentation promises with source call patterns.
It reads root README.md and Markdown with a docs path component, excludes fenced
code, and parses source without executing it. Audits make no network calls,
write no files, and collect no telemetry.

## Install and use

```sh
python3 -m pip install .
invoice-splitter-claim-audit audit . --json
python3 -m invoice_splitter_claim_audit audit . --verbose
invoice-splitter-claim-audit audit . --ignore vendor --ignore build --fail-on medium
invoice-splitter-claim-audit --version
python3 -m unittest discover
python3 -m build
```

The repository defaults to the current directory. Repeatable ignore prefixes match
whole relative path components. Exit codes are 0 for PASS or findings below the
threshold, 2 for findings at or above it, and 1 for usage or I/O errors.
The threshold defaults to high; medium also fails on evidence found only in tests.
JSON reports verdict, findings, claims, and evidence; verbose text adds locations.
At most one finding is emitted per family. A positive promise without production
evidence produces HIGH, or MEDIUM if only tests contain evidence. A denial
contradicted by production evidence produces HIGH. With no source, a positive
promise fails and a denial passes.

## Rules and exact vocabulary

```text
documented-invoice-splitter-claim-false
documented-no-invoice-splitter-claim-false
invoice splitting
split invoice
splits invoice
splitting invoice
invoice splitter
invoice split
invoices splitting
split invoices
splits invoices
splitting invoices
invoices splitter
invoices split
invoice document splitting
split invoice document
splits invoice document
splitting invoice document
invoice document splitter
invoice document split
invoice documents splitting
split invoice documents
splits invoice documents
splitting invoice documents
invoice documents splitter
invoice documents split
multi invoice splitting
split multi invoice
splits multi invoice
splitting multi invoice
multi invoice splitter
multi invoice split
multi invoices splitting
split multi invoices
splits multi invoices
splitting multi invoices
multi invoices splitter
multi invoices split
invoice page splitting
split invoice pages
splits invoice pages
splitting invoice pages
invoice page splitter
invoice page split
invoice batch splitting
split invoice batch
splits invoice batch
splitting invoice batch
invoice batch splitter
invoice batch split
batched invoice splitting
split batched invoices
no invoice splitting
does not split invoices
does not support invoice splitting
without invoice splitting
no invoice splitter
does not split invoice
no invoice split
invoice splitting not supported
no invoices splitting
does not split invoice documents
does not support invoices splitting
without invoices splitting
no invoices splitter
does not split invoice document
no invoice document splitter
invoice splitter not supported
no multi invoice splitting
does not split multi invoices
does not support multi invoice splitting
without multi invoice splitting
no multi invoice splitter
does not split multi invoice
no invoice page splitting
invoice page splitting not supported
```

## Source and matching policy

Paragraphs are normalized to lowercase, contractions expanded, hyphens replaced
with spaces, and whitespace collapsed. Exact word-boundary matches use longest
first and alphabetical ties. Denial spans are removed before positive matching.
Inline code counts. Backtick and tilde fences with up to three leading spaces do
not count. Symlinks are excluded. Source in fixtures, docs, and examples is
excluded; tests are tracked separately. Invalid syntax supplies no evidence.
All parts of a route must occur in one module. Imports resolve aliases; local
functions, methods, classes, assignments, annotated assignments and context-manager
bindings shadow imported names. Source is never executed.

The following reference notes describe the accepted routes and deliberate limits.
They are examples and vocabulary, rather than promises about this auditor.

```text
Generic call names:
split_invoices
split_invoice
split_invoice_document
split_invoice_documents
invoice_splitter
invoice_splitting
split_multi_invoice
split_multi_invoices
invoice_batch_splitter
invoice_batch_splitting
split_invoice_batch
split_batched_invoices
extract_invoice_page_groups
invoice_page_group_extraction
split_invoices_from_pdf
split_invoice_pdf
invoice_pdf_splitter
invoice_pdf_splitting
separate_invoices
separate_invoice
invoice_separator
invoice_separation
group_invoice_pages
invoice_page_grouping

Mindee reference:


mindee Client construction + parse call passing InvoiceSplitterV1
(Name exactly InvoiceSplitterV1, or Attribute with attr exactly
InvoiceSplitterV1 such as product.InvoiceSplitterV1 /
mindee.product.InvoiceSplitterV1 /
mindee.product.invoice_splitter.InvoiceSplitterV1) as any
argument; import gate mindee. InvoiceSplitterV1 is NOT a 4.x-only
fingerprint (4.22.0 wheel inspected 2026-11-15:
mindee/product/invoice_splitter/invoice_splitter_v1.py
defines class InvoiceSplitterV1(Inference), endpoint_name
"invoice_splitter", endpoint_version "1", exported at top-level
mindee.product and via mindee.product.invoice_splitter; its
document is "Invoice Splitter API version 1.4" with field
invoice_page_groups, a list of InvoiceSplitterV1InvoicePageGroup,
each group carrying page_indexes (the list of page indexes that
belong to the same invoice) and page_n (the document page on
which the information was found); there is NO InvoiceSplitterV2
and no TypeInvoiceSplitterV1 form — the 4.22.0 wheel has no
mindee/documents module; the 5.4.0 wheel inspected 2026-11-15 still
contains it at mindee/v1/product/invoice_splitter/ — the product
survived in 5.x). The tool
detects the call in source, not the installed SDK version. A parse
call passing any other product (InvoiceV4, ReceiptV5,
FinancialDocumentV1, PassportV1, BankCheckV1, BankAccountDetailsV1,
BankAccountDetailsV2, PayslipV2, PayslipV3, NutritionFactsLabelV1, HealthcareCardV1,
BusinessCardV1, CustomV1, GeneratedV1, BillOfLadingV1, ResumeV1,
DeliveryNoteV1, DriverLicenseV1, IdCardV1, InternationalIdV2,
CarteGriseV1, EnergyBillV1, MaterialCertificateV1, BarcodeReaderV1, CropperV1,
MultiReceiptsDetectorV1, UsMailV2, UsMailV3, or any other)
is NOT evidence.

## veryfi names (implementation MUST match exactly)

veryfi route: a Call whose func is an Attribute with attr exactly
split_and_process_pdf or split_and_process_pdf_url (any base), in a
module that imports veryfi in any form, unless locally shadowed.
The 5.1.0 wheel, inspected 2026-11-15, defines these in
veryfi/_documents/pdf_split.py (`class PDFSplit`), reached as
client.split_and_process_pdf(...) via veryfi/documents.py
(`class Documents(Tags, LineItems, PDFSplit)`); both POST to
"/documents-set/", Veryfi's Split and Process a PDF endpoint, which
splits a multi-document PDF into its individual documents and
processes each one. The route is generic across receipts and
invoices — recorded honestly in the Why section — but the operation
is splitting a batched PDF into its constituent documents, which
IS the operation this family checks. NOT evidence: veryfi
split_and_process_w2 / split_and_process_w2_url (W-2 splitting,
the tax-form family's domain); veryfi get_pdf /
get_documents_from_pdf (retrieval, not splitting); a call to the
non-existent process_invoice_splitter /
process_invoice_splitter_url (no such method exists in the veryfi
SDK); a raw HTTP call to
"https://api.veryfi.com/api/v8/partner/documents" (the generic
Veryfi documents endpoint, shared by receipts, invoices, and
other documents — not invoice-splitter-specific); veryfi
process_document / process_any_document and every other veryfi
method listed in the Behaviour section.

## azure names (implementation MUST match exactly)

NO azure route: Azure Document Intelligence has no invoice splitter
model. The Microsoft Learn v4.0 (GA) prebuilt-model
language-support page and the v4.0 model catalog,
searched 2026-11-15 (catalog listing carried from R211), list
prebuilt-read, prebuilt-layout, prebuilt-contract,
prebuilt-healthInsuranceCard.us, prebuilt-idDocument,
prebuilt-invoice, prebuilt-receipt,
prebuilt-marriageCertificate.us, prebuilt-creditCard,
prebuilt-check.us, prebuilt-payStub.us, prebuilt-bankStatement,
prebuilt-mortgage.us.1003/.1004/.1005/.1008/.closingDisclosure,
prebuilt-tax.us.*, prebuilt-vaccinationCard,
prebuilt-businessCard (deprecated in v4.0), and
prebuilt-document — and no model named "invoice splitter". A
begin_analyze_document call with ANY model id is NOT
evidence.

## google document ai names (implementation MUST match exactly)

NO Google Document AI route: the Document AI processors list /
pretrained overview page, searched 2026-11-15 (carried from
R211), lists pretrained parsers for invoice, expense, bank
statement, pay slip, W2, US driver licence, passport, utility
bill, and identity proofing — an invoice parser extracts fields
from one invoice, it does not split a batched PDF into invoices,
and there is no invoice splitter processor, so a process_document
call with ANY processor is NOT evidence.

## eden ai / llamaparse / nanonets / docsumo / other vendor names (implementation MUST match exactly)

NO Eden AI route, by deliberate decision: the standing sibling
rule is that a universal-ai call with ANY model id is NOT
evidence, because the model id is a plain string inside an
arbitrary request payload, not a typed SDK call — the same call
shape serves every Eden AI feature, so there is no fixed static
fingerprint for the call itself. NO LlamaParse route: LlamaParse
is a generative parsing API with no fixed static fingerprint
naming invoice splitting. NO Nanonets route: Nanonets document
calls carry an opaque model_id in the URL path (no fixed
fingerprint — the model id is user-configured, not an invoice
splitter product). NO Docsumo route: Docsumo uploads go to a
generic endpoint with the document type configured in the
dashboard, not in the call. NO ABBYY Vantage / Rossum / Klippa /
Parseur / Extend route: opaque skill / queue / template /
workflow IDs. NO Textract route: Textract has no invoice
splitting operation (AnalyzeID covers driver's licenses and
passports). NO generic split-pdf / split-document route: a call
named split_pdf / split_document / pdf_splitter /
document_splitter with no "invoice" qualifier could name
splitting any document, not invoices. NO PDF page-count split
route: pypdf / PyPDF2 page slicing, pdfplumber page iteration,
or fitz page extraction cut a PDF every N pages or on bookmarks
— they do not detect invoice boundaries. NO mindee v2 extraction
API route: configurable model id, no fixed fingerprint. NO
mindee MultiReceiptsDetectorV1 route: detecting receipts in one
image is not splitting invoices. NO mindee CropperV1 route:
cropping a document region is not splitting invoices.


Matching hazards:
- The bare phrases "invoice splitter" / "invoice splitting" /
  "split invoices" are deliberately INVOICESPLITTER phrases: in
  document-tool docs they almost always name splitting a batched
  invoice PDF into individual invoices. But "invoice splitter"
  can also name a tool that merely separates invoice files a user
  already split by hand (a file sorter, a folder organiser) without
  detecting invoice boundaries in a batched document: a doc that
  means sorting files, not grouping pages by invoice, is a false
  positive; the tool flags the claim, only the code decides.
- "split invoice pages" / "invoice page splitting" are deliberately
  phrases: grouping pages by invoice is the core of this family.
  But "invoice pages" can also name pages of one invoice (a
  multi-page invoice) rather than pages across invoices: a doc that
  means paginating a single invoice, not grouping pages by invoice,
  is a false positive; the tool flags the claim, only the code
  decides.
- "invoice batch splitting" / "split invoice batch" are deliberately
  phrases: "batch" names the batched PDF this family splits. But
  "batch" can also name batch processing of already-separate
  invoices (running extraction over a folder of invoice files):
  a doc that means batch extraction, not splitting one batched
  document, is a false positive; the tool flags the claim, only
  the code decides.
- "multi invoice splitting" / "split multi invoices" are
  deliberately phrases. But "multi invoice" can also name a single
  document that itself contains several invoices as line items
  (a consolidated invoice) rather than a batched PDF of separate
  invoices: a doc that means parsing a consolidated invoice, not
  splitting a batch, is a false positive; the tool flags the claim,
  only the code decides.
- "invoice document splitting" / "split invoice document" are
  deliberately phrases. But "invoice document" can also name the
  document class in general ("invoice documents include PDFs and
  scans") rather than the splitting operation — the phrase lists
  require a splitting verb, so a bare class mention is not a
  phrase. Say so in the README.
- InvoiceSplitterV1 groups pages; it carries no invoice fields
  (no totals, no supplier names, no invoice numbers, no line
  items). A tool that extracts those does so through some other
  route; this family checks for the InvoiceSplitterV1 call, not
  for those fields. Say so in the README.
- A generic `split_invoices(` / `split_invoice(` /
  `split_invoice_document(` call can name a string splitter for
  text the user typed in rather than a document splitter: the
  tool counts the call, the claim plus the code decide — and a
  subprocess call invoking an external CLI is NOT evidence by
  design, so a thin wrapper that only calls subprocess fails.
- Mindee `parse` with InvoiceSplitterV1 counts as evidence: the
  product exists in mindee 4.22.0 (wheel inspected 2026-11-15). The
  tool detects the call in source, not whether the call succeeds
  against a current API version. Say so in the README.
- Mindee `parse` with InvoiceSplitterV1 is NOT a 4.x-only
  fingerprint: mindee 5.x kept the invoice splitter product (5.4.0
  wheel inspected 2026-11-15 — it is still present at
  mindee/v1/product/invoice_splitter/). Say so in the README.
- Veryfi `split_and_process_pdf` / `split_and_process_pdf_url`
  counts as evidence: the methods exist in veryfi 5.1.0 (wheel
  inspected 2026-11-15). The route is generic across receipts and
  invoices — the operation is splitting a batched PDF into its
  constituent documents. Say so in the README.
- Mindee `parse` with InvoiceV4 / ReceiptV5 / FinancialDocumentV1 /
  PassportV1 / BankCheckV1 / BankAccountDetailsV1 /
  BankAccountDetailsV2 / PayslipV2 / PayslipV3 / NutritionFactsLabelV1 /
  HealthcareCardV1 / BusinessCardV1 / CustomV1 / GeneratedV1 /
  BillOfLadingV1 / ResumeV1 / DeliveryNoteV1 / DriverLicenseV1 /
  IdCardV1 / InternationalIdV2 / CarteGriseV1 / EnergyBillV1 /
  MaterialCertificateV1 / BarcodeReaderV1 / CropperV1 /
  MultiReceiptsDetectorV1 / UsMailV2 / UsMailV3 is NOT detected:
  those are other document types or other operations. Say so in
  the README.
- Mindee `parse` with InvoiceV4 alone is NOT detected even though
  it reads invoices: extracting fields from one invoice is not
  splitting a batched invoice PDF into invoices, and the
  invoice-only route is the invoice family's domain. The same
  holds for ReceiptV5 alone and FinancialDocumentV1 alone. Say so
  in the README.
- Mindee `parse` with MultiReceiptsDetectorV1 is NOT detected:
  detecting how many receipts sit in one image is detection, not
  splitting a batched invoice PDF. Say so in the README.
- Mindee `parse` with CropperV1 is NOT detected: cropping a
  document region is not splitting invoices. Say so in the README.
- Azure `begin_analyze_document` with ANY model id is NOT
  detected: Azure Document Intelligence has no invoice splitter
  model (the Learn v4.0 GA prebuilt-model pages list no such
  model, verified 2026-11-15). Say so in the README.
- Veryfi `split_and_process_w2` / `split_and_process_w2_url` are
  NOT detected: W-2 splitting is the tax-form family's domain.
  Veryfi `get_pdf` / `get_documents_from_pdf` are NOT detected:
  retrieval of an already-split document set is not the splitting
  operation. Veryfi calls of any other kind are NOT detected
  either, except the two split_and_process_pdf methods above. Say
  so in the README.
- Google Document AI `process_document` / `batch_process_documents`
  with ANY processor is NOT detected: Document AI has no invoice
  splitter processor (the processors list page contains no such
  processor, verified 2026-11-15). Say so in the README.
- Eden AI universal-ai calls with ANY model id are NOT detected:
  the model id is a plain string inside an arbitrary request
  payload, not a typed SDK call, so there is no fixed static
  fingerprint for the call itself. Say so in the README.
- LlamaParse calls are NOT detected: its parsing API is
  generative with no fixed static fingerprint naming invoice
  splitting. Say so in the README.
- Nanonets / Docsumo / ABBYY Vantage / Rossum / Klippa / Parseur /
  Extend calls are NOT detected: opaque model / skill / queue /
  template / workflow IDs, or a generic upload endpoint with the
  document type configured outside the call — no fixed fingerprint.
  Say so in the README.
- Textract `analyze_document` / `analyze_expense` / `analyze_id` /
  `start_document_analysis` / `get_expense_analysis` are NOT
  detected: generic document, expense, and identity analysis are
  not invoice splitting, and Textract has no invoice splitting
  operation. Say so in the README.
- PDF page-count splits (pypdf / PyPDF2 page slicing, pdfplumber
  page iteration, fitz page extraction, fixed-N-pages chunking)
  and PDF bookmark splits are NOT detected: cutting a PDF every N
  pages or on bookmarks does not detect invoice boundaries and
  can cut an invoice in half. Say so in the README.
- Generic "split pdf" / "split document" calls (split_pdf /
  split_document / pdf_splitter / document_splitter with no
  "invoice" qualifier) are NOT detected: a bare split call could
  name splitting any document, not invoices. Say so in the README.
- A hand-rolled split from OCR text (`re.search` /
  `re.findall` on extracted text plus manual page assembly, no
  listed call) is NOT detected: the tool requires a listed call.
  Say so in the README.
- The mindee CLI, the veryfi CLI, and any other external invoice
  splitter tool invoked through subprocess are NOT detected:
  subprocess calls invoking an external CLI are NOT evidence by
  design. Say so in the README.
- Azure Document Intelligence, Mindee, and Veryfi are cloud APIs:
  the tool detects the client call in source, not whether
  credentials are configured or the call succeeds. Say so in the
  README.
- "extract invoices" / "invoice extraction" / "extract invoice
  fields" claims are NOT in the phrase lists: extracting fields
  from one invoice is a different operation from splitting a
  batched invoice PDF into invoices. Say so in the README.
- "split pdf" / "pdf splitting" / "split documents" claims are NOT
  in the phrase lists: splitting a generic PDF or document is a
  different operation from splitting invoices. Say so in the
  README.
- "extract receipts" / "receipt extraction", "extract financial
  documents" / "financial document extraction", "extract bank
  statements" / "statement extraction", "extract tax forms" /
  "extract w2 forms", "extract pay stubs" / "payslip extraction",
  "extract us mail" / "us mail extraction", "extract contracts" /
  "contract extraction", "extract resumes" / "resume extraction",
  "extract bills of lading" / "bill of lading extraction",
  "extract delivery notes" / "delivery note extraction",
  "extract carte grises" / "carte grise extraction",
  "extract energy bills" / "energy bill extraction",
  "extract marriage certificates" / "marriage certificate
  extraction", "extract bank account details" / "bank details
  extraction", "extract nutrition facts labels" / "nutrition facts
  label extraction", "extract material certificates" / "material
  certificate extraction", and "extract bank checks" / "check
  extraction" claims are NOT in the phrase lists: this family
  covers invoice splitting only. Say so in the README.
- As with every family: static pattern matching, not semantic
  judgement; dead code counts; alias chains the tracer cannot follow
  are missed; exact phrases only, not semantics; denial handling
  depends on the denial phrase list; each route must sit in a single
  module.
```
