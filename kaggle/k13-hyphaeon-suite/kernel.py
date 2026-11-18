"""Kaggle GPU kernel: hyphaeon selection suite on the k13 reconstructed-haplotype MSA.

Input: dataset daniellecallan/k13-kmi300-msa
       (k13_ref_codon_msa.fasta -- 168 taxa x 2181 nt codon MSA produced by
        disassembler reconstruct on 300 kmindex k13 hits; first record is the
        PF3D7_1343700 reference, header id "Reference").

All analyses run TREE-FREE via --use-tn93 (distances estimated from the
alignment itself) -- the talk point: no phylogeny required upstream of
hyphaeon inference.

Suite:
  meme      episodic site-level positive selection
  dms       in-silico deep mutational scan, focal taxon = Reference
  epistasis co-selection / epistatic sector mining, focal = Reference
  splits    cross-taxa attention clade structure
  filter    alignment QC / artifact audit
  list-models  provenance for the model variant used

Outputs in /kaggle/working/hyphaeon_out/: *.json/*.csv per analysis,
suite_log.txt, hyphaeon_out.tar.gz.
"""

import glob
import os
import socket
import subprocess
import sys
from pathlib import Path

WORK = Path("/kaggle/working")
OUT = WORK / "hyphaeon_out"


def find_one(pattern: str) -> Path:
    hits = sorted(glob.glob(f"/kaggle/input/**/{pattern}", recursive=True))
    if not hits:
        raise SystemExit(f"missing {pattern}; mounted={os.listdir('/kaggle/input')}")
    return Path(hits[0])


def main() -> int:
    try:
        socket.create_connection(("huggingface.co", 443), timeout=10)
    except OSError:
        raise SystemExit(
            "NO INTERNET on this kernel VM -- verify phone number at "
            "kaggle.com/settings (required for internet + GPU), then re-push."
        )

    aln = find_one("k13_ref_codon_msa.fasta")
    print(f"[*] alignment: {aln}", flush=True)

    # Kaggle image already ships a CUDA torch; hyphaeon-core[tn93] brings the
    # tn93 distance machinery --use-tn93 needs.
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "hyphaeon-core[tn93]", "hyphaeon"], check=True)

    import torch
    print(f"[*] torch {torch.__version__}, cuda={torch.cuda.is_available()}, "
          f"device={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'}",
          flush=True)
    if not torch.cuda.is_available():
        print("[!] no GPU visible -- continuing on CPU (enable_gpu in metadata?)",
              flush=True)

    OUT.mkdir(exist_ok=True)
    log = open(OUT / "suite_log.txt", "w")

    def run(name: str, args: list[str]) -> int:
        cmd = ["hyphaeon"] + args
        print(f"\n===== {name} =====\n+ {' '.join(cmd)}", flush=True)
        log.write(f"\n===== {name} =====\n+ {' '.join(cmd)}\n")
        log.flush()
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
        log.write(f"[{name}] rc={rc}\n")
        log.flush()
        print(f"[{name}] rc={rc}", flush=True)
        return rc

    A = ["-a", str(aln), "--use-tn93"]
    results = {}

    results["list-models"] = run("list-models", ["list-models"])
    results["meme"] = run("meme", ["meme", *A,
        "-o", str(OUT / "meme.json"), "-c", str(OUT / "meme.csv")])
    results["dms"] = run("dms", ["dms", *A,
        "--focal-taxon", "Reference",
        "-o", str(OUT / "dms.json"), "-c", str(OUT / "dms.csv")])
    results["epistasis"] = run("epistasis", ["epistasis", *A,
        "--focal-taxon", "Reference", "-o", str(OUT / "epistasis.json")])
    results["splits"] = run("splits", ["splits", *A,
        "-o", str(OUT / "splits.json"), "-c", str(OUT / "splits.csv")])
    results["filter"] = run("filter", ["filter", *A,
        "-o", str(OUT / "filter.json"), "-c", str(OUT / "filter_audit.csv")])

    log.close()
    print("\n===== suite summary =====", flush=True)
    for k, v in results.items():
        print(f"  {k}: rc={v}", flush=True)

    subprocess.run(["tar", "-czf", str(WORK / "hyphaeon_out.tar.gz"),
                    "-C", str(WORK), "hyphaeon_out"], check=False)
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            print(f"  {p.name}  {p.stat().st_size}", flush=True)
    return 0 if all(v == 0 for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
