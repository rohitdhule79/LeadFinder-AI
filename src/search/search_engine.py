import json
import threading
import httpx
from src.database.store import now
from src.search.rules import normalize_url, qualify
from src.providers.base import ProviderError

class SearchEngine:
    def __init__(self, store):
        self.store = store
        self.cancelled = threading.Event()
        self.active = threading.Event(); self.active.set()

    def cancel(self):
        self.cancelled.set(); self.active.set()

    def pause(self): self.active.clear()
    def resume(self): self.active.set()

    def run(self, criteria, provider, progress=lambda x: None):
        criteria.validate()
        run_id = self.store.start_run(criteria, provider.name)
        counts = dict(candidates=0, new_leads=0, duplicates=0, rejected=0)
        status, error = 'Completed', ''
        try:
            for lead in provider.search(criteria):
                self.active.wait()
                if self.cancelled.is_set():
                    status = 'Cancelled'; break
                counts['candidates'] += 1
                outcome, reason, lead_id, url = 'Rejected', '', None, ''
                try:
                    url = normalize_url(lead.get('profile_url', ''))
                    # Both lookups are indexed; global uniqueness remains the final authority.
                    existing = self.store.country_exists(criteria.country, url) or bool(self.store.rows('SELECT id FROM leads WHERE profile_url=?',(url,)))
                    if existing:
                        outcome, reason = 'Duplicate', 'Already stored; original record preserved'
                        counts['duplicates'] += 1
                    else:
                        for key in ('followers','connections'):
                            raw = lead.get(key)
                            lead[key] = None if raw in (None,'','Unknown') else int(raw)
                        allowed, reason = qualify(lead, criteria)
                        if allowed:
                            lead['discovery_source'] = provider.name
                            lead_id = self.store.add_lead(lead, run_id)
                            outcome = 'Needs Review' if lead_id else 'Duplicate'
                            counts['new_leads' if lead_id else 'duplicates'] += 1
                        else: counts['rejected'] += 1
                except (ValueError, TypeError) as exc:
                    reason = str(exc); counts['rejected'] += 1
                self.store.execute('INSERT INTO search_results(run_id,lead_id,profile_url,outcome,reason) VALUES(?,?,?,?,?)',(run_id,lead_id,url,outcome,reason))
                self.store.execute('UPDATE search_runs SET candidates=?,new_leads=?,duplicates=?,rejected=? WHERE id=?',(*counts.values(),run_id))
                progress(dict(counts, run_id=run_id))
                if counts['new_leads'] >= criteria.target: break
        except (OSError, ProviderError, httpx.HTTPError, ValueError) as exc:
            status, error = 'Failed', str(exc)
        except Exception as exc:
            status, error = 'Failed', f'Unexpected provider failure: {type(exc).__name__}'
        finally:
            self.store.execute('UPDATE search_runs SET status=?,ended_at=?,candidates=?,new_leads=?,duplicates=?,rejected=?,errors=? WHERE id=?',(status,now(),*counts.values(),error,run_id))
        return dict(counts, run_id=run_id, status=status, error=error)
