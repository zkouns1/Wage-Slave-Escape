"""Public, read-only mobile-first Opportunity Radar MVP."""
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Opportunity Radar", page_icon="📡", layout="centered", initial_sidebar_state="collapsed")
st.markdown('''<style>
.block-container{max-width:850px;padding-top:1.2rem;padding-left:1rem;padding-right:1rem}
[data-testid="stMetric"]{background:#f4f6fa;border-radius:12px;padding:12px}
.op-card{border:1px solid #dce1e8;border-radius:14px;padding:16px;margin:10px 0;background:var(--secondary-background-color)}
.op-card a{font-weight:650;text-decoration:none}
small{opacity:.78}
</style>''',unsafe_allow_html=True)
st.title('📡 Opportunity Radar')
st.caption('Grants · Creative opportunities · Jobs · Residencies · Fellowships')
DB=Path(__file__).with_name('radar.db')
if not DB.exists():
    st.info('The first discovery scan has not been published yet. The site is ready; run the collector and commit radar.db to publish listings.')
    st.stop()
with sqlite3.connect(f'file:{DB}?mode=ro',uri=True) as db:
    try:
        df=pd.read_sql_query('SELECT * FROM opportunities ORDER BY score DESC, first_seen DESC',db)
        last=pd.read_sql_query('SELECT MAX(timestamp) AS latest FROM scans',db).iloc[0]['latest']
    except (sqlite3.DatabaseError,KeyError) as exc:
        st.error(f'Database needs a fresh collector run: {exc}')
        st.stop()
st.caption(f'Last scan: {last[:16].replace("T"," ") + " UTC" if isinstance(last,str) else "not recorded"} · Listings may expire; verify at source')
if df.empty:
    st.info('No listings collected yet. Configure sources and run the collector.')
    st.stop()
col1,col2=st.columns(2)
col1.metric('Opportunities',len(df))
col2.metric('Sources',df.source.nunique())
query=st.text_input('🔎 Search',placeholder='Try: poet, composer, analyst')
category=st.selectbox('Category',['All categories']+sorted(df.category.fillna('Other').unique().tolist()))
remote=st.selectbox('Work arrangement',['All arrangements','Remote','Hybrid','In person / other'])
minimum=st.slider('Minimum match score',0,100,0,10)
filtered=df[df.score.fillna(0)>=minimum].copy()
if category!='All categories': filtered=filtered[filtered.category==category]
if query:
    searchcols=['title','organization','description','location']
    match=filtered[searchcols].fillna('').astype(str).agg(' '.join,axis=1).str.contains(query,case=False,regex=False)
    filtered=filtered[match]
if remote=='Remote': filtered=filtered[filtered.remote.fillna('').str.lower().eq('remote')]
elif remote=='Hybrid': filtered=filtered[filtered.remote.fillna('').str.lower().eq('hybrid')]
elif remote=='In person / other': filtered=filtered[~filtered.remote.fillna('').str.lower().isin(['remote','hybrid'])]
st.write(f'**{len(filtered)} matches**')
page_size=20
pages=max(1,(len(filtered)+page_size-1)//page_size)
page=st.number_input('Page',min_value=1,max_value=pages,value=1,step=1)
for _,r in filtered.iloc[(page-1)*page_size:page*page_size].iterrows():
    with st.container(border=True):
        st.markdown(f'**{r["title"]}**')
        st.caption(' · '.join(str(v) for v in [r.get('organization'),r.get('category'),r.get('location')] if pd.notna(v) and str(v).strip()))
        st.write(f'**Match:** {int(r["score"] or 0)}/100  ·  **Source:** {r.get("source") or "Unknown"}')
        if pd.notna(r.get('deadline')) and str(r['deadline']).strip(): st.write('**Deadline:** '+str(r['deadline']))
        if pd.notna(r.get('compensation')) and str(r['compensation']).strip(): st.write('**Compensation:** '+str(r['compensation']))
        st.link_button('View original opportunity ↗',str(r['url']),use_container_width=True)
st.caption('Public preview · Read-only · Scores are keyword estimates, not eligibility decisions. International and remote restrictions vary. Always check original listings.')
