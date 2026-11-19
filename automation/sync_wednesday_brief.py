#!/usr/bin/env python3
"""Import explicitly curated Wednesday Brief records without deleting or replacing saved rows."""
import json, os, pathlib, re, urllib.request, urllib.parse
base=os.environ['SUPABASE_URL'].rstrip('/')+'/rest/v1/papers'
key=os.environ['SUPABASE_SERVICE_ROLE_KEY']
headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'}
def call(method, filters=None, payload=None):
    url=base+('?' + urllib.parse.urlencode(filters) if filters else '')
    request=urllib.request.Request(url,data=None if payload is None else json.dumps(payload).encode(),method=method,headers={**headers,'Prefer':'return=representation'})
    with urllib.request.urlopen(request,timeout=30) as r:
        return json.loads(r.read() or b'[]')
def main():
    records=json.loads(pathlib.Path('automation/wednesday_brief_papers.json').read_text())
    seen=set()
    for row in records:
        doi=row['doi'].strip().lower()
        if not re.fullmatch(r'10\.\d{4,9}/\S+',doi) or doi in seen:
            raise ValueError('Invalid or duplicate DOI: '+doi)
        seen.add(doi)
        if not row['title'].strip() or not 1<=int(row['stars'])<=5:raise ValueError('Invalid record: '+doi)
    failures=[]
    for row in records:
        doi=row['doi'].strip().lower()
        try:
            existing=call('GET',{'doi':'ilike.'+doi,'select':'id,doi,provenance,stars'})
            if not existing and row.get('pmid'):
                existing=call('GET',{'pmid':'eq.'+str(row['pmid']),'select':'id,doi,provenance,stars'})
            if not existing:
                existing=call('GET',{'source_key':'eq.doi:'+doi,'select':'id,doi,provenance,stars'})
            if existing:
                x=existing[0]
                if x['provenance']=='pubmed_weekly_auto':
                    call('PATCH',{'id':'eq.'+x['id']},{'provenance':'wednesday_brief','stars':max(x['stars'],row['stars']),'key_finding':row.get('key_finding',''),'runx2_value':row.get('runx2_value',''),'methods':row.get('methods',''),'topic':row['topic']})
                    print('Promoted',doi)
                else:print('Already saved',doi)
                continue
            fields=('title','authors','journal','publication_year','topic','stars','key_finding','runx2_value','methods')
            obj={k:row[k] for k in fields if k in row}
            obj.update(source_key='doi:'+doi,doi=doi,pmid=row.get('pmid') or None,url='https://doi.org/'+doi,provenance='wednesday_brief',verification_status='paper_confirmed_figure_pending',figures='Original figure details pending review',figure_cards=[])
            call('POST',payload=obj)
            print('Inserted',doi)
        except Exception as exc:
            failures.append(doi)
            print('Failed',doi,type(exc).__name__,str(exc))
    if failures:raise SystemExit('Failed records: '+', '.join(failures))
if __name__=='__main__':main()
