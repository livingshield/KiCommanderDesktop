import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QRadialGradient, QLinearGradient, QFont, QPen, QBrush, QPainterPath
from PySide6.QtCore import Qt, QPointF, QRectF
from PIL import Image

def create_ultra_premium_icon():
    app = QApplication(sys.argv)
    
    size = 512
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 1. Background Rounded Rect with subtle gradient (SaaS style)
    rect = QRectF(20, 20, size-40, size-40)
    path = QPainterPath()
    path.addRoundedRect(rect, 100, 100)
    
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, QColor("#1e1e2e"))
    grad.setColorAt(1, QColor("#11111b"))
    
    painter.fillPath(path, grad)
    
    # Border
    painter.setPen(QPen(QColor("#313244"), 8))
    painter.drawPath(path)
    
    # 2. Main Icon - Minimalist "K" using simple geometric shapes
    # Pure white/blue glow look
    painter.setPen(Qt.NoPen)
    
    # Main vertical bar of K
    k_grad = QLinearGradient(0, size*0.2, 0, size*0.8)
    k_grad.setColorAt(0, QColor("#89b4fa"))
    k_grad.setColorAt(1, QColor("#b4befe"))
    painter.setBrush(k_grad)
    
    # Rect for vertical bar
    v_bar = QRectF(size*0.3, size*0.25, size*0.12, size*0.5)
    v_path = QPainterPath()
    v_path.addRoundedRect(v_bar, 10, 10)
    painter.drawPath(v_path)
    
    # Diagonal bars for K
    # Instead of lines, we use rounded shapes for premium feel
    # Top diagonal
    t_diag_path = QPainterPath()
    t_diag_path.moveTo(size*0.42, size*0.5)
    t_diag_path.lineTo(size*0.65, size*0.25)
    t_diag_path.lineTo(size*0.72, size*0.32)
    t_diag_path.lineTo(size*0.42, size*0.57)
    t_diag_path.closeSubpath()
    painter.drawPath(t_diag_path)
    
    # Bottom diagonal
    b_diag_path = QPainterPath()
    b_diag_path.moveTo(size*0.42, size*0.5)
    b_diag_path.lineTo(size*0.65, size*0.75)
    b_diag_path.lineTo(size*0.72, size*0.68)
    b_diag_path.lineTo(size*0.42, size*0.43)
    b_diag_path.closeSubpath()
    painter.drawPath(b_diag_path)
    
    # 3. Subtle Glow/Accent
    accent_brush = QRadialGradient(size*0.7, size*0.3, size*0.3)
    accent_brush.setColorAt(0, QColor(137, 180, 250, 40))
    accent_brush.setColorAt(1, QColor(137, 180, 250, 0))
    painter.setBrush(accent_brush)
    painter.drawEllipse(size*0.4, size*0.1, size*0.5, size*0.5)
    
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
    print(f"Sleek PNG saved to {png_path}")
    
    # Save ICO using Pillow for Windows Explorer
    img = Image.open(png_path)
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    print(f"Premium ICO saved to {ico_path}")

if __name__ == "__main__":
    create_ultra_premium_icon()
