import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt

def generate_icon(output_path="app_icon.ico"):
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    
    for s in sizes:
        pix = QPixmap(s, s)
        pix.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        corner = max(2, int(s * 0.22))
        painter.setBrush(QColor("#1e1e1e"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, s, s, corner, corner)
        
        painter.setPen(QColor("#4ec9b0"))
        font_size = max(6, int(s * 0.42))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, ">_")
        painter.end()
        
        images.append(pix.toImage())

    saved = False
    try:
        from PIL import Image
        import io
        pil_images = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, "PNG")
            buf.seek(0)
            pil_images.append(Image.open(buf))
        
        pil_images[-1].save(
            output_path,
            format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=pil_images[:-1]
        )
        saved = True
    except Exception as e:
        try:
            saved = images[-1].save(output_path, "ICO")
        except Exception:
            pass

    if saved:
        print(f"[OK] Icon successfully created: {output_path}")
    else:
        png_path = os.path.splitext(output_path)[0] + ".png"
        images[-1].save(png_path, "PNG")
        print(f"[WARN] Saved as PNG: {png_path}")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    generate_icon(out)