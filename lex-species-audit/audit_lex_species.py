"""Species-audit all LexicMap k13 hit accessions via SRA runinfo batches.

Writes /tmp/lex_species_map.tsv (accession, ScientificName, LibraryStrategy)
incrementally; a final species histogram goes to /tmp/lex_species_hist.txt.
Checkpoint-aware: skips accessions already in the TSV so a restart resumes.
"""

import csv
import io
import time
from collections import Counter
from pathlib import Path

import requests

LEX = Path("/home/danielle/Documents/brc-analytics/astmh-2026/k13_lexicmap_all_accessions.txt")
TSV = Path("/tmp/lex_species_map.tsv")
HIST = Path("/tmp/lex_species_hist.txt")
BATCH = 200

S = requests.Session()


def runinfo(batch):
    for attempt in range(8):
        try:
            r = S.get(
                "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo",
                params={"acc": ",".join(batch)}, timeout=120)
            if r.status_code in (429, 500, 502, 503):
                time.sleep(min(2 ** attempt, 30))
                continue
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"runinfo failed for batch starting {batch[0]}")


def main():
    accs = [l.strip() for l in open(LEX) if l.strip()]
    done = set()
    if TSV.exists():
        for row in csv.reader(open(TSV), delimiter="\t"):
            if row:
                done.add(row[0])
    todo = [a for a in accs if a not in done]
    print(f"{len(accs)} total, {len(done)} done, {len(todo)} to fetch", flush=True)

    out = open(TSV, "a", buffering=1)
    w = csv.writer(out, delimiter="\t")
    t0 = time.time()
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        try:
            text = runinfo(batch)
            rows = list(csv.DictReader(io.StringIO(text)))
        except RuntimeError as e:
            print(f"BATCHFAIL {batch[0]}: {e}", flush=True)
            rows = []
        for r in rows:
            w.writerow([r.get("Run", ""), r.get("ScientificName", "?"),
                        r.get("LibraryStrategy", "?")])
        done_n = min(i + BATCH, len(todo))
        if done_n % 2000 < BATCH:
            rate = done_n / max(time.time() - t0, 1)
            print(f"{done_n}/{len(todo)} ({rate:.0f}/s, "
                  f"eta {int((len(todo) - done_n) / max(rate, 1))}s)", flush=True)
        time.sleep(0.35)
    out.close()

    org = Counter()
    strat = Counter()
    for row in csv.reader(open(TSV), delimiter="\t"):
        if row:
            org[row[1]] += 1
            strat[row[2]] += 1
    with open(HIST, "w") as f:
        f.write("=== ScientificName ===\n")
        for k, v in org.most_common(100):
            f.write(f"{v}\t{k}\n")
        f.write("\n=== LibraryStrategy ===\n")
        for k, v in strat.most_common(30):
            f.write(f"{v}\t{k}\n")
    print("AUDIT DONE", len(done) + len(todo), flush=True)


if __name__ == "__main__":
    main()
