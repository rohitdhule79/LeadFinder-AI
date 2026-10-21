import csv
import json
import time
from pathlib import Path
from urllib.parse import quote
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QShortcut, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QListWidget, QStackedWidget, QLineEdit, QComboBox, QSpinBox, QCheckBox, QTextEdit, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QFileDialog, QMessageBox, QInputDialog, QProgressBar, QScrollArea)
from src.search.rules import Criteria, ROLES, queries
from src.search.search_engine import SearchEngine
from src.providers.free_web_search import AuthorizedImport
from src.geography.service import Geography, CONTINENTS
from src.exports.service import export_leads
from src.workers.tasks import Task
from src.ui.theme import DARK, LIGHT

PAGES=['Dashboard','Find Leads','Lead Database','Search History','Saved Searches','Exports','Data Sources','Settings','About']

def label(text, style=''):
    w=QLabel(text); w.setWordWrap(True)
    if style: w.setObjectName(style)
    return w

def button(text, callback, primary=False):
    w=QPushButton(text); w.clicked.connect(callback)
    if primary: w.setObjectName('primary')
    return w

def combo(items):
    w=QComboBox(); w.addItems(items); return w

def table(headers):
    w=QTableWidget(0,len(headers)); w.setHorizontalHeaderLabels(headers)
    w.setAlternatingRowColors(True); w.setSelectionBehavior(QAbstractItemView.SelectRows)
    w.setEditTriggers(QAbstractItemView.NoEditTriggers)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    w.verticalHeader().hide(); return w

def fill(w, rows, keys):
    w.setSortingEnabled(False); w.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,key in enumerate(keys):
            value=row.get(key)
            item=QTableWidgetItem('Unknown' if value is None else str(value)); item.setData(Qt.UserRole,row.get('id'))
            w.setItem(i,j,item)

class Window(QMainWindow):
    def __init__(self, store):
        super().__init__(); self.store=store; self.geo=Geography(store); self.tasks=[]; self.engine=None; self.offset=0; self.step=0
        self.setWindowTitle('LeadFinder AI'); self.resize(1380,900); self.setMinimumSize(980,680)
        self.setStyleSheet(DARK)
        root=QWidget(); self.setCentralWidget(root); outer=QHBoxLayout(root); outer.setContentsMargins(16,16,16,16); outer.setSpacing(20)
        rail=QVBoxLayout(); self.brand=label('◈  LEADFINDER\n     AI WORKSPACE'); self.brand.setStyleSheet('font-size:18px;font-weight:700;'); rail.addWidget(self.brand)
        rail.addWidget(label('LOCAL FIRST  /  PRIVATE BY DEFAULT','muted'))
        self.nav=QListWidget(); self.nav.addItems(PAGES); self.nav.setFixedWidth(210); self.nav.currentRowChanged.connect(self.navigate); rail.addWidget(self.nav)
        rail.addWidget(button('☰  Collapse sidebar', self.collapse)); rail.addWidget(label('Your data. Your machine.\nNo account required.','muted')); outer.addLayout(rail)
        content=QVBoxLayout(); outer.addLayout(content,1)
        header=QHBoxLayout(); self.heading=label('Dashboard','title'); header.addWidget(self.heading); header.addStretch()
        self.command=QLineEdit(); self.command.setPlaceholderText('Search leads…  Ctrl+K'); self.command.returnPressed.connect(self.global_search); header.addWidget(self.command)
        content.addLayout(header); content.addWidget(label('Discover thoughtfully. Review the evidence. Build lasting connections.','muted'))
        self.pages=QStackedWidget(); content.addWidget(self.pages,1)
        self.build_dashboard(); self.build_wizard(); self.build_database(); self.build_history(); self.build_saved(); self.build_exports(); self.build_sources(); self.build_settings(); self.build_about()
        self.status=label('Ready • SQLite local storage • No automatic profile scraping','muted'); content.addWidget(self.status)
        QShortcut(QKeySequence('Ctrl+K'), self, activated=self.command.setFocus)
        self.nav.setCurrentRow(0); self.refresh()

    def page(self):
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(4,12,4,4); layout.setSpacing(14)
        self.pages.addWidget(page); return layout

    def card(self, title, description=''):
        frame=QFrame(); frame.setObjectName('card'); lay=QVBoxLayout(frame); lay.setContentsMargins(20,18,20,18)
        lay.addWidget(label(title,'title'))
        if description: lay.addWidget(label(description,'muted'))
        return frame,lay

    def notify(self, text): self.status.setText(text)
    def error(self, exc): QMessageBox.warning(self,'LeadFinder AI',str(exc)); self.notify(str(exc))
    def safe(self, action):
        try: return action()
        except Exception as exc: self.error(exc)

    def navigate(self, index):
        if index<0: return
        self.pages.setCurrentIndex(index); self.heading.setText(PAGES[index]); self.refresh()

    def collapse(self):
        small=self.nav.width()>100; self.nav.setFixedWidth(70 if small else 210)
        for i,name in enumerate(PAGES):
            self.nav.item(i).setText(name[:2] if small else name); self.nav.item(i).setToolTip(name)
        self.brand.setText('◈' if small else '◈  LEADFINDER\n     AI WORKSPACE')

    def global_search(self):
        self.db_text.setText(self.command.text()); self.nav.setCurrentRow(2); self.reload_leads()

    def build_dashboard(self):
        lay=self.page(); frame,card=self.card('A clearer view of your next opportunity','Public profile discovery, with a permanent local memory.'); actions=QHBoxLayout()
        actions.addWidget(button('Find new leads  →',lambda:self.nav.setCurrentRow(1),True)); actions.addWidget(button('Open lead database',lambda:self.nav.setCurrentRow(2))); actions.addStretch(); card.addLayout(actions); lay.addWidget(frame)
        stats=QHBoxLayout(); self.stat_labels={}
        for key,title in [('total','Unique leads'),('today','Discovered today'),('verified','Verified'),('exported','Exported'),('countries','Countries')]:
            f=QFrame(); f.setObjectName('card'); v=QVBoxLayout(f); v.addWidget(label(title,'muted')); n=label('0','number'); self.stat_labels[key]=n; v.addWidget(n); stats.addWidget(f)
        lay.addLayout(stats); lay.addWidget(label('Recent search activity','title'))
        self.recent=table(['Started','Country criteria','Status','New']); lay.addWidget(self.recent,1)
        lay.addWidget(label('Recently discovered','title')); self.preview=table(['Name','Role','Country','Review']); lay.addWidget(self.preview,1)
        lay.addWidget(label('Source status: manual browser search + authorized CSV import. No live search API connected.','muted'))

    def build_wizard(self):
        lay=self.page(); self.steps=label('01  Geography     /     02  Audience     /     03  Requirements     /     04  Review','muted'); lay.addWidget(self.steps)
        self.wizard=QStackedWidget(); lay.addWidget(self.wizard,1)
        def step(title,desc):
            f,v=self.card(title,desc); scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(f); self.wizard.addWidget(scroll); return v
        v=step('Where is your audience?','Country assignments follow GeoNames continent codes. Territories are retained; each entry has one assigned continent.')
        self.continent=combo(list(CONTINENTS.values())); self.country=QComboBox(); self.country.setEditable(True); self.country.setInsertPolicy(QComboBox.NoInsert); self.country.completer().setFilterMode(Qt.MatchContains)
        self.division=QComboBox(); self.division.setEditable(True); self.division.setInsertPolicy(QComboBox.NoInsert); self.city=QLineEdit(); self.city.setPlaceholderText('Optional city')
        for title,w in [('Continent',self.continent),('Country / territory',self.country),('Administrative division (local type shown)',self.division),('City',self.city)]: v.addWidget(label(title,'muted')); v.addWidget(w)
        self.population=label('Population unavailable. Refresh to retrieve dated World Bank data.','muted'); v.addWidget(self.population); v.addWidget(button('Refresh population',self.refresh_population)); v.addStretch()
        self.continent.currentTextChanged.connect(self.populate_countries); self.country.currentTextChanged.connect(self.populate_divisions); self.populate_countries()
        v=step('Who would you like to meet?','Select one or more titles. Text matches remain unverified until reviewed.')
        self.roles=QListWidget(); self.roles.setSelectionMode(QAbstractItemView.MultiSelection); self.roles.addItems(ROLES); self.roles.item(0).setSelected(True); v.addWidget(self.roles)
        self.custom=QLineEdit(); self.custom.setPlaceholderText('Custom titles, comma separated'); self.keywords=QLineEdit(); self.keywords.setPlaceholderText('Company or industry keywords'); self.exclusions=QLineEdit(); self.exclusions.setPlaceholderText('Excluded words, comma separated')
        for w in (self.custom,self.keywords,self.exclusions): v.addWidget(w)
        v=step('Set your qualification rules','Minimum metrics apply only to sourced, dated observations. Independent mode accepts either active threshold, like OR; AND requires every active threshold.')
        self.target=QSpinBox(); self.target.setRange(1,10000); self.target.setValue(25)
        self.followers=QSpinBox(); self.followers.setRange(0,1000000000); self.connections=QSpinBox(); self.connections.setRange(0,1000000000)
        self.mode=combo(['AND','OR','Independent']); self.unknown=QCheckBox('Include unknown metrics separately (explicitly permits unknown threshold values)')
        self.existing=QCheckBox('Exclude previously discovered leads'); self.existing.setChecked(True); self.existing.setEnabled(False); self.existing.setToolTip('Permanent uniqueness always preserves existing records. Use the database to review or export them.')
        self.company=QLineEdit(); self.industry=QLineEdit()
        for title,w in [('New lead target (not guaranteed)',self.target),('Minimum followers (0 = no filter)',self.followers),('Minimum connections (0 = no filter)',self.connections),('Metric rule',self.mode),('Company',self.company),('Industry',self.industry)]: v.addWidget(label(title,'muted')); v.addWidget(w)
        v.addWidget(self.unknown); v.addWidget(self.existing); v.addStretch()
        v=step('Review & discover','No free automated search provider has been approved. Open a query in your browser, then import a CSV you are authorized to use. No profiles are fetched by this app.')
        self.summary=QTextEdit(); self.summary.setReadOnly(True); v.addWidget(self.summary)
        self.query_box=QComboBox(); v.addWidget(self.query_box)
        row=QHBoxLayout(); row.addWidget(button('Open query in browser',self.open_query)); row.addWidget(button('Import authorized CSV / Start',self.start_import,True)); row.addWidget(button('Save search',self.save_search)); v.addLayout(row)
        self.progress=QProgressBar(); self.progress.setRange(0,1); self.progress.setValue(0); v.addWidget(self.progress)
        self.progress_text=label('No search running. Imported records will be marked Needs Review.','muted'); v.addWidget(self.progress_text)
        row=QHBoxLayout(); self.pause_btn=button('Pause',self.pause); self.cancel_btn=button('Cancel running import',self.cancel); row.addWidget(self.pause_btn); row.addWidget(self.cancel_btn); v.addLayout(row); self.pause_btn.setEnabled(False); self.cancel_btn.setEnabled(False)
        row=QHBoxLayout(); row.addWidget(button('Back',lambda:self.change_step(-1))); row.addStretch(); row.addWidget(button('Cancel wizard',lambda:self.nav.setCurrentRow(0))); row.addWidget(button('Continue  →',lambda:self.change_step(1),True)); lay.addLayout(row)

    def populate_countries(self):
        self.country.clear()
        for c in self.geo.countries_in(self.continent.currentText()): self.country.addItem(c['name'],c['iso'])

    def country_code(self):
        index=self.country.findText(self.country.currentText(), Qt.MatchExactly)
        return self.country.itemData(index) if index>=0 else None

    def populate_divisions(self):
        self.division.clear(); self.division.addItem('Any division','')
        code=self.country_code()
        if code:
            for name,kind in self.geo.divisions(code): self.division.addItem(f'{name} ({kind})',name)
        self.show_population(self.geo.cached(code) if code else None)

    def show_population(self,data):
        self.population.setText(f"Population {data['population']:,} • {data['year']} • {data['source']}\nRefreshed {data['refreshed']} • {data['license']}" if data else 'Population unavailable. Refresh or retry later; no estimate is displayed.')

    def refresh_population(self):
        code=self.country_code()
        if not code: return self.error('Select a supported country')
        self.notify('Refreshing population…')
        self.task(lambda _:self.geo.refresh(code),lambda data:self.show_population(data) if self.country_code()==code else None)

    def criteria(self):
        if self.country.findText(self.country.currentText())<0: raise ValueError('Select a supported country')
        division_text=self.division.currentText().strip()
        division_index=self.division.findText(division_text, Qt.MatchExactly)
        division=self.division.itemData(division_index) if division_index>=0 else division_text
        return Criteria(country=self.country.currentText(),continent=self.continent.currentText(),division=division or '',city=self.city.text().strip(),roles=[i.text() for i in self.roles.selectedItems()]+[s.strip() for s in self.custom.text().split(',') if s.strip()],keywords=self.keywords.text().strip(),exclusions=self.exclusions.text().strip(),company=self.company.text().strip(),industry=self.industry.text().strip(),target=self.target.value(),followers=self.followers.value(),connections=self.connections.value(),mode=self.mode.currentText(),include_unknown=self.unknown.isChecked()).validate()

    def change_step(self,delta):
        def run():
            c=self.criteria(); self.step=max(0,min(3,self.step+delta)); self.wizard.setCurrentIndex(self.step)
            self.steps.setText(f'Step {self.step+1} of 4  •  '+['Geography','Audience','Requirements','Review'][self.step])
            self.summary.setPlainText(json.dumps(c.dict(),indent=2)); self.query_box.clear(); self.query_box.addItems(queries(c))
        self.safe(run)

    def open_query(self):
        if self.query_box.currentText():
            if not QDesktopServices.openUrl(QUrl('https://www.google.com/search?q='+quote(self.query_box.currentText()))):
                self.error('Could not open a browser. Copy the generated query into your browser manually.')

    def save_search(self):
        def run():
            c=self.criteria(); name,ok=QInputDialog.getText(self,'Save search','Name')
            if ok and name.strip(): self.store.save_search(name.strip(),c); self.refresh(); self.notify('Search saved')
        self.safe(run)

    def task(self,fn,callback):
        worker=Task(fn,self); self.tasks.append(worker); worker.succeeded.connect(callback); worker.failed.connect(self.error); worker.finished.connect(lambda:self.tasks.remove(worker)); worker.start(); return worker

    def start_import(self):
        def run():
            if self.engine: raise ValueError('An import is already running')
            c=self.criteria(); path,_=QFileDialog.getOpenFileName(self,'Import results you are authorized to use','','CSV (*.csv)')
            if not path: return
            self.engine=SearchEngine(self.store); self.started=time.monotonic(); self.paused=False
            self.progress.setRange(0,0); self.pause_btn.setEnabled(True); self.cancel_btn.setEnabled(True)
            worker=self.task(lambda progress:self.engine.run(c,AuthorizedImport(path),progress),self.import_done); worker.progress.connect(self.import_progress)
        self.safe(run)

    def import_progress(self,counts):
        self.progress_text.setText(f"{counts['candidates']} candidates • {counts['new_leads']} new / needs review • {counts['duplicates']} duplicates • {counts['rejected']} rejected • {int(time.monotonic()-self.started)}s")

    def import_done(self,result):
        self.engine=None; self.progress.setRange(0,1); self.progress.setValue(1); self.pause_btn.setEnabled(False); self.cancel_btn.setEnabled(False); self.pause_btn.setText('Pause')
        self.progress_text.setText(f"{result['status']}: {result['new_leads']} new leads needing review; {result['duplicates']} duplicates; {result['rejected']} rejected. {result['error']}"); self.refresh()

    def pause(self):
        if self.engine:
            self.paused=not self.paused; self.engine.pause() if self.paused else self.engine.resume(); self.pause_btn.setText('Resume' if self.paused else 'Pause')
    def cancel(self):
        if self.engine: self.engine.cancel()

    def build_database(self):
        lay=self.page(); row=QHBoxLayout(); self.db_text=QLineEdit(); self.db_text.setPlaceholderText('Search name, company or URL'); self.db_country=QLineEdit(); self.db_country.setPlaceholderText('Country (exact)'); self.db_role=QLineEdit(); self.db_role.setPlaceholderText('Role contains')
        for w in (self.db_text,self.db_country,self.db_role): row.addWidget(w)
        lay.addLayout(row); row=QHBoxLayout(); self.db_status=combo(['Any verification','Verified','Unverified']); self.db_metric=combo(['Any metrics','Known','Unknown']); self.db_sort=combo(['Newest','Oldest','Name','Country']); self.db_start=QLineEdit(); self.db_start.setPlaceholderText('From YYYY-MM-DD'); self.db_end=QLineEdit(); self.db_end.setPlaceholderText('Through YYYY-MM-DD')
        for w in (self.db_status,self.db_metric,self.db_sort,self.db_start,self.db_end): row.addWidget(w)
        row.addWidget(button('Apply filters',self.filter_leads)); lay.addLayout(row)
        self.lead_table=table(['Name','Role','Company','Country','Followers','Connections','Review']); self.lead_table.itemDoubleClicked.connect(lambda _:self.details()); lay.addWidget(self.lead_table,1)
        row=QHBoxLayout()
        for title,fn in [('Details / review',self.details),('Delete selected',self.delete_selected),('Export selected',lambda:self.export('selected')),('Export all matching',lambda:self.export('matching')),('Verified only',lambda:self.export('verified')),('Unexported only',lambda:self.export('new'))]: row.addWidget(button(title,fn))
        lay.addLayout(row); row=QHBoxLayout(); row.addWidget(button('← Previous',lambda:self.page_leads(-1))); self.page_label=label('Page 1','muted'); row.addWidget(self.page_label); row.addStretch(); row.addWidget(button('Next →',lambda:self.page_leads(1))); lay.addLayout(row)

    def filter_leads(self): self.offset=0; self.safe(self.reload_leads)
    def page_leads(self,direction): self.offset=max(0,self.offset+direction*100); self.safe(self.reload_leads)
    def matching(self,limit=100,offset=None):
        return self.store.list_leads(self.db_text.text(),self.db_country.text(),self.db_status.currentText() if self.db_status.currentIndex() else '',self.offset if offset is None else offset,limit,self.db_role.text(),self.db_metric.currentText() if self.db_metric.currentIndex() else '',self.db_start.text(),self.db_end.text()+'T23:59:59.999999+00:00' if self.db_end.text() else '',['id DESC','id ASC','full_name ASC','country ASC'][self.db_sort.currentIndex()])
    def reload_leads(self):
        self.lead_rows=self.matching(); fill(self.lead_table,self.lead_rows,['full_name','designation','company','country','followers','connections','review_status']); self.page_label.setText(f'Page {self.offset//100+1} • {len(self.lead_rows)} shown')
    def selected(self):
        return [self.lead_rows[i.row()] for i in self.lead_table.selectionModel().selectedRows()]

    def details(self):
        def run():
            rows=self.selected()
            if len(rows)!=1: raise ValueError('Select one lead')
            lead=rows[0]
            from PySide6.QtWidgets import QDialog
            dialog=QDialog(self); dialog.setWindowTitle('Lead evidence & review'); dialog.resize(650,650); lay=QVBoxLayout(dialog)
            text=QTextEdit(); text.setReadOnly(True); text.setPlainText('\n'.join(f'{k}: {v if v is not None else "Unknown"}' for k,v in lead.items())); lay.addWidget(text)
            notes=QTextEdit(); notes.setPlaceholderText('Reviewer evidence and notes. Verification means a manual identity/role/location check, not verified metrics.'); notes.setPlainText(lead.get('notes') or ''); lay.addWidget(notes)
            review=combo(['Needs Review','Verified','Rejected']); review.setCurrentText(lead['review_status']); lay.addWidget(review)
            def save():
                def action(): self.store.review(lead['id'],review.currentText(),notes.toPlainText()); dialog.accept(); self.refresh()
                self.safe(action)
            lay.addWidget(button('Edit identity / company fields',lambda:self.edit_lead(lead,dialog))); lay.addWidget(button('Save review',save,True)); lay.addWidget(button('Open public profile',lambda:QDesktopServices.openUrl(QUrl(lead['profile_url'])))); dialog.exec()
        self.safe(run)

    def edit_lead(self,lead,detail_dialog):
        from PySide6.QtWidgets import QDialog, QFormLayout
        dialog=QDialog(self); dialog.setWindowTitle('Edit lead • resets verification'); form=QFormLayout(dialog); fields={}
        for key in ('full_name','designation','company','industry','country','continent','division','city'):
            fields[key]=QLineEdit(lead.get(key) or ''); form.addRow(key.replace('_',' ').title(),fields[key])
        def commit():
            def action():
                self.store.edit(lead['id'],{key:widget.text().strip() for key,widget in fields.items()}); dialog.accept(); detail_dialog.accept(); self.refresh()
            self.safe(action)
        form.addRow(button('Save changes',commit,True)); dialog.exec()

    def delete_selected(self):
        rows=self.selected()
        if rows and QMessageBox.question(self,'Delete leads',f'Delete {len(rows)} leads? Their permanent deduplication records will also be removed.')==QMessageBox.Yes:
            with self.store.connect() as db: db.executemany('DELETE FROM leads WHERE id=?',[(r['id'],) for r in rows])
            self.refresh()

    def export(self,mode):
        def run():
            rows=self.selected() if mode=='selected' else self.matching(100000,0)
            if mode=='verified': rows=[r for r in rows if r['verification_status']=='Verified']
            if mode=='new': rows=[r for r in rows if not r['exported']]
            if not rows: raise ValueError('No matching leads')
            path,_=QFileDialog.getSaveFileName(self,f'Export {len(rows)} leads (100,000 maximum per file)','leads.csv','CSV (*.csv);;Excel (*.xlsx)')
            if path: export_leads(self.store,rows,path); self.refresh(); self.notify(f'Exported {len(rows)} leads to {path}')
        self.safe(run)

    def build_history(self):
        lay=self.page(); lay.addWidget(label('Every run has a record. Interrupted imports can be rerun safely.','muted')); self.history=table(['Started','Provider','Status','Candidates','New','Duplicates','Rejected','Error']); lay.addWidget(self.history)
        lay.addWidget(button('Inspect selected run results',self.run_results)); lay.addWidget(button('Rerun selected criteria',self.rerun_history))
    def run_results(self):
        selected=self.history.selectionModel().selectedRows()
        if not selected: return
        run=self.history_rows[selected[0].row()]
        results=self.store.rows('SELECT * FROM search_results WHERE run_id=? ORDER BY id LIMIT 500',(run['id'],))
        box=QMessageBox(self); box.setWindowTitle('Run results (first 500)'); box.setText(f"{run['status']} • {run['candidates']} candidates"); box.setDetailedText('\n'.join(f"{r['outcome']}: {r['profile_url']} — {r['reason']}" for r in results)); box.exec()
    def rerun_history(self):
        selected=self.history.selectionModel().selectedRows()
        if selected: self.load_criteria(json.loads(self.history_rows[selected[0].row()]['criteria']))

    def build_saved(self):
        lay=self.page(); self.saved=table(['Name','Created']); lay.addWidget(self.saved); lay.addWidget(button('Load selected search',self.load_saved)); lay.addWidget(button('Delete selected saved search',self.delete_saved))
    def load_saved(self):
        selected=self.saved.selectionModel().selectedRows()
        if selected: self.load_criteria(json.loads(self.saved_rows[selected[0].row()]['criteria']))
    def delete_saved(self):
        selected=self.saved.selectionModel().selectedRows()
        if selected and QMessageBox.question(self,'Delete saved search','Delete this saved configuration?')==QMessageBox.Yes:
            self.store.execute('DELETE FROM saved_searches WHERE id=?',(self.saved_rows[selected[0].row()]['id'],)); self.refresh()
    def load_criteria(self,data):
        c=Criteria(**data); self.continent.setCurrentText(c.continent); self.country.setCurrentIndex(self.country.findText(c.country, Qt.MatchExactly))
        idx=self.division.findData(c.division)
        if idx>=0:self.division.setCurrentIndex(idx)
        else:self.division.setEditText(c.division)
        for key in ('city','keywords','exclusions','company','industry'): getattr(self,key).setText(getattr(c,key))
        for key in ('target','followers','connections'): getattr(self,key).setValue(getattr(c,key))
        self.mode.setCurrentText(c.mode); self.unknown.setChecked(c.include_unknown)
        for i in range(self.roles.count()): self.roles.item(i).setSelected(self.roles.item(i).text() in c.roles)
        self.custom.setText(', '.join(r for r in c.roles if r not in ROLES)); self.step=2; self.change_step(1); self.nav.setCurrentRow(1)

    def build_exports(self):
        lay=self.page(); lay.addWidget(label('Files are recorded only after a successful write. Existing files are never overwritten.','muted')); self.exports=table(['Created','Count','Path']); lay.addWidget(self.exports); lay.addWidget(button('Open selected export folder',self.open_export))
    def open_export(self):
        selected=self.exports.selectionModel().selectedRows()
        if selected: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.export_rows[selected[0].row()]['path']).parent)))

    def build_sources(self):
        lay=self.page(); frame,v=self.card('Transparent by design','No paid API, account cookies, or undocumented scraping endpoints.'); lay.addWidget(frame)
        v.addWidget(label('Browser search • Manual\nOpens a prefilled query in your default browser. Your browser interacts directly with that provider under its terms. No automated search connection is claimed.'))
        v.addWidget(label('Authorized CSV • Available locally\nRequired columns: profile_url, source_url. Recommended: full_name, designation, country. Optional: company, industry, division, city, followers, connections, metric_source, metric_observed_at, snippet. Metrics need a source and ISO date. All imports require review.'))
        v.addWidget(button('Save blank import template',self.template))
        v.addWidget(label('World Bank population • Optional network refresh\nDated observations are cached locally. HTTP failures retain the last good cache. Geography names work offline.'))
        lay.addStretch()
    def template(self):
        path,_=QFileDialog.getSaveFileName(self,'Save blank CSV template','import-template.csv','CSV (*.csv)')
        if path:
            def write():
                with open(path,'x',encoding='utf-8',newline='') as f: csv.writer(f).writerow(['profile_url','source_url','full_name','designation','country','company','industry','continent','division','city','followers','connections','metric_source','metric_observed_at','snippet'])
                self.notify('Blank template saved')
            self.safe(write)

    def build_settings(self):
        lay=self.page(); frame,v=self.card('Your workspace, your rules',f'Local database: {self.store.path}'); lay.addWidget(frame)
        self.theme=combo(['Dark','Light']); self.theme.currentTextChanged.connect(self.change_theme); v.addWidget(label('Appearance','muted')); v.addWidget(self.theme)
        v.addWidget(label('Static glass gradients provide a portable fallback. No unsupported OS blur APIs or animations are used.','muted'))
        v.addWidget(button('Check database integrity',lambda:self.notify('Database integrity: '+self.store.rows('PRAGMA integrity_check')[0]['integrity_check'])))
        v.addWidget(button('Back up database',self.backup)); v.addWidget(button('Restore backup',self.restore)); v.addWidget(button('Open local data folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.path.parent)))))
        v.addWidget(label('Retention: records remain until explicitly deleted. Export defaults: CSV, UTF-8 BOM, no overwrite. Network pacing: no automated search requests; population refresh is a single, user-triggered request.','muted'))
        v.addWidget(button('Delete all lead data',self.delete_all)); lay.addStretch()
        saved=self.store.rows("SELECT value FROM app_settings WHERE key='theme'")
        if saved:self.theme.setCurrentText(saved[0]['value'])
    def change_theme(self,value):
        self.setStyleSheet(LIGHT if value=='Light' else DARK); self.store.execute("INSERT INTO app_settings(key,value) VALUES('theme',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(value,))
    def backup(self):
        path,_=QFileDialog.getSaveFileName(self,'Back up to a new file','leadfinder-backup.db','SQLite (*.db)')
        if path:self.safe(lambda:(self.store.backup(path),self.notify('Backup saved')))
    def restore(self):
        if self.engine or self.tasks: return self.error('Wait for background work to finish before restoring')
        path,_=QFileDialog.getOpenFileName(self,'Restore SQLite backup','','SQLite (*.db)')
        if path and QMessageBox.question(self,'Restore backup','Replace the current database? A safety backup will be retained.')==QMessageBox.Yes:
            self.safe(lambda:(self.store.restore(path),self.refresh(),self.notify('Database restored')))
    def delete_all(self):
        if self.engine: return self.error('Stop the running import first')
        if QMessageBox.question(self,'Delete all lead data','Delete all leads and search result records? Make a backup first. Saved searches and history remain.')==QMessageBox.Yes:
            with self.store.connect() as db: db.execute('DELETE FROM search_results'); db.execute('DELETE FROM leads')
            self.refresh()
    def build_about(self):
        lay=self.page(); f,v=self.card('LeadFinder AI','A local-first workspace for evidence-led professional discovery.'); lay.addWidget(f)
        v.addWidget(label('Manual verification confirms the reviewer checked identity, role and geography against recorded evidence. It does not independently certify metrics or guarantee that a profile is current.'))
        v.addWidget(label('No fake leads. No guaranteed search volume. No account automation.\n\nGeography: GeoNames country/continent assignments (CC BY 4.0 data), including territories and a single assignment for transcontinental entries. Names/divisions: pycountry / Debian iso-codes (LGPL dataset). Population: World Bank SP.POP.TOTL, source year and refresh timestamp required. See LICENSES.md for sources and dependency licenses.\n\nWindows packaging must be performed and tested on Windows.'))
        lay.addStretch()

    def refresh(self):
        if not hasattr(self,'lead_table'): return
        stats=self.store.stats()
        for key,w in self.stat_labels.items(): w.setText(str(stats[key] or 0))
        self.history_rows=self.store.rows('SELECT * FROM search_runs ORDER BY id DESC LIMIT 500')
        fill(self.history,self.history_rows,['started_at','provider','status','candidates','new_leads','duplicates','rejected','errors'])
        fill(self.recent,[dict(row,country=json.loads(row['criteria']).get('country','')) for row in self.history_rows[:5]],['started_at','country','status','new_leads'])
        fill(self.preview,self.store.list_leads(limit=5),['full_name','designation','country','review_status'])
        self.saved_rows=self.store.rows('SELECT * FROM saved_searches ORDER BY id DESC'); fill(self.saved,self.saved_rows,['name','created_at'])
        self.export_rows=self.store.rows('SELECT * FROM export_history ORDER BY id DESC LIMIT 500'); fill(self.exports,self.export_rows,['created_at','count','path']); self.reload_leads()

    def closeEvent(self,event):
        if any(t.isRunning() for t in self.tasks):
            self.error('Background work is running. Cancel the import or wait for population refresh before closing.'); event.ignore()
        else: event.accept()
