import json
import math
import re
from datetime import datetime, timezone
import httpx
import pycountry
import geonamescache

CONTINENTS={'AF':'Africa','AS':'Asia','EU':'Europe','NA':'North America','SA':'South America','OC':'Oceania','AN':'Antarctica'}

class Geography:
    def __init__(self, store):
        self.store=store
        self.countries=sorted(geonamescache.GeonamesCache().get_countries().values(),key=lambda c:c['name'])

    def countries_in(self, continent):
        return [c for c in self.countries if CONTINENTS.get(c['continentcode'])==continent]

    def divisions(self, code):
        return sorted([(s.name,s.type) for s in pycountry.subdivisions.get(country_code=code)],key=lambda x:x[0])

    def cached(self, code):
        rows=self.store.rows('SELECT payload FROM geographic_data_metadata WHERE country=?',(code,))
        return json.loads(rows[0]['payload']) if rows else None

    def refresh(self, code, client=None):
        if not pycountry.countries.get(alpha_2=code): raise ValueError('Unknown country code')
        url=f'https://api.worldbank.org/v2/country/{code}/indicator/SP.POP.TOTL'
        if client is None:
            with httpx.Client(timeout=20,follow_redirects=False) as client:
                return self.refresh(code,client)
        response=client.get(url,params={'format':'json','per_page':20})
        response.raise_for_status()
        body=response.json()
        if not isinstance(body,list) or len(body)<2 or not isinstance(body[1],list): raise ValueError('Population response unavailable')
        records=[r for r in body[1] if isinstance(r,dict) and type(r.get('value')) in (int,float)
                 and math.isfinite(r['value']) and r['value']>=0
                 and re.fullmatch(r'[0-9]{4}',str(r.get('date','')))]
        record=max(records,key=lambda r:int(r['date']),default=None)
        if not record: raise ValueError('No dated population available')
        payload={'population':record['value'],'year':record['date'],'source':'World Bank SP.POP.TOTL','url':url,'license':'CC BY 4.0 (World Bank dataset terms apply)','refreshed':datetime.now(timezone.utc).isoformat()}
        self.store.execute('INSERT INTO geographic_data_metadata(country,payload) VALUES(?,?) ON CONFLICT(country) DO UPDATE SET payload=excluded.payload',(code,json.dumps(payload)))
        return payload
