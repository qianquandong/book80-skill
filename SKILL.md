---
name: distill-book
description: Distill an EPUB, PDF, or other long-form book into a fast, source-grounded briefing that conveys the highest-value 80% of its ideas. Use when a user wants to understand a whole book quickly, get a book summary with citations, identify the most valuable chapters, extract arguments and evidence, decide whether the original is worth reading, or turn a book into an actionable 30-second, 3-minute, and 10-minute report.
---

# Distill Book

Build a reliable mental model of a book in minutes. Optimize for understanding per minute, not coverage per page.

## Inputs

Accept:

- EPUB files
- Text-based or scanned PDF files
- Plain text, Markdown, HTML, or DOCX when the environment can extract them
- A book title only when the user explicitly asks for a synthesis from publicly available sources; disclose that this is not a source-grounded extraction of the full book

Match the user's language unless they request another language.

## Workflow

### 1. Establish the reading goal

Infer the goal from the request. If no goal is stated, use **rapid understanding**. Supported modes:

- **rapid understanding**: thesis, core ideas, argument structure, and high-value chapters
- **work application**: decisions, methods, checklists, and conditions for use
- **critical reading**: assumptions, weak evidence, counterarguments, and unresolved questions
- **content creation**: strong ideas, stories, examples, and angles worth developing
- **study**: definitions, relationships, likely questions, and retrieval prompts

Ask a question only when the missing choice would materially change the result.

### 2. Extract the source with stable locators

For EPUB, run:

```bash
python3 scripts/extract_epub.py BOOK.epub --output-dir EXTRACTED_DIR
```

Read `manifest.json`, then analyze chapter files in spine order.

For PDF:

1. Determine whether the PDF contains extractable text.
2. Extract text while retaining page boundaries.
3. Use OCR for image-only pages.
4. Remove repeated headers and footers without removing page locators.

For every format, preserve the strongest available locator:

1. page number
2. chapter plus section heading
3. EPUB spine index plus source file
4. paragraph index as a fallback

Do not silently summarize missing or unreadable sections. Report extraction gaps.

### 3. Analyze each chapter independently

Produce an internal chapter record with:

- chapter purpose
- new claims introduced
- supporting evidence or examples
- useful frameworks or methods
- assumptions and limitations
- relationship to earlier chapters
- novelty score from 1 to 5
- decision value from 1 to 5
- evidence strength from 1 to 5
- recommended action: read, skim, or skip
- source locators for every retained claim

Treat anecdotes, repeated explanations, scene-setting, and promotional material as low-value unless they are necessary to understand or evaluate a central claim.

### 4. Synthesize across the whole book

Do not concatenate chapter summaries. Instead:

1. Reconstruct the author's central question and thesis.
2. Merge semantically duplicate claims.
3. Separate premises, conclusions, evidence, examples, and advice.
4. Map how the major ideas depend on or contradict one another.
5. Rank ideas by explanatory power, practical value, novelty, and evidence.
6. Identify chapters that add little beyond repetition.
7. Check the final claims against their cited source passages.

Use the phrase “vital 80%” as a prioritization target, not a mathematical claim.

### 5. Produce a layered briefing

Read [references/report-protocol.md](references/report-protocol.md) before writing the final report. Follow its section order and evidence labels.

The report must support three reading speeds:

- **30 seconds**: decide what the book says and whether it matters
- **3 minutes**: acquire the book's conceptual skeleton
- **10 minutes**: understand the main claims, reasoning, evidence, and application

### 6. Verify before delivery

Check that:

- every quotation is verbatim and has a locator
- every major factual attribution has a locator
- AI inference is labeled and not presented as the author's claim
- repeated ideas are consolidated
- chapter rankings are justified
- the report names extraction gaps and uncertainty
- the output is substantially shorter than the source

If source coverage is incomplete, lower confidence rather than filling gaps from memory.

## Evidence Rules

Keep these categories visibly separate:

- **Author's claim**: a faithful paraphrase supported by a locator
- **Direct quote**: exact source text in quotation marks with a locator
- **Analysis**: interpretation or criticism produced during synthesis
- **Application**: a suggested use derived from the book

Never fabricate page numbers, quotations, chapter names, or citations.

When a digital edition has unstable page numbers, cite chapter and section or EPUB source location instead.

## Output Defaults

- Prefer concise prose and compact tables.
- Use Markdown unless the user requests another format.
- Include 5–10 core ideas, not one item per chapter.
- Include no more than 10 short direct quotes unless requested.
- End with the fastest useful next action: stop here, read selected chapters, or read the full book.
- Save a `.md` report beside the source when the user asks for a file.

## Failure Handling

- **DRM-protected book**: explain that the content cannot be extracted and ask for a DRM-free copy or exported text.
- **Scanned PDF with poor OCR**: report affected pages and avoid confident synthesis of unreadable material.
- **Very long book**: process in chapter batches, save intermediate chapter records, then synthesize globally.
- **Missing chapters**: list them explicitly in the coverage section.
- **Fiction**: adapt the report to plot architecture, characters, themes, style, and interpretive stakes; avoid exposing major spoilers unless requested.
