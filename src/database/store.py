import json
from contextlib import contextmanager
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from src.search.rules import normalize_url

def now():
    return datetime.now(timezone.utc).isoformat()

FIELDS = ('full_name designation company industry country continent division city profile_url followers connections metric_source metric_observed_at discovery_source source_url snippet first_discovered last_checked verification_status review_status exported search_run_id notes created_at updated_at').split()

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version > 1:
                raise ValueError('Database version is newer than this application')
            db.executescript('''
            CREATE TABLE IF NOT EXISTS search_runs(id INTEGER PRIMARY KEY, criteria TEXT NOT NULL, provider TEXT, status TEXT, started_at TEXT, ended_at TEXT, candidates INTEGER DEFAULT 0, new_leads INTEGER DEFAULT 0, duplicates INTEGER DEFAULT 0, rejected INTEGER DEFAULT 0, errors TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY, full_name TEXT, designation TEXT, company TEXT, industry TEXT, country TEXT, continent TEXT, division TEXT, city TEXT, profile_url TEXT NOT NULL UNIQUE, followers INTEGER CHECK(followers IS NULL OR followers>=0), connections INTEGER CHECK(connections IS NULL OR connections>=0), metric_source TEXT, metric_observed_at TEXT, discovery_source TEXT, source_url TEXT NOT NULL, snippet TEXT, first_discovered TEXT, last_checked TEXT, verification_status TEXT DEFAULT 'Unverified', review_status TEXT DEFAULT 'Needs Review', exported INTEGER DEFAULT 0, search_run_id INTEGER REFERENCES search_runs(id), notes TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS search_results(id INTEGER PRIMARY KEY, run_id INTEGER REFERENCES search_runs(id), lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL, profile_url TEXT, outcome TEXT, reason TEXT);
            CREATE TABLE IF NOT EXISTS saved_searches(id INTEGER PRIMARY KEY, name TEXT, criteria TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS export_history(id INTEGER PRIMARY KEY, path TEXT, count INTEGER, created_at TEXT);
            CREATE TABLE IF NOT EXISTS data_sources(id INTEGER PRIMARY KEY, name TEXT UNIQUE, status TEXT, details TEXT);
            CREATE TABLE IF NOT EXISTS geographic_data_metadata(id INTEGER PRIMARY KEY, country TEXT UNIQUE, payload TEXT);
            CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY, value TEXT);
            CREATE INDEX IF NOT EXISTS idx_country ON leads(country);
            CREATE INDEX IF NOT EXISTS idx_designation ON leads(designation);
            CREATE INDEX IF NOT EXISTS idx_company ON leads(company);
            CREATE INDEX IF NOT EXISTS idx_verification ON leads(verification_status);
            CREATE INDEX IF NOT EXISTS idx_discovered ON leads(first_discovered);
            PRAGMA user_version=1;
            ''')
            db.execute("INSERT OR IGNORE INTO data_sources(name,status,details) VALUES(?,?,?)", ('Browser + authorized CSV', 'Manual', 'No automated profile requests'))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def rows(self, sql, args=()):
        with self.connect() as db:
            return [dict(r) for r in db.execute(sql, args)]

    def execute(self, sql, args=()):
        with self.connect() as db:
            return db.execute(sql, args).lastrowid

    def recover(self):
        self.execute("UPDATE search_runs SET status='Interrupted', ended_at=? WHERE status IN ('Running','Paused')", (now(),))

    def start_run(self, c, provider):
        return self.execute('INSERT INTO search_runs(criteria,provider,status,started_at) VALUES(?,?,?,?)', (json.dumps(c.dict()), provider, 'Running', now()))

    def country_exists(self, country, url):
        return bool(self.rows('SELECT id FROM leads WHERE country=? AND profile_url=?', (country, url)))

    def add_lead(self, value, run_id=None):
        lead = {k: value.get(k) or None for k in FIELDS}
        lead['profile_url'] = normalize_url(value.get('profile_url', ''))
        source = urlsplit(lead['source_url'] or '')
        if source.scheme != 'https' or not source.hostname or source.username or source.password:
            raise ValueError('A valid HTTPS source URL is required')
        for key in ('followers', 'connections'):
            raw = value.get(key)
            lead[key] = None if raw in (None, '', 'Unknown') else int(raw)
            if lead[key] is not None and lead[key] < 0:
                raise ValueError('Negative metric')
        if any(lead[k] is not None for k in ('followers', 'connections')):
            if not lead['metric_source'] or not lead['metric_observed_at']:
                raise ValueError('Metrics require source and ISO observation date')
            datetime.fromisoformat(lead['metric_observed_at'])
        stamp = now()
        lead.update(first_discovered=stamp, created_at=stamp, updated_at=stamp, last_checked=None,
                    search_run_id=run_id, exported=0, verification_status='Unverified', review_status='Needs Review')
        with self.connect() as db:
            cur = db.execute(f"INSERT INTO leads({','.join(FIELDS)}) VALUES({','.join('?' for _ in FIELDS)}) ON CONFLICT(profile_url) DO NOTHING", [lead[k] for k in FIELDS])
            return cur.lastrowid if cur.rowcount else None

    def list_leads(self, text='', country='', status='', offset=0, limit=100, role='', metrics='', start='', end='', sort='id DESC'):
        where, args = ['1=1'], []
        for column, val, op in [('country',country,'='),('verification_status',status,'='),('designation',role,'LIKE'),('first_discovered',start,'>='),('first_discovered',end,'<=')]:
            if val:
                where.append(f'{column} {op} ?'); args.append('%'+val+'%' if op=='LIKE' else val)
        if text:
            where.append('(full_name LIKE ? OR company LIKE ? OR profile_url LIKE ?)'); args += ['%'+text+'%']*3
        if metrics == 'Known': where.append('(followers IS NOT NULL OR connections IS NOT NULL)')
        if metrics == 'Unknown': where.append('(followers IS NULL AND connections IS NULL)')
        order = sort if sort in ('id DESC','id ASC','full_name ASC','country ASC') else 'id DESC'
        return self.rows(f"SELECT * FROM leads WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?", args+[limit,offset])

    def stats(self):
        return self.rows("SELECT COUNT(*) total, SUM(substr(first_discovered,1,10)=?) today, SUM(verification_status='Verified') verified, SUM(exported=1) exported, COUNT(DISTINCT country) countries FROM leads", (now()[:10],))[0]

    def review(self, lead_id, status, notes):
        if status not in ('Verified', 'Needs Review', 'Rejected'):
            raise ValueError('Invalid review status')
        lead = self.rows('SELECT * FROM leads WHERE id=?', (lead_id,))[0]
        if status == 'Verified' and (not lead['full_name'] or not lead['designation'] or not lead['country'] or not lead['source_url'] or not notes.strip()):
            raise ValueError('Verification needs name, role, country, source and reviewer evidence in notes')
        self.execute('UPDATE leads SET review_status=?, verification_status=?, notes=?, last_checked=?, updated_at=? WHERE id=?', (status, 'Verified' if status=='Verified' else 'Unverified', notes, now(), now(), lead_id))

    def edit(self, lead_id, values):
        allowed = {'full_name','designation','company','industry','country','continent','division','city','notes'}
        if not values or not set(values).issubset(allowed):
            raise ValueError('Unsupported edit fields')
        assignments = ','.join(f'{key}=?' for key in values)
        self.execute(f"UPDATE leads SET {assignments}, verification_status='Unverified', review_status='Needs Review', updated_at=? WHERE id=?", [*values.values(), now(), lead_id])

    def save_search(self, name, c):
        return self.execute('INSERT INTO saved_searches(name,criteria,created_at) VALUES(?,?,?)',(name,json.dumps(c.dict()),now()))

    def backup(self, destination):
        destination = Path(destination)
        if destination.exists(): raise ValueError('Choose a new backup filename')
        with self.connect() as db, sqlite3.connect(destination) as backup:
            db.backup(backup)

    def restore(self, source):
        source = Path(source).resolve()
        if source == self.path.resolve(): raise ValueError('Choose another database')
        with sqlite3.connect(f'{source.as_uri()}?mode=ro', uri=True) as check:
            if check.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Invalid database')
            if check.execute('PRAGMA user_version').fetchone()[0] != 1: raise ValueError('Unsupported schema')
            for table in ('leads','search_runs','search_results','saved_searches','export_history','data_sources','geographic_data_metadata','app_settings'):
                check.execute(f'SELECT * FROM {table} LIMIT 0')
            check.execute('SELECT '+','.join(['id']+FIELDS)+' FROM leads LIMIT 0')
            check.execute('SELECT id,criteria,provider,status,started_at,ended_at,candidates,new_leads,duplicates,rejected,errors FROM search_runs LIMIT 0')
            self.backup(self.path.with_name('before-restore-'+datetime.now().strftime('%Y%m%d%H%M%S%f')+'.db'))
            with self.connect() as db: check.backup(db)
