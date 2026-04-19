# Patrika

Automated handwritten assessment platform.

## What it does
Students write on dotted paper (e.g Anoto) with an infrared pen. Patrika captures handwriting in real time, renders a structured digital assessment with solution replay, and delivers feedback to both student and teacher.

**Demo video:** 
https://youtu.be/MrDMNqjp7Dk

## Why it matters
- Eliminates 5–10 hours/week of manual marking per educator
- Physical writing workflow — no scanning or typing
- Native STEM notation support
- Solution replay shows reasoning sequence, not just final answer
- Built-in contestation workflow and multilingual grading

## Traction
- First paying customer: 40-unit order, Tempah Digital Sdn. Bhd. (Malaysia)
- Pilot: IITM MSc Physics lab assessments
- Pilot: IITM Global Engagement Centre
- Sterling Road Imperial College Grant (2025)
- Provisional patent filed (India)

## Tech stack
- IR pen + dotted paper capture (here we've used Anoto paper pattern and INQ pens)
- Python (cv2, asyncio, tkinter, json)
- OCR / ML assessment layer
- Arduino
- HTML frontend

## Status
Active — pilots running at IIT Madras


## Installation

**Requirements:** Python 3.9+

Install dependencies:
```bash
pip install anthropic pillow reportlab
```

You also need an **Anthropic API key**. Open `src/pipeline_poc.py` and paste your key here:
```python
API_KEY = "your-key-here"
```

## Usage

**1. Add your student image**

Place a JPEG of the student's handwritten answer in the `src/` folder. 
By default the script looks for `q5_poc.jpeg` — rename your file to match, or update this line:
```python
IMAGE_S4 = os.path.join(os.path.dirname(__file__), "q5_poc.jpeg")
```

**2. Run the pipeline**
```bash
cd src
python pipeline_poc.py
```

**3. What happens**
- Claude vision evaluates the handwritten answer against the mark scheme
- An annotated PDF is generated showing per-line feedback
- A teacher dashboard (tkinter window) opens showing all students' marks
- Click "View" next to any student to open their annotated submission
- Click "Open Full Report" for the full class PDF summary

## Demo

S1–S3 use pre-computed results. S4 is evaluated live against the mark scheme using Claude vision.
Output files are saved to `~/Documents/iitm/mathi/`.


## Paper format

The system reads handwriting on Anoto dotted paper in a specific layout.
Each block is separated by a horizontal line written across the page.

### Layout example

    x-----------------x
    Q8    Find the roots of x²-6x+8                        (2)
    A
          M1a  Factorises expression to (x-4)(x-2)         (1)
          M1b  Writes equations of the form
               a+b=-6 ; ab=8 and correctly
               solves for a,b                              (1)
          M1c  Applies quadratic formula x=(-b±√b²-4ac)/2a
               with a,b,c correctly identified             (1)
          M2   States correct roots
               x = +4                                      (½)
          M3   and x = +2                                  (½)
    x-----------------x
    S1    x=+3  x=4  x=+4
    S2    x²-6x+8 = (x-4)(x-2)
          ⟹ x=4, x=2
    x-----------------x

### Codes written on the left margin

| Code | Meaning | Example |
|------|---------|---------|
| `Q8` | Teacher's question number | `Q8` |
| `A` | Marks the start of the mark scheme block | `A` |
| `M1a`, `M1b`, `M1c` | Mark scheme criteria — sub-criteria under M1 | `M1a` |
| `M2`, `M3` | Further mark criteria | `M2` |
| `(1)`, `(½)` | Marks available for that criterion, written in right margin | `(½)` |
| `S1`, `S2` | Student responses — X is the student ID number | `S1` |
| `x` | Tick/cross written by system next to student response | `x` (cross) |

### How the system reads it
1. Teacher writes the question (`Q8`) and mark scheme (`A`, `M1a`...) on the left
2. Marks available per criterion are written in brackets on the right margin
3. Students write their responses below, prefixed with their ID (`S1`, `S2`...)
4. Claude vision reads the full page, matches each student response against the mark scheme, and awards marks per criterion

### Generalisation
The quadratic equation is the POC case. Any written mathematical question 
works — the mark scheme is defined by the teacher per question (M1, M2...) 
and Claude evaluates each student response against it automatically.

