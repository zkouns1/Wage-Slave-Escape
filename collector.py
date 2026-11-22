"""Opportunity Radar collector. Public APIs and operator-configured RSS feeds only."""
import datetime as dt
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests

ROOT = Path(__file__).parent
DB = ROOT / 'radar.db'
CFG = json.loads((ROOT / 'config.json').read_text())
HEADERS = {'User-Agent': 'OpportunityRadar/2.0 (contact: configure-before-public-deployment)'}


def connect():
    db = sqlite3.connect(DB)
    db.execute('''CREATE TABLE IF NOT EXISTS opportunities (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, organization TEXT, category TEXT,
        location TEXT, remote TEXT, url TEXT NOT NULL, source TEXT,
        deadline TEXT, compensation TEXT, description TEXT,
        first_seen TEXT, last_seen TEXT, status TEXT DEFAULT 'new',
        eligibility TEXT DEFAULT 'unverified', score INTEGER DEFAULT 0)''')
    db.execute('''CREATE TABLE IF NOT EXISTS scans (
        timestamp TEXT, source TEXT, result TEXT, count INTEGER)''')
    return db


def category_for(text):
    t = text.lower()
    rules = [
        ('Audio engineering jobs', ['audio engineer','sound engineer','sound designer','mixing engineer','mastering engineer','audio producer']),
        ('Data analytics jobs', ['data analyst','analytics','business intelligence','data scientist']),
        ('Poetry & writing', ['poetry','poet','literary','writing','writer']),
        ('Artist residencies', ['residency','residence','artist-in-residence']),
        ('Fellowships & competitions', ['fellowship','competition','contest','prize']),
        ('Music & arts grants', ['music','composer','grant','arts','artist'])]
    for category, terms in rules:
        if any(term in t for term in terms):
            return category
    return 'Other'


def relevance(row):
    t = (row.get('title','') + ' ' + row.get('description','')).lower()
    hits = sum(1 for k in CFG['keywords'] if k in t)
    score = min(90, hits * 12)
    if row.get('remote') == 'remote': score += 10
    return min(100, score)


def save(db, row):
    if not row.get('url') or not row.get('title'): return False
    key = hashlib.sha256(row['url'].strip().split('#')[0].encode()).hexdigest()[:24]
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    row.setdefault('category', category_for(row['title'] + ' ' + row.get('description','')))
    row['score'] = relevance(row)
    fields = ('id','title','organization','category','location','remote','url','source','deadline','compensation','description','first_seen','last_seen','score')
    values = [key] + [row.get(f,'') for f in fields[1:-3]] + [now,now,row['score']]
    exists = db.execute('SELECT id FROM opportunities WHERE id=?',(key,)).fetchone()
    if exists:
        db.execute('UPDATE opportunities SET last_seen=?, score=? WHERE id=?',(now,row['score'],key))
        return False
    db.execute(f"INSERT INTO opportunities ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",values)
    return True


def get_json(url, method='GET', payload=None):
    r = requests.request(method,url,json=payload,headers=HEADERS,timeout=25)
    r.raise_for_status()
    return r.json()


def collect_jobs(provider,slug):
    if not slug: return []
    if provider == 'greenhouse':
        url=f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true'
        jobs=get_json(url).get('jobs',[])
        return [dict(title=j.get('title',''),organization=slug,location=(j.get('location') or {}).get('name',''),remote='unknown',url=j.get('absolute_url',''),source='Greenhouse',description=j.get('content','')) for j in jobs]
    if provider == 'lever':
        jobs=get_json(f'https://api.lever.co/v0/postings/{slug}?mode=json')
        return [dict(title=j.get('text',''),organization=slug,location=(j.get('categories') or {}).get('location',''),remote=str(j.get('workplaceType','unknown')).lower(),url=j.get('hostedUrl',''),source='Lever',description=j.get('descriptionPlain','')) for j in jobs]
    if provider == 'ashby':
        jobs=get_json(f'https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true').get('jobs',[])
        return [dict(title=j.get('title',''),organization=slug,location=j.get('location',''),remote=str(j.get('workplaceType','unknown')).lower(),url=j.get('jobUrl',''),source='Ashby',description=j.get('descriptionPlain',''),compensation=j.get('compensation',{}).get('compensationTierSummary','') if isinstance(j.get('compensation'),dict) else '') for j in jobs if j.get('isListed',True)]
    raise ValueError('Unsupported provider')


def collect_grants(keyword):
    data=get_json('https://api.grants.gov/v1/api/search2','POST',{'keyword':keyword})
    items=data.get('data',{}).get('oppHits',[]) or []
    return [dict(title=j.get('title',''),organization=j.get('agencyName',''),location='United States / eligibility varies',remote='not applicable',url='https://www.grants.gov/search-results-detail/'+str(j.get('id','')),source='Grants.gov',deadline=j.get('closeDate',''),description=j.get('description','')) for j in items if j.get('id')]


def collect_feed(url):
    if urlparse(url).scheme != 'https': raise ValueError('Only HTTPS feeds allowed')
    feed=feedparser.parse(url)
    if feed.bozo and not feed.entries: raise ValueError(str(feed.bozo_exception))
    return [dict(title=e.get('title',''),organization=feed.feed.get('title',''),url=e.get('link',''),source='RSS',description=e.get('summary',''),remote='unknown') for e in feed.entries]


def run():
    db=connect()
    sources=[]
    sources += [(f'{b["provider"]}:{b["slug"]}',lambda b=b:collect_jobs(b['provider'],b['slug'])) for b in CFG['job_boards'] if b.get('slug')]
    sources += [(f'Grants.gov:{k}',lambda k=k:collect_grants(k)) for k in CFG['grants_gov_keywords']]
    sources += [(f'RSS:{url}',lambda url=url:collect_feed(url)) for url in CFG['rss_feeds']]
    for name,fn in sources:
        try:
            rows=fn(); new=sum(save(db,row) for row in rows)
            result=f'ok: {len(rows)} retrieved, {new} new'
            db.execute('INSERT INTO scans VALUES (?,?,?,?)',(dt.datetime.now(dt.timezone.utc).isoformat(),name,result,len(rows)))
            print(name,result)
        except Exception as exc:
            print(name,'ERROR:',exc,file=sys.stderr)
            db.execute('INSERT INTO scans VALUES (?,?,?,?)',(dt.datetime.now(dt.timezone.utc).isoformat(),name,str(exc),0))
        db.commit()
    db.close()

if __name__ == '__main__': run()
