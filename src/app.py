import argparse
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.config import data_dir
from src.database.store import Store
from src.ui.window import Window

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--smoke-test',action='store_true'); parser.add_argument('--screenshot'); args=parser.parse_args()
    app=QApplication(sys.argv[:1]); app.setApplicationName('LeadFinder AI'); store=Store(data_dir()/'leads.db'); store.recover(); window=Window(store); window.show()
    if args.smoke_test:
        def finish():
            for i in range(window.pages.count()): window.nav.setCurrentRow(i); app.processEvents()
            window.nav.setCurrentRow(0); app.processEvents()
            if args.screenshot: window.grab().save(args.screenshot)
            window.close(); app.quit()
        QTimer.singleShot(700,finish)
    return app.exec()
