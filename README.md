# Patrika

Automated handwritten assessment platform.

## What it does
Students write on dotted paper (e.g Anoto) with an infrared pen. Patrika captures handwriting in real time, renders a structured digital assessment with solution replay, and delivers feedback to both student and teacher.

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
