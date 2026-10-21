"""No undocumented search endpoints or authenticated profile fetching."""
import csv
from pathlib import Path
from .base import ProviderError

class AuthorizedImport:
    name = 'Authorized CSV import'
    def __init__(self, path):
        self.path = Path(path)

    def search(self, criteria):
        if self.path.stat().st_size > 20_000_000:
            raise ProviderError('Import exceeds the 20 MB limit')
        with self.path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or not {'profile_url', 'source_url'}.issubset(reader.fieldnames):
                raise ProviderError('CSV requires profile_url and source_url columns')
            for index, row in enumerate(reader):
                if index >= 100000:
                    raise ProviderError('Import exceeds 100,000 rows')
                yield row

class BrowserSearch:
    name = 'Manual browser search'
    status = 'Manual — no automatic results or connection claim'
    def search(self, criteria):
        raise ProviderError('Open the generated query in your browser, then import results you are authorized to use')
