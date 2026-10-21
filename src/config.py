import os
from pathlib import Path

def data_dir():
    base = os.environ.get('LEADFINDER_DATA_DIR')
    path = Path(base) if base else Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'LeadFinderAI/data'
    path.mkdir(parents=True, exist_ok=True)
    return path
