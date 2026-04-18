## TASK-2.14: Prereq — Extract authoritative data from BitLedger_Technical_Overview.docx

Goal:                 Read BitLedger_Technical_Overview.docx using Python XML extraction
                      and produce structured excerpts for: (1) the 31-currency ordered
                      list, (2) the wizard field order and valid ranges, (3) the
                      simulator output format if specified, (4) any Layer 1/2 field
                      default values that differ from TECHNICAL_OVERVIEW.md.

Acceptance criteria:  1. Currency list: all 31 named currencies with index, code, name,
                         symbol extracted in canonical order (index 1–31)
                      2. Wizard field order: confirmed sequence for Layer 1 and Layer 2
                         prompts, with valid ranges and display labels
                      3. Simulator format: either a confirmed spec or "not specified —
                         use TASK-2.11 design" determination
                      4. Layer 1/2 defaults: any value in docx that differs from
                         TECHNICAL_OVERVIEW.md is flagged and recorded in
                         system/logs/decisions.md with Orchestrator resolution
                      5. Output written to system/audits/docx-extract.md for reference
                         by TASK-2.02, TASK-2.10, TASK-2.11
                      6. This task produces no production code — it is a read-only
                         data extraction task

Write scope:          system/audits/docx-extract.md (new)
                      system/logs/decisions.md (append if conflicts found)

Tests required:       (none — read-only extraction task)

Rollback:             (none — only creates new files)

Fragility:            The currency index ordering is wire-format data. Any index
                      assignment error here will silently corrupt all records that use
                      the affected currency code. Verify the extraction by cross-checking
                      against the Protocol v3 spec if currencies appear in both documents.

Risk notes:           (Orchestrator) Use Python zipfile + xml.etree to extract docx body
                      text — do not rely on file metadata. The docx XML namespace is
                      http://schemas.openxmlformats.org/wordprocessingml/2006/main.
                      Extract paragraphs in order; tables require iterating <w:tr> rows.
                      If the docx content contradicts TECHNICAL_OVERVIEW.md on any
                      protocol field value, log it in decisions.md before proceeding.

Depends on:           (none — prerequisite task, run before TASK-2.02 and TASK-2.10)

Status:               pending

