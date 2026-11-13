"""Dibuja el icono de la app (PNG 1024x1024). En macOS la CI lo convierte a .icns."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath

app = QGuiApplication([])
size = 1024
img = QImage(size, size, QImage.Format.Format_ARGB32)
img.fill(Qt.GlobalColor.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.RenderHint.Antialiasing)

# Fondo redondeado estilo macOS (margen del 10 %)
m = size * 0.1
rect = QRectF(m, m, size - 2 * m, size - 2 * m)
grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
grad.setColorAt(0, QColor("#4F7CFF"))
grad.setColorAt(1, QColor("#7B4DFF"))
path = QPainterPath()
path.addRoundedRect(rect, size * 0.18, size * 0.18)
p.fillPath(path, grad)

# Hoja blanca
sheet = QRectF(size * 0.30, size * 0.22, size * 0.40, size * 0.52)
sp = QPainterPath()
sp.addRoundedRect(sheet, size * 0.03, size * 0.03)
p.fillPath(sp, QColor("white"))

# "M↓" de Markdown
p.setPen(QColor("#4F5BD5"))
font = QFont("Helvetica", int(size * 0.13))
font.setBold(True)
p.setFont(font)
p.drawText(sheet, Qt.AlignmentFlag.AlignCenter, "M↓")
p.end()

out = sys.argv[1] if len(sys.argv) > 1 else "icon.png"
img.save(out)
print(out)
