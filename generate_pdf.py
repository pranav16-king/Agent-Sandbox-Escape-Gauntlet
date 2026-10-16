#!/usr/bin/env python3
"""
Agent Sandbox Escape Gauntlet - Professional Document Generator
Converts D:\Agent Sandbox Escape Gauntlet\2.md to a highly readable,
beautifully arranged technical specification PDF using ReportLab.
Employs an elegant monochrome/neutral palette (no garish colors/animation),
crisp typography, structured tables, boxed code snippets, and clean headers/footers.
"""

import os
import re
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ------------------------------------------------------------------------------
# 1. Font Registration (Windows System Fonts)
# ------------------------------------------------------------------------------
FONT_FAMILY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_CODE = "Courier"
FONT_CODE_BOLD = "Courier-Bold"

font_dir = Path("C:/Windows/Fonts")
if (font_dir / "segoeui.ttf").exists():
    try:
        pdfmetrics.registerFont(TTFont("SegoeUI", str(font_dir / "segoeui.ttf")))
        pdfmetrics.registerFont(TTFont("SegoeUI-Bold", str(font_dir / "segoeuib.ttf")))
        pdfmetrics.registerFont(TTFont("SegoeUI-Italic", str(font_dir / "segoeuii.ttf")))
        FONT_FAMILY = "SegoeUI"
        FONT_BOLD = "SegoeUI-Bold"
        FONT_ITALIC = "SegoeUI-Italic"
    except Exception as e:
        print(f"Warning: Failed to register Segoe UI: {e}")

if (font_dir / "consola.ttf").exists():
    try:
        pdfmetrics.registerFont(TTFont("Consolas", str(font_dir / "consola.ttf")))
        pdfmetrics.registerFont(TTFont("Consolas-Bold", str(font_dir / "consolab.ttf")))
        FONT_CODE = "Consolas"
        FONT_CODE_BOLD = "Consolas-Bold"
    except Exception as e:
        print(f"Warning: Failed to register Consolas: {e}")

print(f"Active Fonts: Body={FONT_FAMILY}, Bold={FONT_BOLD}, Code={FONT_CODE}")

# ------------------------------------------------------------------------------
# 2. Refined Minimalist Palette (Strictly Neutral, Highly Readable)
# ------------------------------------------------------------------------------
COLOR_TEXT = colors.HexColor("#1A202C")        # Deep charcoal body text
COLOR_MUTED = colors.HexColor("#4B5563")       # Muted slate for captions & metadata
COLOR_HEADING = colors.HexColor("#0F172A")     # Near-black slate for headings
COLOR_BORDER = colors.HexColor("#CBD5E1")      # Light neutral border (0.5 pt)
COLOR_DIVIDER = colors.HexColor("#E2E8F0")     # Thin crisp divider line
COLOR_BG_LIGHT = colors.HexColor("#F8FAFC")    # Very light neutral for code & callouts
COLOR_BG_ALT = colors.HexColor("#F1F5F9")      # Subtle neutral table header background
COLOR_ACCENT_BAR = colors.HexColor("#475569")  # Subtle charcoal bar for blockquotes

# ------------------------------------------------------------------------------
# 3. Two-Pass Numbered Canvas (Header & Footer with "Page X of Y")
# ------------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont(FONT_FAMILY, 8)
        self.setFillColor(COLOR_MUTED)
        self.setStrokeColor(COLOR_DIVIDER)
        self.setLineWidth(0.5)

        margin_x = 45
        right_x = 567
        top_y = 752
        bottom_y = 42

        # Running header on page 2 onwards
        if self._pageNumber > 1:
            self.line(margin_x, top_y, right_x, top_y)
            self.drawString(margin_x, top_y + 4.5, "AGENT SANDBOX ESCAPE GAUNTLET — SYSTEM ARCHITECTURE SPECIFICATION")
            self.drawRightString(right_x, top_y + 4.5, "REV 0.1.0")

        # Running footer on all pages
        self.line(margin_x, bottom_y, right_x, bottom_y)
        self.drawString(margin_x, bottom_y - 12, "CONFIDENTIAL & PROPRIETARY — SECURITY ARCHITECTURE SPECIFICATION")
        self.drawRightString(right_x, bottom_y - 12, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()

# ------------------------------------------------------------------------------
# 4. Text Sanitizer & Inline Markdown Formatter
# ------------------------------------------------------------------------------
def sanitize_text(text: str) -> str:
    """Escapes XML entities and cleans unsupported unicode characters."""
    if not text:
        return ""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("\u00d7", "x").replace("\u2014", "--").replace("\u2013", "-")
    return text

def format_inline_md(text: str) -> str:
    """Converts inline markdown (bold, italic, code, links) to ReportLab XML tags."""
    if not text:
        return ""

    # Clean trailing backslashes used in markdown for linebreaks
    text = re.sub(r'\\+$', '', text.strip())

    # Escape HTML entities first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Replace special math multiplication sign
    text = text.replace("\u00d7", "x").replace("&times;", "x")

    # Inline code: `code`
    def repl_code(m):
        code_content = m.group(1)
        return f'<font name="{FONT_CODE}" size="8" color="#0F172A"><b>{code_content}</b></font>'
    text = re.sub(r'`([^`]+)`', repl_code, text)

    # Bold: **bold**
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)

    # Italic: *italic*
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)

    # Links: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    return text

# ------------------------------------------------------------------------------
# 5. Pandoc Grid Table Parser
# ------------------------------------------------------------------------------
def parse_pandoc_table(table_lines: list[str]):
    """Parses pandoc-style text tables into structured headers and rows."""
    if len(table_lines) < 3:
        return [], []

    delim_line = table_lines[2]
    spans = []
    for m in re.finditer(r'-+', delim_line):
        spans.append((m.start(), m.end()))

    if not spans:
        return [], []

    # Extract headers
    headers = []
    for s, e in spans:
        hdr = table_lines[1][s:e].strip() if s < len(table_lines[1]) else ""
        headers.append(hdr)

    # Extract body rows
    rows = []
    current_row = [""] * len(spans)

    for line in table_lines[3:-1]:
        # Empty line or divider line indicates a row separator
        if not line.strip() or line.strip().startswith("-----"):
            if any(c.strip() for c in current_row):
                rows.append([c.strip() for c in current_row])
                current_row = [""] * len(spans)
            continue

        for idx, (s, e) in enumerate(spans):
            val = line[s:e].strip() if s < len(line) else ""
            if val:
                if current_row[idx]:
                    current_row[idx] += " " + val
                else:
                    current_row[idx] = val

    if any(c.strip() for c in current_row):
        rows.append([c.strip() for c in current_row])

    return headers, rows

# ------------------------------------------------------------------------------
# 6. Main Document Builder
# ------------------------------------------------------------------------------
def build_pdf(input_md_path: str, output_pdf_path: str):
    print(f"Reading markdown source: {input_md_path}")
    with open(input_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    usable_width = 522  # 612 - 45*2
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=48,
        bottomMargin=48
    )

    style_title = ParagraphStyle(
        "DocTitle",
        fontName=FONT_BOLD,
        fontSize=21,
        leading=25,
        textColor=COLOR_HEADING,
        spaceAfter=8,
        keepWithNext=True
    )

    style_h1 = ParagraphStyle(
        "Heading1_Custom",
        fontName=FONT_BOLD,
        fontSize=13,
        leading=16.5,
        textColor=COLOR_HEADING,
        spaceBefore=14,
        spaceAfter=5,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        "Heading2_Custom",
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14,
        textColor=COLOR_HEADING,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    style_h3 = ParagraphStyle(
        "Heading3_Custom",
        fontName=FONT_BOLD,
        fontSize=9.5,
        leading=13,
        textColor=COLOR_HEADING,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        "Body_Custom",
        fontName=FONT_FAMILY,
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
        spaceAfter=5
    )

    style_bullet = ParagraphStyle(
        "Bullet_Custom",
        fontName=FONT_FAMILY,
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=2.5
    )

    style_num_list = ParagraphStyle(
        "NumList_Custom",
        fontName=FONT_FAMILY,
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
        leftIndent=16,
        firstLineIndent=-12,
        spaceAfter=2.5
    )

    style_callout = ParagraphStyle(
        "Callout_Custom",
        fontName=FONT_FAMILY,
        fontSize=8.5,
        leading=12.5,
        textColor=COLOR_TEXT
    )

    style_code_text = ParagraphStyle(
        "CodeText_Custom",
        fontName=FONT_CODE,
        fontSize=7.5,
        leading=9.8,
        textColor=COLOR_HEADING
    )

    style_th = ParagraphStyle(
        "TableHeader_Custom",
        fontName=FONT_BOLD,
        fontSize=8,
        leading=10.5,
        textColor=COLOR_HEADING
    )

    style_td = ParagraphStyle(
        "TableCell_Custom",
        fontName=FONT_FAMILY,
        fontSize=8,
        leading=10.5,
        textColor=COLOR_TEXT
    )

    style_toc_item = ParagraphStyle(
        "TocItem_Custom",
        fontName=FONT_FAMILY,
        fontSize=8,
        leading=11,
        textColor=COLOR_TEXT
    )

    story = []

    # --------------------------------------------------------------------------
    # Document Header / Banner (Executive Cover Block)
    # --------------------------------------------------------------------------
    story.append(Paragraph("Agent Sandbox Escape Gauntlet", style_title))
    
    tagline_text = (
        "<b>System Overview:</b> A security testing and containment platform for AI coding agents. "
        "Routes tool execution through controlled policies, runs tasks in isolated environments, "
        "records tamper-evident audit evidence, and objectively evaluates containment."
    )
    callout_data = [[Paragraph(tagline_text, style_callout)]]
    callout_tbl = Table(callout_data, colWidths=[usable_width])
    callout_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINEBEFORE', (0, 0), (0, -1), 3.0, COLOR_ACCENT_BAR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(callout_tbl)
    story.append(Spacer(1, 8))

    # Metadata Table
    meta_rows = [
        [Paragraph("<b>Document Version:</b>", style_td), Paragraph("0.1.0", style_td)],
        [Paragraph("<b>Project Status:</b>", style_td), Paragraph("Architecture and Starter Specification", style_td)],
        [Paragraph("<b>Target Audience:</b>", style_td), Paragraph("Developers, Security Researchers, Hackathon Teams, Engineering Students", style_td)],
        [Paragraph("<b>Date of Issue:</b>", style_td), Paragraph("October 2026", style_td)],
    ]
    meta_table = Table(meta_rows, colWidths=[120, usable_width - 120])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_ALT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_DIVIDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # --------------------------------------------------------------------------
    # Structured Table of Contents (2-Column Grid on Page 1)
    # --------------------------------------------------------------------------
    toc_items = [
        "1. Overview", "2. Problem Statement", "3. Goals and Non-Goals",
        "4. Core Features", "5. Architecture", "6. Technology Stack",
        "7. Repository Structure", "8. End-to-End Workflow", "9. Agent Integrations",
        "10. Security Model", "11. Benchmark & Test Dataset", "12. Data Model",
        "13. API Design", "14. Dashboard and Metrics", "15. Local Development Setup",
        "16. Configuration", "17. Testing and Validation", "18. Evaluation Methodology",
        "19. Deployment Guidance", "20. Limitations and Threats", "21. Roadmap",
        "22. Contributing", "23. License"
    ]
    mid = (len(toc_items) + 1) // 2
    col1_items = toc_items[:mid]
    col2_items = toc_items[mid:]

    toc_rows = [[Paragraph("<b>Table of Contents (Index of Sections)</b>", style_th), ""]]
    max_r = max(len(col1_items), len(col2_items))
    for r_idx in range(max_r):
        c1 = col1_items[r_idx] if r_idx < len(col1_items) else ""
        c2 = col2_items[r_idx] if r_idx < len(col2_items) else ""
        toc_rows.append([
            Paragraph(f"•&nbsp;&nbsp;{c1}", style_toc_item) if c1 else "",
            Paragraph(f"•&nbsp;&nbsp;{c2}", style_toc_item) if c2 else ""
        ])

    toc_table = Table(toc_rows, colWidths=[usable_width / 2, usable_width / 2])
    toc_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_BG_ALT),
        ('BACKGROUND', (0, 1), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_DIVIDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(toc_table)

    # PageBreak after Cover & Table of Contents so Section 1 begins cleanly on Page 2
    story.append(PageBreak())

    # --------------------------------------------------------------------------
    # Parse 2.md Content Lines
    # --------------------------------------------------------------------------
    raw_lines = content.splitlines()

    # Skip initial headers and markdown TOC (lines up to line 41)
    start_idx = 0
    for idx, line in enumerate(raw_lines):
        if line.strip() == "## 1. Overview":
            start_idx = idx
            break

    lines = raw_lines[start_idx:]
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i]
        stripped = line.strip()

        # 1. Blank line
        if not stripped:
            i += 1
            continue

        # 2. Check for Pandoc Grid Table START before checking horizontal divider
        if re.match(r'^[ ]*-{10,}$', line) and i + 2 < total_lines and re.match(r'^[ ]*-{3,}[ -]+$', lines[i+2]):
            table_lines = [line]
            i += 1
            while i < total_lines:
                table_lines.append(lines[i])
                if i > 2 and re.match(r'^[ ]*-{10,}$', lines[i]):
                    i += 1
                    break
                i += 1

            headers, rows = parse_pandoc_table(table_lines)

            if headers and rows:
                col_count = len(headers)
                # Compute balanced column widths
                if col_count == 3:
                    if "Layer" in headers[0]:
                        col_widths = [110, 150, usable_width - 260]
                    elif "Table" in headers[0]:
                        col_widths = [120, 180, usable_width - 300]
                    elif "Method" in headers[0]:
                        col_widths = [65, 175, usable_width - 240]
                    else:
                        col_widths = [usable_width / col_count] * col_count
                elif col_count == 4:
                    col_widths = [65, 95, 175, usable_width - 335]
                elif col_count == 2:
                    col_widths = [140, usable_width - 140]
                else:
                    col_widths = [usable_width / col_count] * col_count

                table_data = []
                # Header row
                table_data.append([Paragraph(format_inline_md(h), style_th) for h in headers])
                # Data rows
                for r in rows:
                    row_cells = []
                    for c in r:
                        row_cells.append(Paragraph(format_inline_md(c), style_td))
                    table_data.append(row_cells)

                t_flowable = Table(table_data, colWidths=col_widths, repeatRows=1)
                t_flowable.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), COLOR_BG_ALT),
                    ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_HEADING),
                    ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_DIVIDER),
                    ('TOPPADDING', (0, 0), (-1, -1), 3.5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
                ]))
                story.append(t_flowable)
                story.append(Spacer(1, 6))
            continue

        # 3. Horizontal divider
        if re.match(r'^-{5,}$', stripped):
            story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_DIVIDER, spaceAfter=8, spaceBefore=8))
            i += 1
            continue

        # 4. Headings
        if stripped.startswith("## "):
            title = format_inline_md(stripped[3:])
            story.append(Paragraph(title, style_h1))
            i += 1
            continue
        elif stripped.startswith("### "):
            title = format_inline_md(stripped[4:])
            story.append(Paragraph(title, style_h2))
            i += 1
            continue
        elif stripped.startswith("#### "):
            title = format_inline_md(stripped[5:])
            story.append(Paragraph(title, style_h3))
            i += 1
            continue

        # 5. Blockquotes
        if stripped.startswith("> "):
            quote_lines = []
            while i < total_lines and (lines[i].strip().startswith("> ") or (lines[i].strip() and quote_lines and not lines[i].strip().startswith("#"))):
                curr = lines[i].strip()
                if curr.startswith("> "):
                    curr = curr[2:]
                quote_lines.append(curr)
                i += 1
                if i < total_lines and not lines[i].strip():
                    break

            quote_text = format_inline_md(" ".join(quote_lines))
            c_table = Table([[Paragraph(quote_text, style_callout)]], colWidths=[usable_width])
            c_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('LINEBEFORE', (0, 0), (0, -1), 2.5, COLOR_ACCENT_BAR),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(c_table)
            story.append(Spacer(1, 4))
            continue

        # 6. Fenced Code Blocks
        if stripped.startswith("```"):
            lang = stripped[3:].strip().lower()
            code_lines = []
            i += 1
            while i < total_lines and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```

            code_body = "\n".join(code_lines)

            # Special aesthetic rendering for Mermaid Architecture Diagram
            if "mermaid" in lang or "flowchart" in code_body:
                diagram_header = Paragraph("<b>Architecture Dataflow Diagram (Logical Execution Path)</b>", style_h3)
                code_clean = sanitize_text(code_body)
                code_p = Paragraph(f"<pre>{code_clean}</pre>", style_code_text)
                d_table = Table([[diagram_header], [code_p]], colWidths=[usable_width])
                d_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                    ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(d_table)
                story.append(Spacer(1, 6))
            else:
                code_clean = sanitize_text(code_body)
                code_p = Paragraph(f"<pre>{code_clean}</pre>", style_code_text)
                code_table = Table([[code_p]], colWidths=[usable_width])
                code_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                    ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(code_table)
                story.append(Spacer(1, 6))
            continue

        # 7. Bullet Lists (- or *)
        if re.match(r'^[ ]*[-*][ ]+', stripped):
            list_text = re.sub(r'^[ ]*[-*][ ]+', '', stripped)
            # Use clean styled bullet marker
            story.append(Paragraph(f"-&nbsp;&nbsp;{format_inline_md(list_text)}", style_bullet))
            i += 1
            continue

        # 8. Numbered Lists (1. or 2.)
        match_num = re.match(r'^[ ]*(\d+)\.[ ]+(.*)', stripped)
        if match_num:
            num = match_num.group(1)
            list_text = match_num.group(2)
            story.append(Paragraph(f"<b>{num}.</b>&nbsp;&nbsp;{format_inline_md(list_text)}", style_num_list))
            i += 1
            continue

        # 9. Standard Paragraph (aggregate multiline paragraph blocks)
        p_lines = [stripped]
        i += 1
        while i < total_lines:
            next_line = lines[i].strip()
            if not next_line:
                break
            if (next_line.startswith("#") or next_line.startswith("```") or 
                next_line.startswith("> ") or re.match(r'^[ ]*[-*][ ]+', next_line) or 
                re.match(r'^[ ]*\d+\.[ ]+', next_line) or re.match(r'^-{5,}$', next_line)):
                break
            p_lines.append(next_line)
            i += 1

        full_p_text = format_inline_md(" ".join(p_lines))
        story.append(Paragraph(full_p_text, style_body))

    # --------------------------------------------------------------------------
    # Build Document with NumberedCanvas
    # --------------------------------------------------------------------------
    print(f"Building PDF with {len(story)} flowable elements...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {output_pdf_path}")

if __name__ == "__main__":
    src_file = r"D:\Agent Sandbox Escape Gauntlet\2.md"
    out_pdf = r"D:\Agent Sandbox Escape Gauntlet\Agent_Sandbox_Escape_Gauntlet_Specification.pdf"
    build_pdf(src_file, out_pdf)
