import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from src.database.store import Store
from src.ui.window import Window
from src.search.rules import Criteria
from src.providers.free_web_search import AuthorizedImport
from src.search.search_engine import SearchEngine

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

def test_navigation_wizard_import_review_export(app,tmp_path):
    store=Store(tmp_path/'ui.db'); window=Window(store); window.show(); app.processEvents()
    assert window.pages.count()==9
    for i in range(9): window.nav.setCurrentRow(i); app.processEvents(); assert window.pages.currentIndex()==i
    window.load_criteria(Criteria(country='India',continent='Asia',roles=['Founder'],city='Pune').dict())
    assert window.criteria().country=='India' and window.wizard.currentIndex()==3
    source=tmp_path/'input.csv'; source.write_text('profile_url,source_url,full_name,designation,country,city\nhttps://linkedin.com/in/test-fixture,https://example.org/evidence,Fixture,Founder,India,Pune\n')
    result=SearchEngine(store).run(window.criteria(),AuthorizedImport(source)); window.refresh()
    assert result['new_leads']==1 and window.stat_labels['total'].text()=='1'
    assert window.lead_table.item(0,4).text()=='Unknown'
    window.db_text.setText('Fixture'); window.filter_leads(); assert window.lead_table.rowCount()==1
    window.theme.setCurrentText('Light'); window.collapse(); window.collapse(); app.processEvents()
    assert store.rows("SELECT value FROM app_settings WHERE key='theme'")[0]['value']=='Light'
    window.close()

def test_background_import_signals(app,tmp_path):
    import time
    from src.workers.tasks import Task
    store=Store(tmp_path/'worker.db')
    source=tmp_path/'input.csv'; source.write_text('profile_url,source_url,full_name,designation,country\nhttps://linkedin.com/in/worker-fixture,https://example.org/evidence,Fixture,Founder,India\n')
    engine=SearchEngine(store); results=[]; progress=[]; errors=[]
    worker=Task(lambda emit:engine.run(Criteria(country='India'),AuthorizedImport(source),emit))
    worker.succeeded.connect(results.append); worker.progress.connect(progress.append); worker.failed.connect(errors.append)
    worker.start(); deadline=time.monotonic()+5
    while not results and not errors and time.monotonic()<deadline:
        app.processEvents(); worker.wait(10)
    worker.wait(1000); app.processEvents()
    assert not errors and results[0]['new_leads']==1 and progress[0]['candidates']==1

def test_manual_division_roundtrip(app,tmp_path):
    window=Window(Store(tmp_path/'division.db'))
    c=Criteria(country='India',continent='Asia',division='Custom district',roles=['Founder'])
    window.load_criteria(c.dict())
    assert window.criteria().division=='Custom district'
    window.division.setCurrentIndex(0)
    assert window.criteria().division==''
    index=window.division.findData('Mahārāshtra')
    window.division.setCurrentIndex(index)
    assert window.criteria().division=='Mahārāshtra'
    window.close()

def test_typed_country_uses_matching_code_and_divisions(app,tmp_path):
    window=Window(Store(tmp_path/'typed-country.db'))
    window.continent.setCurrentText('Asia')
    window.country.setEditText('India')
    assert window.country_code()=='IN'
    assert window.division.findData('Mahārāshtra')>=0
    window.country.setEditText('Not a country')
    assert window.country_code() is None
    with pytest.raises(ValueError): window.criteria()
    window.close()
