import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QRadialGradient, QFont, QPen, QBrush
from PySide6.QtCore import Qt, QPointF, QRectF
from PIL import Image

def create_premium_icon():
    app = QApplication(sys.argv)
    
    size = 512
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 1. Background Circle with Gradient (Cyberpunk style)
    grad = QRadialGradient(size/2, size/2, size/2)
    grad.setColorAt(0, QColor("#1e1e2e"))
    grad.setColorAt(1, QColor("#11111b"))
    
    painter.setBrush(grad)
    painter.setPen(QPen(QColor("#89b4fa"), 12))
    painter.drawEllipse(10, 10, size-20, size-20)
    
    # 2. Draw a Stylized "K"
    pen = QPen(QColor("#89b4fa"), 25)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    
    # K - Vertical line
    painter.drawLine(size*0.35, size*0.25, size*0.35, size*0.75)
    
    # K - Diagonal up
    painter.drawLine(size*0.35, size*0.5, size*0.65, size*0.25)
    
    # K - Diagonal down
    painter.drawLine(size*0.35, size*0.5, size*0.65, size*0.75)
    
    # 3. Add a small accent
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#f5c2e7"))
    painter.drawEllipse(size*0.65 - 10, size*0.25 - 10, 20, 20)
    painter.drawEllipse(size*0.65 - 10, size*0.75 - 10, 20, 20)
    
    painter.end()
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    assets_dir = os.path.join(project_root, "assets")
    
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
        
    png_path = os.path.join(assets_dir, "icon.png")
    ico_path = os.path.join(assets_dir, "icon.ico")
    
    # Save PNG
    pixmap.save(png_path, "PNG")
    print(f"PNG saved to {png_path}")
    
    # Save ICO using Pillow for Windows Explorer
    img = Image.open(png_path)
    # Windows likes multiple sizes in one .ico
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    print(f"ICO saved to {ico_path}")

if __name__ == "__main__":
    create_premium_icon()
