import csv
import os
import tempfile
from pathlib import Path
from openpyxl import Workbook
from src.database.store import FIELDS, now

EXPORT_FIELDS = ['id'] + FIELDS

def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value

def export_leads(store, leads, destination):
    path = Path(destination)
    if path.suffix.lower() not in ('.csv','.xlsx'): raise ValueError('Choose CSV or XLSX')
    if not leads: raise ValueError('No leads selected')
    if path.exists(): raise ValueError('File exists. Choose a new filename')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=path.suffix)
    os.close(fd)
    try:
        rows = [[safe_cell(row.get(k)) for k in EXPORT_FIELDS] for row in leads]
        if path.suffix.lower() == '.csv':
            with open(tmp,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.writer(stream); writer.writerow(EXPORT_FIELDS); writer.writerows(rows)
        else:
            book=Workbook(); sheet=book.active; sheet.title='Leads'; sheet.append(EXPORT_FIELDS)
            for row in rows: sheet.append(row)
            sheet.freeze_panes='A2'; sheet.auto_filter.ref=sheet.dimensions
            book.save(tmp); book.close()
        # Exclusive creation prevents a race from overwriting an existing export.
        with open(path, 'xb') as output, open(tmp,'rb') as source:
            try:
                import shutil
                shutil.copyfileobj(source,output)
                output.flush(); os.fsync(output.fileno())
            except BaseException:
                output.close(); path.unlink(missing_ok=True); raise
        with store.connect() as db:
            db.executemany('UPDATE leads SET exported=1, updated_at=? WHERE id=?',[(now(),row['id']) for row in leads])
            db.execute('INSERT INTO export_history(path,count,created_at) VALUES(?,?,?)',(str(path.resolve()),len(leads),now()))
        return path
    finally:
        Path(tmp).unlink(missing_ok=True)
