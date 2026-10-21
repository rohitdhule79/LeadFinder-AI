from PySide6.QtCore import QThread, Signal

class Task(QThread):
    succeeded=Signal(object)
    failed=Signal(str)
    progress=Signal(object)
    def __init__(self, function, parent=None):
        super().__init__(parent); self.function=function
    def run(self):
        try: self.succeeded.emit(self.function(self.progress.emit))
        except Exception as exc: self.failed.emit(str(exc))
