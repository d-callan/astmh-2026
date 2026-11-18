import csv, io, sys, time
import requests
BATCH=200; W=int(sys.argv[1]); N=int(sys.argv[2])
LEX="/home/danielle/Documents/brc-analytics/astmh-2026/k13_lexicmap_all_accessions.txt"
OUT=f"/tmp/lex_species_w{W}.tsv"
accs=[l.strip() for l in open(LEX) if l.strip()]
done=set()
try:
    for row in csv.reader(open(OUT),delimiter="\t"):
        if row: done.add(row[0])
except FileNotFoundError: pass
# also skip what the original worker already fetched
try:
    for row in csv.reader(open("/tmp/lex_species_map.tsv"),delimiter="\t"):
        if row: done.add(row[0])
except FileNotFoundError: pass
todo=[a for i,a in enumerate(accs) if i%N==W and a not in done]
print(f"w{W}: {len(todo)} to fetch",flush=True)
S=requests.Session()
def runinfo(batch):
    for a in range(8):
        try:
            r=S.get("https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo",
                    params={"acc":",".join(batch)},timeout=120)
            if r.status_code in (429,500,502,503): time.sleep(min(2**a,30)); continue
            r.raise_for_status(); return r.text
        except requests.RequestException: time.sleep(min(2**a,30))
    return None
out=open(OUT,"a",buffering=1); w=csv.writer(out,delimiter="\t")
fails=[]
for i in range(0,len(todo),BATCH):
    b=todo[i:i+BATCH]
    t=runinfo(b)
    if t is None: fails+=b; continue
    for r in csv.DictReader(io.StringIO(t)):
        w.writerow([r.get("Run",""),r.get("ScientificName","?"),r.get("LibraryStrategy","?")])
    if (i//BATCH)%10==0: print(f"w{W}: {i}/{len(todo)}",flush=True)
    time.sleep(0.25)
print(f"w{W} DONE, {len(fails)} failed",flush=True)
