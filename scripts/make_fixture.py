"""Generate scripts/fixtures/sample.pdf for the smoke test.

Run: uv run --with reportlab python scripts/make_fixture.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

PAGES = [
    [
        "The Zebra Protocol",
        "The Zebra Protocol is a fictional handshake used by migrating data herds.",
        "Each node announces itself with alternating black and white packets.",
        "A handshake completes after exactly seven stripes are exchanged.",
    ],
    [
        "Zebra Protocol Failure Modes",
        "If a node sends two black packets in a row, the herd marks it as a lion.",
        "Lions are quarantined for ninety seconds before they may rejoin.",
    ],
]

out = Path(__file__).parent / "fixtures" / "sample.pdf"
out.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(out), pagesize=LETTER)
for lines in PAGES:
    y = 720
    for line in lines:
        c.drawString(72, y, line)
        y -= 20
    c.showPage()
c.save()
print(f"wrote {out}")
