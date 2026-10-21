DARK = '''
QWidget { background: #0c1222; color: #e6edf9; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 13px; }
QMainWindow { background: #0c1222; }
QFrame#card { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #202d47,stop:1 #141e33); border: 1px solid #34435f; border-radius: 16px; }
QLabel { background: transparent; }
QLabel#title { font-size: 28px; font-weight: 700; }
QLabel#muted { color: #a6b5cf; }
QLabel#number { font-size: 30px; font-weight: 600; color: #c3d6ff; }
QPushButton { background: #24324d; border: 1px solid #435679; border-radius: 8px; padding: 10px 16px; }
QPushButton:hover { background: #354b70; border-color: #8da7e3; }
QPushButton:pressed { background: #425d88; }
QPushButton:disabled { color: #7c879a; border-color: #2a3448; }
QPushButton#primary { background: #6268cd; color: white; border-color: #9299f0; font-weight: 600; }
QLineEdit, QComboBox, QSpinBox, QTextEdit { background: #121e33; border: 1px solid #3c4e6d; border-radius: 7px; padding: 8px; selection-background-color: #6268cd; }
QComboBox QAbstractItemView { background: #1b2942; selection-background-color: #5367b0; }
QListWidget { background: #101a2d; border: none; border-radius: 10px; outline: 0; }
QListWidget::item { padding: 12px; margin: 3px; border-radius: 8px; }
QListWidget::item:selected { background: #344670; color: #e6eeff; }
QTableWidget { background: #121d31; alternate-background-color: #18243a; border: 1px solid #34435f; border-radius: 10px; gridline-color: #2b3951; selection-background-color: #344e77; }
QHeaderView::section { background: #23324c; color: #bfcde5; border: none; padding: 9px; }
QCheckBox { spacing: 8px; background: transparent; padding: 4px; }
QProgressBar { border: 1px solid #394969; border-radius: 6px; background: #172138; text-align: center; }
QProgressBar::chunk { background: #7e89e8; border-radius: 5px; }
QScrollArea { border: none; }
QToolTip { color: white; background: #34435f; border: 1px solid #7188b4; }
'''
LIGHT = DARK.replace('#0c1222','#eff3fa').replace('#e6edf9','#18253c').replace('#101a2d','#e0e7f4').replace('#121d31','#f9fbff').replace('#18243a','#e8eef8').replace('#121e33','#ffffff').replace('#a6b5cf','#4c6080').replace('#202d47','#e1e9f7').replace('#141e33','#f7f9fe').replace('#c3d6ff','#394c91')

# Explicit control colors keep inherited dark-theme surfaces readable in light mode.
LIGHT += """
QPushButton { background: #e0e7f4; color: #18253c; border-color: #8b9bb5; }
QPushButton:hover { background: #cddaf0; }
QPushButton:pressed { background: #b9c9e5; }
QPushButton:disabled { background: #e9edf4; color: #64748b; }
QPushButton#primary { background: #4e56b4; color: white; }
QComboBox QAbstractItemView { background: white; color: #18253c; selection-background-color: #d1ddf5; selection-color: #18253c; }
QHeaderView::section { background: #dce5f3; color: #263c60; }
QTableWidget { selection-background-color: #cad8f1; selection-color: #18253c; }
QListWidget::item:selected { background: #cad8f1; color: #18253c; }
QProgressBar { background: #dce5f3; color: #18253c; }
"""
