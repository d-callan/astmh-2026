"""Kaggle CPU kernel: disassembler reconstruct + hyphaeon suite on ~5k mixed-plasmodium accessions.

Cohort: ALL LexicMap k13 hits that resolve to non-falciparum Plasmodium species
(orthologous k13 in P. vivax / berghei / knowlesi / chabaudi / ovale / malariae / ...)
plus a random Pfal fill to 5,000 total. Provenance: species_map.tsv in the dataset.

Pipeline (mirrors the kmi300 kernel + UDT):
  per 1,000-accession chunk:
    disassembler reconstruct -l chunk.txt -q k13_ref.fasta --msa-reference k13_ref.fasta
        -o out_i -w 8 --max-size-mb 512 --emit-snv-table --mafft-threads 4
        -- --scratch-dir . -t 1
  then:
    cat out_*/reconstructed.fasta -> all_recon.fasta
    mafft --auto --keeplength --thread 4 --addfragments all_recon.fasta k13_ref.fasta
        > k13_plasmo_codon_msa.fasta          (same as reconstruct's MSA stage)
    hyphaeon suite --use-tn93 (tree-free): meme, dms, epistasis, splits, filter

Chunking gives crash-resume: a completed out_i is skipped on re-push, and
partial cohorts still yield a usable MSA if the kernel hits the session cap.

Inputs (dataset daniellecallan/k13-plasmo5k):
  acc.txt, k13_ref.fasta, species_map.tsv
Outputs (/kaggle/working):
  out_0..out_4/  all_recon.fasta  k13_plasmo_codon_msa.fasta
  hyphaeon_out/  suite_log.txt  plasmo5k_out.tar.gz
"""

import glob
import os
import socket
import subprocess
import sys
from pathlib import Path

WORK = Path("/kaggle/working")
MM_ROOT = Path("/root/micromamba")
ENV_BIN = MM_ROOT / "envs" / "dis" / "bin"
COMMIT = "25c27f2"          # d-callan/disassembler, same pin as kmi300 kernel
CHUNK = 1000
WORKERS = 8                  # fetch-bound; oversubscribing 4 cores is a win
HYP = WORK / "hyphaeon_out"


def find_one(pattern: str) -> Path:
    hits = sorted(glob.glob(f"/kaggle/input/**/{pattern}", recursive=True))
    if not hits:
        raise SystemExit(f"missing {pattern}; mounted={os.listdir('/kaggle/input')}")
    return Path(hits[0])


def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], **kw)


def run_logged(name, cmd, log):
    print(f"\n===== {name} =====\n+ {' '.join(map(str, cmd))}", flush=True)
    log.write(f"\n===== {name} =====\n+ {' '.join(map(str, cmd))}\n")
    log.flush()
    rc = subprocess.run([str(c) for c in cmd],
                        stdout=log, stderr=subprocess.STDOUT).returncode
    log.write(f"[{name}] rc={rc}\n")
    log.flush()
    print(f"[{name}] rc={rc}", flush=True)
    return rc


def main() -> int:
    try:
        socket.create_connection(("s3.amazonaws.com", 443), timeout=10)
    except OSError:
        raise SystemExit("NO INTERNET -- verify phone number at kaggle.com/settings")

    os.chdir(WORK)
    acc_file = find_one("acc.txt")
    ref = find_one("k13_ref.fasta")
    accs = [l.strip() for l in open(acc_file) if l.strip()]
    print(f"[*] {len(accs)} accessions", flush=True)

    # --- toolchain env ---------------------------------------------------
    os.environ["MAMBA_ROOT_PREFIX"] = str(MM_ROOT)
    if not Path("/root/bin/micromamba").exists():
        subprocess.run(["bash", "-c",
            "curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest "
            "| tar -xj -C /root bin/micromamba"], check=True)
    mm = "/root/bin/micromamba"
    subprocess.run([mm, "create", "-y", "-n", "dis",
        "-c", "conda-forge", "-c", "bioconda",
        "python=3.12", "logan-walker", "graphaligner=1.0.17b",
        "mafft>=7.526", "fasttree", "zstd",
        "biopython", "requests", "pip", "git"], check=True)
    subprocess.run([str(ENV_BIN / "pip"), "install", "--quiet",
                    f"git+https://github.com/d-callan/disassembler.git@{COMMIT}"],
                   check=True)
    os.environ["PATH"] = f"{ENV_BIN}:{os.environ['PATH']}"
    # hyphaeon on Kaggle's own python (torch already present)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "hyphaeon-core[tn93]", "hyphaeon"], check=True)

    HYP.mkdir(exist_ok=True)
    log = open(HYP / "suite_log.txt", "w")

    # --- chunked reconstruct ---------------------------------------------
    chunks = [accs[i:i + CHUNK] for i in range(0, len(accs), CHUNK)]
    for ci, chunk in enumerate(chunks):
        outdir = WORK / f"out_{ci}"
        marker = outdir / "reconstructed.fasta"
        if marker.exists() and marker.stat().st_size > 0:
            print(f"[*] chunk {ci}: already done ({marker})", flush=True)
            continue
        cf = WORK / f"acc_{ci}.txt"
        cf.write_text("\n".join(chunk) + "\n")
        run_logged(f"reconstruct[{ci}]", [
            str(ENV_BIN / "disassembler"), "reconstruct",
            "-l", cf, "-q", ref, "--msa-reference", ref,
            "-o", outdir, "-w", WORKERS,
            "--max-size-mb", "512", "--emit-snv-table",
            "--mafft-threads", "4",
            "--", "--scratch-dir", ".", "-t", "1"], log)

    # --- combined codon MSA ----------------------------------------------
    recon = sorted(WORK.glob("out_*/reconstructed.fasta"))
    with open(WORK / "all_recon.fasta", "w") as f:
        for p in recon:
            f.write(p.read_text())
    n = sum(1 for p in recon for l in open(p) if l.startswith(">"))
    print(f"[*] {n} reconstructed haplotypes from {len(recon)} chunks", flush=True)

    msa = WORK / "k13_plasmo_codon_msa.fasta"
    # same invocation reconstruct's MSA stage uses; alignment goes to stdout
    cmd = [str(ENV_BIN / "mafft"), "--auto", "--keeplength", "--thread", "4",
           "--addfragments", str(WORK / "all_recon.fasta"), str(ref)]
    print("+", " ".join(cmd), flush=True)
    with open(msa, "w") as out:
        rc = subprocess.run(cmd, stdout=out, stderr=log).returncode
    log.write(f"[mafft] rc={rc}\n"); log.flush()
    print(f"[mafft] rc={rc} -> {msa} ({msa.stat().st_size} bytes)", flush=True)

    # --- hyphaeon suite (tree-free) ---------------------------------------
    A = ["-a", str(msa), "--use-tn93"]
    results = {}
    results["list-models"] = run_logged("list-models", ["hyphaeon", "list-models"], log)
    results["meme"] = run_logged("meme", ["hyphaeon", "meme", *A,
        "-o", HYP / "meme.json", "-c", HYP / "meme.csv"], log)
    results["dms"] = run_logged("dms", ["hyphaeon", "dms", *A,
        "--focal-taxon", "Reference",
        "-o", HYP / "dms.json", "-c", HYP / "dms.csv"], log)
    results["epistasis"] = run_logged("epistasis", ["hyphaeon", "epistasis", *A,
        "--focal-taxon", "Reference", "-o", HYP / "epistasis.json"], log)
    results["splits"] = run_logged("splits", ["hyphaeon", "splits", *A,
        "-o", HYP / "splits.json", "-c", HYP / "splits.csv"], log)
    results["filter"] = run_logged("filter", ["hyphaeon", "filter", *A,
        "-o", HYP / "filter.json", "-c", HYP / "filter_audit.csv"], log)
    log.close()

    print("\n===== suite summary =====", flush=True)
    for k, v in results.items():
        print(f"  {k}: rc={v}", flush=True)
    subprocess.run(["tar", "-czf", "plasmo5k_out.tar.gz",
                    *[f"out_{i}" for i in range(len(chunks))],
                    "all_recon.fasta", "k13_plasmo_codon_msa.fasta",
                    "hyphaeon_out"], check=False)
    return 0 if all(v == 0 for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
