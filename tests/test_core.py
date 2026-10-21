import csv
import json
import sqlite3
import threading
import httpx
import pytest
from openpyxl import load_workbook
from src.database.store import Store
from src.search.rules import Criteria, normalize_url, metric_match, queries
from src.search.search_engine import SearchEngine
from src.providers.free_web_search import AuthorizedImport, BrowserSearch
from src.exports.service import export_leads
from src.geography.service import Geography

@pytest.fixture
def store(tmp_path): return Store(tmp_path/'leads.db')
@pytest.fixture
def lead(): return dict(profile_url='https://www.linkedin.com/in/test-person/',source_url='https://example.org/evidence',full_name='Test Person',designation='Founder',country='India')
class Provider:
    name='Synthetic test fixture'
    def __init__(self,rows): self.rows=rows
    def search(self,c): yield from self.rows

def test_schema_persistence(store,lead):
    i=store.add_lead(lead)
    again=Store(store.path)
    assert again.rows('PRAGMA user_version')[0]['user_version']==1
    assert again.rows('SELECT * FROM leads WHERE id=?',(i,))[0]['full_name']=='Test Person'
    assert len(again.rows("SELECT name FROM sqlite_master WHERE type='table'"))==8

def test_newer_schema_rejected(store):
    store.execute('PRAGMA user_version=99')
    with pytest.raises(ValueError): Store(store.path)

def test_country_global_dedup(store,lead):
    assert store.add_lead(lead)
    url=normalize_url(lead['profile_url'])
    assert store.country_exists('India',url)
    assert not store.country_exists('France',url)
    assert store.add_lead(dict(lead,country='France',profile_url=url+'?trk=test')) is None
    assert store.stats()['total']==1
    plan=store.rows('EXPLAIN QUERY PLAN SELECT id FROM leads WHERE country=?',('India',))
    assert 'idx_country' in str(plan)

@pytest.mark.parametrize('url',['https://linkedin.com/in/abc/?trk=foo#detail','https://in.linkedin.com/in/abc','https://www.linkedin.com/in/abc/'])
def test_url_normalization(url): assert normalize_url(url)=='https://www.linkedin.com/in/abc'
@pytest.mark.parametrize('url',['http://linkedin.com/in/abc','https://linkedin.com.evil.org/in/abc','https://user@linkedin.com/in/abc','https://linkedin.com/company/a','https://linkedin.com/in/a/b','javascript:alert(1)','https://linkedin.com:88/in/abc'])
def test_invalid_urls(url):
    with pytest.raises(ValueError): normalize_url(url)

def test_unknown_metrics_and_provenance(store,lead):
    store.add_lead(lead); row=store.list_leads()[0]
    assert row['followers'] is None and row['connections'] is None
    with pytest.raises(ValueError): store.add_lead(dict(lead,followers=100))
    with pytest.raises(ValueError): store.add_lead(dict(lead,followers=-1))

@pytest.mark.parametrize('mode,unknown,expected',[('AND',False,False),('OR',False,True),('Independent',False,True),('AND',True,True)])
def test_metric_rules(mode,unknown,expected):
    c=Criteria(country='India',followers=100,connections=50,mode=mode,include_unknown=unknown)
    assert metric_match(dict(followers=None,connections=60),c)==expected

def test_queries():
    c=Criteria(country='India',roles=['Founder','CEO'],city='Pune',exclusions='recruiter')
    assert len(queries(c))==2 and '-"recruiter"' in queries(c)[0]
    with pytest.raises(ValueError): Criteria().validate()

def test_rerun_and_history(store,lead):
    c=Criteria(country='India')
    first=SearchEngine(store).run(c,Provider([lead]))
    second=SearchEngine(Store(store.path)).run(c,Provider([lead]))
    assert first['new_leads']==1 and second['duplicates']==1
    assert store.rows('SELECT * FROM search_runs')[1]['status']=='Completed'
    assert len(store.rows('SELECT * FROM search_results'))==2

def test_rejection_and_no_invented_geography(store,lead):
    missing=dict(lead); del missing['country']
    result=SearchEngine(store).run(Criteria(country='India'),Provider([missing,dict(lead,profile_url='https://evil.org/a')]))
    assert result['rejected']==2 and store.stats()['total']==0

def test_interruption_recovery(store,lead):
    run=store.start_run(Criteria(country='India'),'test'); store.add_lead(lead,run)
    Store(store.path).recover()
    assert store.rows('SELECT status FROM search_runs')[0]['status']=='Interrupted'
    assert SearchEngine(store).run(Criteria(country='India'),Provider([lead]))['duplicates']==1

def test_cancel_and_pause(store,lead):
    engine=SearchEngine(store); engine.pause(); result=[]
    thread=threading.Thread(target=lambda:result.append(engine.run(Criteria(country='India'),Provider([lead])))); thread.start()
    engine.cancel(); thread.join(timeout=5)
    assert not thread.is_alive() and result[0]['status']=='Cancelled'
    assert store.stats()['total']==0

@pytest.mark.parametrize('exception',[httpx.ReadTimeout('timeout'),httpx.HTTPStatusError('429 rate limit',request=httpx.Request('GET','https://example.org'),response=httpx.Response(429))])
def test_provider_failures(store,exception):
    class Failed:
        name='test failure'
        def search(self,c): raise exception
    result=SearchEngine(store).run(Criteria(country='India'),Failed())
    assert result['status']=='Failed' and result['error']

def test_csv_import(store,lead,tmp_path):
    path=tmp_path/'input.csv'
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=lead); writer.writeheader(); writer.writerow(lead)
    result=SearchEngine(store).run(Criteria(country='India'),AuthorizedImport(path))
    assert result['new_leads']==1
    result=SearchEngine(store).run(Criteria(country='India'),BrowserSearch())
    assert result['status']=='Failed'

@pytest.mark.parametrize('extension',['csv','xlsx'])
def test_export(store,lead,tmp_path,extension):
    store.add_lead(dict(lead,full_name='  =SUM(1,2)'))
    path=tmp_path/f'export.{extension}'; export_leads(store,store.list_leads(),path)
    if extension=='csv':
        with path.open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
        assert rows[0]['full_name'].startswith("'") and rows[0]['followers']==''
    else:
        book=load_workbook(path); sheet=book.active; values=list(sheet.values); row=dict(zip(values[0],values[1]))
        assert row['full_name'].startswith("'") and row['followers'] is None; book.close()
    assert store.list_leads()[0]['exported']==1
    assert store.rows('SELECT count FROM export_history')[0]['count']==1
    with pytest.raises(ValueError): export_leads(store,store.list_leads(),path)

def test_failed_export_does_not_mark(store,lead,tmp_path):
    store.add_lead(lead); path=tmp_path/'exists.csv'; path.write_text('existing')
    with pytest.raises(ValueError): export_leads(store,store.list_leads(),path)
    assert not store.list_leads()[0]['exported'] and path.read_text()=='existing'

def test_verification(store,lead):
    i=store.add_lead(lead)
    with pytest.raises(ValueError): store.review(i,'Verified','')
    store.review(i,'Verified','Manually checked role, identity and location in supplied evidence')
    assert store.list_leads()[0]['verification_status']=='Verified'

def test_backup_restore(store,lead,tmp_path):
    store.add_lead(lead); backup=tmp_path/'backup.db'; store.backup(backup)
    store.execute('DELETE FROM leads'); store.restore(backup)
    assert store.stats()['total']==1
    bad=tmp_path/'bad.db'; bad.write_text('not sqlite')
    with pytest.raises(sqlite3.DatabaseError): store.restore(bad)
    assert store.stats()['total']==1

def test_saved_search(store):
    c=Criteria(country='India'); store.save_search('Founders',c)
    saved=Store(store.path).rows('SELECT * FROM saved_searches')[0]
    assert Criteria(**json.loads(saved['criteria'])).country=='India'

def test_geography_cache_and_offline(store):
    geo=Geography(store)
    assert any(c['iso']=='IN' for c in geo.countries_in('Asia'))
    assert any(name=='Mahārāshtra' for name,kind in geo.divisions('IN'))
    assert geo.cached('IN') is None
    def response(request): return httpx.Response(200,json=[{},[{'value':None,'date':'2025'},{'value':123,'date':'2024'}]])
    with httpx.Client(transport=httpx.MockTransport(response)) as client: data=geo.refresh('IN',client)
    assert data['year']=='2024' and data['source'] and data['refreshed'] and data['license']
    def failure(request): raise httpx.ReadTimeout('offline')
    with httpx.Client(transport=httpx.MockTransport(failure)) as client:
        with pytest.raises(httpx.ReadTimeout): geo.refresh('IN',client)
    assert geo.cached('IN')['population']==123

def test_geography_malformed_response(store):
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'error':'unavailable'}))) as client:
        with pytest.raises(ValueError): Geography(store).refresh('IN',client)

@pytest.mark.parametrize('records',[
    [{'value':123}], [{'value':123,'date':'Unknown'}],
    [{'value':True,'date':'2024'}], [None,{},'bad'],
])
def test_population_requires_numeric_value_and_year(store,records):
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=[{},records]))) as client:
        with pytest.raises(ValueError,match='No dated population'): Geography(store).refresh('IN',client)
    assert Geography(store).cached('IN') is None

def test_population_uses_latest_dated_record(store):
    records=[{'value':100,'date':'2022'},{'value':200,'date':'2024'}]
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=[{},records]))) as client:
        assert Geography(store).refresh('IN',client)['year']=='2024'
