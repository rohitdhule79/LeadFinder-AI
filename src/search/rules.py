from dataclasses import dataclass, field, asdict
from urllib.parse import urlsplit, unquote, quote
import re

ROLES = ['Founder', 'Co-Founder', 'CEO', 'Chief Executive Officer', 'Managing Director', 'Owner', 'Business Owner', 'President', 'Director', 'Executive Director', 'CTO', 'CIO', 'CISO', 'CFO', 'COO', 'Partner', 'Investor']

def normalize_url(value):
    try:
        u = urlsplit(value.strip())
        host = (u.hostname or '').lower()
        if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443):
            raise ValueError('Use an HTTPS public LinkedIn profile URL')
        if host not in ('linkedin.com', 'www.linkedin.com') and not re.fullmatch(r'[a-z]{2,3}\.linkedin\.com', host):
            raise ValueError('Only public LinkedIn /in/ profile URLs are supported')
        path = unquote(u.path).rstrip('/')
        if not re.fullmatch(r'/in/[\w-]{2,120}', path, re.UNICODE):
            raise ValueError('Expected a public /in/ profile URL')
        return 'https://www.linkedin.com' + quote(path, safe='/-')
    except (TypeError, AttributeError) as exc:
        raise ValueError('Invalid URL') from exc

@dataclass
class Criteria:
    country: str = ''
    continent: str = ''
    division: str = ''
    city: str = ''
    roles: list = field(default_factory=lambda: ['Founder'])
    keywords: str = ''
    exclusions: str = ''
    company: str = ''
    industry: str = ''
    target: int = 25
    followers: int = 0
    connections: int = 0
    mode: str = 'AND'
    include_unknown: bool = False
    exclude_existing: bool = True

    def validate(self):
        if not self.country.strip() or not any(r.strip() for r in self.roles):
            raise ValueError('Choose a country and at least one role')
        if not 1 <= self.target <= 10000 or min(self.followers, self.connections) < 0:
            raise ValueError('Invalid lead count or metrics')
        if self.mode not in ('AND', 'OR', 'Independent'):
            raise ValueError('Invalid metric rule')
        return self

    def dict(self):
        return asdict(self)

def metric_match(lead, criteria):
    checks = []
    for key in ('followers', 'connections'):
        minimum = getattr(criteria, key)
        if minimum:
            value = lead.get(key)
            checks.append(criteria.include_unknown if value is None else value >= minimum)
    if not checks:
        return True
    return all(checks) if criteria.mode == 'AND' else any(checks)

def queries(c):
    c.validate()
    def quoted(s):
        return '"' + s.replace('"', ' ').replace('\n', ' ') + '"'
    common = ' '.join(quoted(x) for x in (c.country, c.division, c.city, c.keywords, c.company, c.industry) if x.strip())
    excluded = ' '.join('-' + quoted(x.strip()) for x in c.exclusions.split(',') if x.strip())
    return [f'site:linkedin.com/in/ {quoted(role)} {common} {excluded}'.strip() for role in c.roles if role.strip()]

def qualify(lead, c):
    # Search snippets and matching text are hints, not independent verification.
    for key in ('country', 'division', 'city', 'company', 'industry'):
        wanted = getattr(c, key)
        if wanted and wanted.casefold() not in str(lead.get(key) or '').casefold():
            return False, f'{key} missing or does not match'
    designation = str(lead.get('designation') or '').casefold()
    if not any(role.casefold() in designation for role in c.roles):
        return False, 'Role missing or does not match'
    text = ' '.join(str(x or '') for x in lead.values()).casefold()
    if c.keywords and c.keywords.casefold() not in text:
        return False, 'Keyword missing'
    if any(x.strip().casefold() in text for x in c.exclusions.split(',') if x.strip()):
        return False, 'Excluded keyword'
    return metric_match(lead, c), 'Metric threshold not satisfied'
