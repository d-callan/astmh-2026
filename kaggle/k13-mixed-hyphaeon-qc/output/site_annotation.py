"""Annotate QC-mixed meme survivor sites with residue composition.

Inputs (raw outputs):
  kaggle/k13-mixed-hyphaeon-qc/output/hyphaeon_out/meme.csv      <- QC mixed hits
  kaggle/k13-pfal-hyphaeon-qc/output/hyphaeon_out/meme.csv       <- QC Pfal-only hits
  kaggle/k13-mixed-msa-qc-dataset/k13_ref_codon_msa.fasta        <- QC mixed MSA
  kaggle/k13-plasmo5k-dataset/species_map.tsv                    <- accession -> species

Output: per-site table = p, q, ref aa, non-Pfal aa counts, Pfal aa counts,
        mixed-only flag, domain region (N-term <350 / propeller 350-620 / C-tail),
        known-resistance-codon flag.
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path('/home/danielle/Documents/brc-analytics/astmh-2026')
CT = {'ttt':'F','ttc':'F','tta':'L','ttg':'L','ctt':'L','ctc':'L','cta':'L','ctg':'L',
      'att':'I','atc':'I','ata':'I','atg':'M','gtt':'V','gtc':'V','gta':'V','gtg':'V',
      'tct':'S','tcc':'S','tca':'S','tcg':'S','cct':'P','ccc':'P','cca':'P','ccg':'P',
      'act':'T','acc':'T','aca':'T','acg':'T','gct':'A','gcc':'A','gca':'A','gcg':'A',
      'tat':'Y','tac':'Y','taa':'*','tag':'*','cat':'H','cac':'H','caa':'Q','cag':'Q',
      'aat':'N','aac':'N','aaa':'K','aag':'K','gat':'D','gac':'D','gaa':'E','gag':'E',
      'tgt':'C','tgc':'C','tga':'*','tgg':'W','cgt':'R','cgc':'R','cga':'R','cgg':'R',
      'agt':'S','agc':'S','aga':'R','agg':'R','ggt':'G','ggc':'G','gga':'G','ggg':'G',
      '---':'-'}
# WHO-validated + candidate K13 artemisinin-resistance codons
RESISTANCE = {446,458,469,476,481,493,515,522,527,531,537,538,539,543,553,
              561,568,574,578,580,584,622,675}

def load_fasta(path):
    seqs, name = {}, None
    for line in open(path):
        if line.startswith('>'):
            name = line[1:].split()[0]
            seqs[name] = ''
        else:
            seqs[name] += line.strip()
    return seqs

def hits(path, thresh=0.10):
    return {int(r['site']): (float(r['p_value']), float(r['q_value']))
            for r in csv.DictReader(open(path)) if float(r['p_value']) <= thresh}

species = {r[0]: r[1] for r in csv.reader(open(ROOT/'kaggle/k13-plasmo5k-dataset/species_map.tsv'), delimiter='\t')}
seqs = load_fasta(ROOT/'kaggle/k13-mixed-msa-qc-dataset/k13_ref_codon_msa.fasta')
ref = seqs['PF3D7_1343700']
nonpfal = {k: s for k, s in seqs.items()
           if k.split('_')[0] in species and 'falciparum' not in species[k.split('_')[0]]}
pfal = {k: s for k, s in seqs.items()
        if k != 'PF3D7_1343700' and k.split('_')[0] in species and 'falciparum' in species[k.split('_')[0]]}
print(f'MSA: {len(seqs)} taxa = {len(pfal)} Pfal + {len(nonpfal)} non-Pfal + ref')

mixed_hits = hits(ROOT/'kaggle/k13-mixed-hyphaeon-qc/output/hyphaeon_out/meme.csv')
pfal_hits = hits(ROOT/'kaggle/k13-pfal-hyphaeon-qc/output/hyphaeon_out/meme.csv')
print(f'QC-mixed hits: {len(mixed_hits)} | QC-Pfal hits: {len(pfal_hits)} | shared: {sorted(set(mixed_hits)&set(pfal_hits))}\n')

def region(site):
    # K13 structure: N-terminal ~350 aa = Plasmodium-specific low-complexity tract;
    # ~350-726 = six-bladed kelch propeller (validated marker A675V is blade 6)
    if site < 350: return 'N-term'
    return 'propeller'

print(f"{'site':>5} {'p':>8} {'q':>6} {'ref':>4} {'region':>9} {'R?':>3} {'only':>4} | {'nonPfal':<28} | Pfal")
for site in sorted(mixed_hits, key=lambda s: mixed_hits[s][0]):
    p, q = mixed_hits[site]
    i = (site-1)*3
    raa = CT.get(ref[i:i+3], '?')
    naa = Counter(CT.get(s[i:i+3], '?') for s in nonpfal.values())
    paa = Counter(CT.get(s[i:i+3], '?') for s in pfal.values())
    only = '' if site in pfal_hits else 'MIX'
    flag = 'R' if site in RESISTANCE else ''
    print(f"{site:>5} {p:>8.4f} {q:>6.3f} {raa:>4} {region(site):>9} {flag:>3} {only:>4} | "
          f"{str(dict(naa.most_common(4))):<28} | {dict(paa.most_common(3))}")
