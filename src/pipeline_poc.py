"""
pipeline_poc.py
===============
POC demo for Patrika — automated exam marking system.

Components:
  (ii) Teacher dashboard — tkinter UI showing per-student mark breakdown,
       click to view annotated submission PDF
  (iii) Student submission annotator — uses Claude vision to identify
        correct/incorrect lines, draws red boxes, ticks, and margin marks
"""

import os, re, base64, json, tkinter as tk
from tkinter import ttk, font as tkfont
import anthropic
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── CONFIG ────────────────────────────────────────────────────────────────────
API_KEY       = ""
OUTPUT_DIR    = os.path.expanduser("~/Documents/iitm/mathi")
IMAGE_S4      = os.path.join(os.path.dirname(__file__), "q5_poc.jpeg")
os.makedirs(OUTPUT_DIR, exist_ok=True)

client = anthropic.Anthropic(api_key=API_KEY)

# ── Q5 MARK SCHEME ────────────────────────────────────────────────────────────
Q5_SCHEME = {
    "question": "Find the roots of x² - 5x + 6",
    "max_marks": 2.0,
    "criteria": [
        {"label": "M1", "description": "Correct method: factorisation OR solving a+b=-5,ab=6 OR quadratic formula", "max": 1.0},
        {"label": "M2", "description": "Stating root x=2", "max": 0.5},
        {"label": "M3", "description": "Stating root x=3", "max": 0.5},
    ]
}

# ── PRE-COMPUTED RESULTS (S1-S3 from previous run, S4 annotated live) ─────────
RESULTS = [
    {
        "student_id": "S1",
        "question": "Q5",
        "total": 1.0,
        "max_marks": 2.0,
        "scheme_breakdown": [
            {"label": "M1", "awarded": 0.0, "max": 1.0, "reason": "Factorised incorrectly as (x-3)(x+2)"},
            {"label": "M2", "awarded": 0.5, "max": 0.5, "reason": None},
            {"label": "M3", "awarded": 0.5, "max": 0.5, "reason": None},
        ],
        "image": None
    },
    {
        "student_id": "S2",
        "question": "Q5",
        "total": 2.0,
        "max_marks": 2.0,
        "scheme_breakdown": [
            {"label": "M1", "awarded": 1.0, "max": 1.0, "reason": None},
            {"label": "M2", "awarded": 0.5, "max": 0.5, "reason": None},
            {"label": "M3", "awarded": 0.5, "max": 0.5, "reason": None},
        ],
        "image": None
    },
    {
        "student_id": "S3",
        "question": "Q5",
        "total": 0.0,
        "max_marks": 2.0,
        "scheme_breakdown": [
            {"label": "M1", "awarded": 0.0, "max": 1.0, "reason": "Discriminant computed incorrectly, no valid method"},
            {"label": "M2", "awarded": 0.0, "max": 0.5, "reason": "Root x=2 not stated"},
            {"label": "M3", "awarded": 0.0, "max": 0.5, "reason": "Root x=3 not stated"},
        ],
        "image": None
    },
    {
        "student_id": "S4",
        "question": "Q5",
        "total": None,  # computed live
        "max_marks": 2.0,
        "scheme_breakdown": None,  # computed live
        "image": IMAGE_S4
    },
]

# ── STEP 1: ANNOTATE STUDENT SUBMISSION ───────────────────────────────────────
def encode_pil(img):
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")

def evaluate_and_annotate(image_path, scheme):
    """
    Send student image to Claude:
    1. Evaluate against scheme
    2. Get per-line feedback with y_position (0.0-1.0 fraction of image height)
    3. Draw ticks, crosses, underlines at correct positions
    """
    img = Image.open(image_path).convert("RGB")
    buf = encode_pil(img)
    _, h = img.size

    criteria_desc = "\n".join(
        f"- {c['label']} ({c['max']} marks): {c['description']}"
        for c in scheme["criteria"]
    )

    prompt = f"""You are marking a student's handwritten exam answer.

QUESTION: {scheme["question"]}

MARKING CRITERIA:
{criteria_desc}

Look at the image carefully. Identify each line of handwriting.
For each line, estimate its vertical position as a fraction of image height (0.0=top, 1.0=bottom).

Return ONLY valid JSON:
{{
  "criteria": [
    {{"label": "M1", "awarded": 1.0, "max": 1.0, "reason": null}},
    {{"label": "M2", "awarded": 0.5, "max": 0.5, "reason": null}},
    {{"label": "M3", "awarded": 0.0, "max": 0.5, "reason": "Wrong root: wrote x=-3 instead of x=3"}}
  ],
  "total": 1.5,
  "line_feedback": [
    {{"content": "x^2 - 5x + 6 = 0", "status": "neutral", "y_pos": 0.18, "mark_label": null}},
    {{"content": "(x-3)(x-2) = 0", "status": "correct", "y_pos": 0.28, "mark_label": "M1"}},
    {{"content": "x = -3, x = +2", "status": "partial", "y_pos": 0.38, "mark_label": "M3"}}
  ]
}}

Status values:
- "correct": line is fully correct, draw green tick + double underline
- "wrong": line contains an error, draw red cross
- "partial": line is partially correct (some right, some wrong), draw orange tilde ~
- "neutral": setup/working line, no annotation
- "final_correct": the final answer line if fully correct, draw double green underline
mark_label: which criterion this line satisfies (or null)
Rules: ALL OR NOTHING per criterion. Do not invent partial credit."""

    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": buf}},
                {"type": "text", "text": prompt}
            ]
        }]
    )

    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```json|^```|```$', '', raw, flags=re.MULTILINE).strip()
    raw = re.sub(r'\]\s*,\s*\{\"label\"', ', {"label"', raw)

    try:
        result = json.loads(raw)
    except Exception as e:
        print(f"[EVAL ERROR] {e}\nRaw: {raw}")
        result = {"criteria": scheme["criteria"], "total": 0, "line_feedback": []}

    print("[DEBUG] line_feedback:", json.dumps(result.get("line_feedback", []), indent=2))
    print("[DEBUG] criteria:", json.dumps(result.get("criteria", []), indent=2))
    print("[DEBUG] image size:", img.size)

    # Generate side-by-side annotated PDF
    ann_pdf = image_path.replace(".jpeg", "_annotated.pdf").replace(".jpg", "_annotated.pdf")
    generate_annotated_pdf(
        image_path    = image_path,
        line_feedback = result.get("line_feedback", []),
        criteria      = result.get("criteria", []),
        output_path   = ann_pdf,
        student_id    = "S4"
    )
    return result, ann_pdf

def generate_annotated_pdf(image_path, line_feedback, criteria, output_path, student_id="S?"):
    """Side-by-side PDF: cropped student image on left, mark breakdown on right."""
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from PIL import Image as PILImage

    # Crop image to writing area only (top 40% of page)
    pil = PILImage.open(image_path)
    pw, ph = pil.size
    cropped = pil.crop((0, 0, pw, int(ph * 0.42)))
    crop_path = output_path.replace(".pdf", "_crop.jpeg")
    cropped.save(crop_path, quality=95)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
        rightMargin=1*cm, leftMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []

    title_s  = ParagraphStyle("t",  fontSize=13, fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_CENTER)
    hdr_s    = ParagraphStyle("h",  fontSize=10, fontName="Helvetica-Bold", textColor=colors.white)
    cell_s   = ParagraphStyle("c",  fontSize=10, fontName="Helvetica", leading=14)
    bold_s   = ParagraphStyle("b",  fontSize=10, fontName="Helvetica-Bold", leading=14)
    reason_s = ParagraphStyle("rs", fontSize=9,  fontName="Helvetica-Oblique",
                               textColor=colors.HexColor("#CC2200"), leading=12)

    story.append(Paragraph("Mathi — Student Submission Review", title_s))
    story.append(Spacer(1, 0.3*cm))

    total = sum(float(c.get("awarded", 0)) for c in criteria)
    max_m = sum(float(c.get("max", 0)) for c in criteria)
    pct   = total / max_m if max_m else 0

    # Image — twice as wide, proportional height
    img_rl = RLImage(crop_path, width=13*cm, height=16*cm, kind="proportional")

    # ── Feedback table: only show criteria breakdown (skip line-by-line) ──
    # Header
    student_id = output_path.split("/")[-1].replace("_annotated.pdf","").replace("_annotated","")

    tdata = [[
        Paragraph("Student", hdr_s),
        Paragraph("Criterion", hdr_s),
        Paragraph("Score", hdr_s),
        Paragraph("Feedback", hdr_s),
    ]]

    # Per-criterion rows
    for i, c in enumerate(criteria):
        got  = float(c.get("awarded", 0))
        mx   = float(c.get("max", 0))
        rsn  = c.get("reason") or ""
        ok   = got >= mx
        sym  = "✓" if ok else "✗"
        score_para = Paragraph(
            f'<font color="{"#006600" if ok else "#CC0000"}">{sym} {got}/{mx}</font>',
            bold_s
        )
        tdata.append([
            Paragraph(student_id if i == 0 else "", bold_s),
            Paragraph(c["label"], bold_s),
            score_para,
            Paragraph(rsn[:55], reason_s) if rsn else Paragraph("—", cell_s),
        ])

    # Separator + total
    tdata.append(["", "", "", ""])
    tot_col = "#006600" if pct >= 0.8 else "#CC6600" if pct >= 0.5 else "#CC0000"
    tdata.append([
        Paragraph("", cell_s),
        Paragraph("TOTAL", bold_s),
        Paragraph(f'<font color="{tot_col}">{total}/{max_m}</font>', bold_s),
        Paragraph("", cell_s),
    ])

    n = len(tdata)
    ftable = Table(tdata, colWidths=[2*cm, 2.5*cm, 2*cm, 3.5*cm])
    ftable.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),   colors.HexColor("#1A2940")),
        ("TEXTCOLOR",     (0,0), (-1,0),   colors.white),
        ("GRID",          (0,0), (-1,-1),  0.5, colors.HexColor("#CCCCCC")),
        ("ALIGN",         (0,0), (-1,-1),  "CENTER"),
        ("VALIGN",        (0,0), (-1,-1),  "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1),  6),
        ("BOTTOMPADDING", (0,0), (-1,-1),  6),
        ("ROWBACKGROUNDS",(0,1), (-1,n-3), [colors.white, colors.HexColor("#F5F7FA")]),
        ("BACKGROUND",    (0,n-1),(-1,n-1), colors.HexColor("#EEF4FF")),
        ("FONTNAME",      (0,n-1),(-1,n-1), "Helvetica-Bold"),
        ("LINEABOVE",     (0,n-2),(-1,n-2), 1.5, colors.HexColor("#1A2940")),
    ]))

    # Side by side
    layout = Table([[img_rl, ftable]], colWidths=[11*cm, 10.5*cm])
    layout.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
    ]))
    story.append(layout)
    doc.build(story)
    print(f"[ANNOTATED PDF] {output_path}")


def draw_annotations(img, line_feedback, criteria):
    """Kept for compatibility — actual annotation now done as PDF."""
    return img


# ── STEP 2: GENERATE TEACHER REPORT PDF ───────────────────────────────────────
def generate_report_pdf(results, output_path):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    doc = SimpleDocTemplate(output_path, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    title_style  = ParagraphStyle('t', fontSize=16, alignment=TA_CENTER, spaceAfter=4, fontName='Helvetica-Bold')
    sub_style    = ParagraphStyle('s', fontSize=10, alignment=TA_CENTER, spaceAfter=8, fontName='Helvetica', textColor=colors.HexColor('#555555'))
    cell_style   = ParagraphStyle('c', fontSize=9,  alignment=TA_CENTER, leading=13, fontName='Helvetica')
    reason_style = ParagraphStyle('r', fontSize=8,  alignment=TA_CENTER, leading=11, fontName='Helvetica-Oblique', textColor=colors.HexColor('#CC2200'))
    story.append(Paragraph("Mathi — Automated Assessment Report", title_style))
    story.append(Paragraph("Q5 · Find the roots of x² − 5x + 6 · 2 marks", sub_style))
    story.append(Spacer(1, 0.4*cm))
    table_data = [['Student', 'Question', 'Mark Allocation', 'Total']]
    for r in results:
        breakdown = r.get("scheme_breakdown") or []
        lines = []
        for s in breakdown:
            awarded = s.get("awarded", 0)
            max_m   = s.get("max", 0)
            lines.append(Paragraph(f"{s['label']}: {awarded}/{max_m}", cell_style))
            reason = s.get("reason")
            if reason and float(awarded) < float(max_m):
                lines.append(Paragraph(reason, reason_style))
        total_str = f"{r['total']}/{r['max_marks']}" if r['total'] is not None else "—"
        table_data.append([
            Paragraph(r['student_id'], cell_style),
            Paragraph(r['question'],   cell_style),
            lines or [Paragraph("—", cell_style)],
            Paragraph(total_str, cell_style)
        ])
    table = Table(table_data, colWidths=[2.5*cm, 2.5*cm, 9*cm, 2*cm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0),  colors.HexColor('#1A2940')),
        ('TEXTCOLOR',     (0,0),(-1,0),  colors.white),
        ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,0),  10),
        ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#F5F7FA')]),
        ('GRID',          (0,0),(-1,-1), 0.5, colors.black),
        ('BACKGROUND',    (-1,1),(-1,-1),colors.HexColor('#E8F4FD')),
        ('FONTNAME',      (-1,1),(-1,-1),'Helvetica-Bold'),
    ]))
    story.append(table)
    doc.build(story)
    print(f"[REPORT] {output_path}")

# ── STEP 3: TEACHER DASHBOARD ─────────────────────────────────────────────────
def launch_dashboard(results, report_pdf):
    import tkinter as tk
    from tkinter import font as tkfont
    root = tk.Tk()
    root.title("Mathi — Teacher Dashboard")
    root.configure(bg="#FFFFFF")
    root.geometry("960x560")
    root.resizable(True, True)

    try:
        title_font  = tkfont.Font(family="Arial", size=22, weight="bold")
        header_font = tkfont.Font(family="Arial", size=12, weight="bold")
        body_font   = tkfont.Font(family="Arial", size=11)
        btn_font    = tkfont.Font(family="Arial", size=11)
    except:
        title_font = header_font = body_font = btn_font = None

    # Header
    header = tk.Frame(root, bg="#FFFFFF", pady=12)
    header.pack(fill="x", padx=24)
    tk.Label(header, text="Mathi", bg="#FFFFFF", fg="#000000", font=title_font).pack(side="left")
    tk.Label(header, text="  — Automated Assessment Dashboard", bg="#FFFFFF", fg="#333333", font=body_font).pack(side="left", pady=4)
    tk.Button(header, text="Open Full Report",
              command=lambda: os.system(f'open "{report_pdf}"'),
              bg="#1A2940", fg="#FFFFFF", font=btn_font,
              relief="flat", padx=10, pady=5, cursor="hand2").pack(side="right")

    # Question bar
    qbar = tk.Frame(root, bg="#1A2940", pady=8)
    qbar.pack(fill="x", padx=24)
    tk.Label(qbar, text="Q5 · Find the roots of x² - 5x + 6 · 2 marks",
             bg="#1A2940", fg="#FFFFFF", font=header_font).pack(side="left", padx=10)

    # Table
    table_frame = tk.Frame(root, bg="#FFFFFF")
    table_frame.pack(fill="both", expand=True, padx=24, pady=8)

    cols       = ["Student", "M1 (method)", "M2 (root x=2)", "M3 (root x=3)", "Total", "Submission"]
    col_widths = [80, 180, 130, 130, 80, 120]

    # Header row
    hdr = tk.Frame(table_frame, bg="#1A2940", highlightbackground="#000000", highlightthickness=1)
    hdr.pack(fill="x")
    for col, cw in zip(cols, col_widths):
        tk.Label(hdr, text=col, width=cw//8, bg="#1A2940", fg="#FFFFFF",
                 font=header_font, anchor="center", pady=6).pack(side="left", padx=1)

    for r in results:
        bd     = r.get("scheme_breakdown") or []
        bd_map = {s["label"]: s for s in bd}

        tk.Frame(table_frame, bg="#000000", height=1).pack(fill="x")
        row = tk.Frame(table_frame, bg="#FFFFFF", pady=4)
        row.pack(fill="x")

        def cell(txt, col, w):
            tk.Label(row, text=txt, width=w//8, bg="#FFFFFF", fg=col,
                     font=body_font, anchor="center", wraplength=w-8).pack(side="left", padx=2)

        cell(r["student_id"], "#000000", col_widths[0])

        for key, cw in zip(["M1","M2","M3"], col_widths[1:4]):
            c = bd_map.get(key)
            if c:
                got   = c.get("awarded", 0)
                mx    = c.get("max", 1)
                rsn   = c.get("reason", "") or ""
                color = "#008800" if got >= mx else "#CC0000"
                sym   = "✓" if got >= mx else "✗"
                txt   = f"{sym} {got}/{mx}"
                if rsn: txt += f"\n{rsn[:35]}"
            else:
                color, txt = "#888888", "—"
            cell(txt, color, cw)

        total = r.get("total")
        max_m = r.get("max_marks", 2.0)
        if total is not None:
            pct  = total/max_m
            tcol = "#008800" if pct>=0.8 else "#CC6600" if pct>=0.5 else "#CC0000"
            cell(f"{total}/{max_m}", tcol, col_widths[4])
        else:
            cell("—", "#888888", col_widths[4])

        ann = r.get("annotated_path")
        tk.Button(row, text="📄 View",
                  command=lambda p=ann: os.system(f'open "{p}"') if p and os.path.exists(p) else None,
                  bg="#AAAAAA", fg="#000000", font=btn_font,
                  relief="raised", padx=8, pady=2, cursor="hand2", width=8).pack(side="left", padx=6)

    # Footer
    tk.Frame(root, bg="#000000", height=1).pack(fill="x", side="bottom")
    tk.Label(root, text="Mathi POC · IIT Madras", bg="#FFFFFF", fg="#888888", font=btn_font).pack(side="bottom", pady=4)

    root.mainloop()

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("[MATHI POC] Starting...")
    print("[EVALUATING] S4 — annotating submission...")
    s4 = RESULTS[3]
    result, ann_pdf = evaluate_and_annotate(s4["image"], Q5_SCHEME)
    ann_path = ann_pdf  # ann_pdf returned from evaluate_and_annotate
    print(f"[ANNOTATED] Saved to {ann_path}")
    s4["total"]            = result.get("total", 0)
    s4["scheme_breakdown"] = result.get("criteria", [])
    s4["annotated_path"]   = ann_path
    report_pdf = os.path.join(OUTPUT_DIR, "poc_report_Q5.pdf")
    generate_report_pdf(RESULTS, report_pdf)
    print("[DASHBOARD] Launching...")
    launch_dashboard(RESULTS, report_pdf)

if __name__ == "__main__":
    main()
