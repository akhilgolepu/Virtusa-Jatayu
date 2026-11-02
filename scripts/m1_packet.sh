#!/usr/bin/env bash
# Rebuild every M1 evidence file at ONE commit (HEAD, clean tree): commit.txt, the ten samples, verify before/after a
# tamper, the tamper suite, the five worst failures and the full pytest run. Usage: bash scripts/m1_packet.sh
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=results/packets/m1
if [ -n "$(git status --porcelain --untracked-files=all | grep -v ' results/' || true)" ]; then
  echo "dirty tree: commit first" >&2; exit 1
fi
C=$(git rev-parse --short HEAD)
echo "$C" > $OUT/commit.txt
DB=$OUT/sample.sqlite; rm -f "$DB"
i=0
while IFS= read -r s; do
  i=$((i+1)); f=$(printf "%s/sample_%02d.json" $OUT $i)
  if [ $i -eq 1 ]; then
    python -m f2r.cli --db "$DB" add "$s" --extractor rules > "$f"
    INC=$(python -c "import json,sys;print(json.load(open('$f'))['utterance']['incident_id'])")
  else
    python -m f2r.cli --db "$DB" add "$s" --incident "$INC" --extractor rules > "$f"
  fi
done <<'S'
gave 0.3 mg adrenaline IM
gave point three milligrams of adrenaline IM two mins ago
pushed 4 mg ondansetron IV
aspirin 300 mg PO at 10 40
fentanyl one hundred and fifty micrograms IV just now
morphine 5 mg IV, pain score 8, no nausea
gave aspirin
patient allergic to morphine
started CPR and gave adrenaline 1 mg IV
ondansetron 4, no sorry, 2 mg IV
S
{
  echo "# commit: $C"
  echo '$ python -m f2r.cli --db sample.sqlite verify    # before tamper'
  python -m f2r.cli --db "$DB" verify && echo "exit code: 0" || echo "exit code: $?"
  echo
  echo '$ python scripts/tamper.py --db sample.sqlite --seq 5 --dose 1500    # fentanyl 150 mcg -> 1500'
  python scripts/tamper.py --db "$DB" --seq 5 --dose 1500
  echo
  echo '$ python -m f2r.cli --db sample.sqlite verify    # after tamper'
  python -m f2r.cli --db "$DB" verify && echo "exit code: 0" || echo "exit code: $?"
} > $OUT/verify_before_after_tamper.txt 2>&1
{ echo "# commit: $C"; python -m pytest -v -p no:cacheprovider tests/test_audit_tamper.py 2>&1; } > $OUT/tamper_suite_pytest.txt
python - "$OUT/worst_failures.json" <<'PY'
import json, sys
from datetime import datetime
from jatayu.extract.rules import RulesExtractor
from jatayu.lexicon import Lexicon
from jatayu.validate import validate_all
path = sys.argv[1]
rows = json.load(open(path))
lex = Lexicon.load(); x = RulesExtractor(lex); cap = datetime.now().astimezone()
for r in rows:
    out = []
    for e in validate_all(x.extract(r["input"], cap), lex, []):
        d = {"drug": e.drug.value, "dose": e.dose_value.value, "unit": e.dose_unit.value, "route": e.route.value} \
            if e.kind == "medication" else {"procedure": e.procedure.value}
        out.append({**d, "time_source": e.time_source, "flags": [f.code for f in e.flags]})
    r["output"] = out
json.dump(rows, open(path, "w"), indent=2); open(path, "a").write("\n")
PY
GPU=$(nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo none)
{ echo "# python -m pytest -v -rs  (full suite, nothing deselected)"; echo "# commit: $C  date: $(date -Iseconds)"
  echo "# GPU at start: $GPU"; echo
  python -m pytest -v -rs -p no:cacheprovider 2>&1; } > $OUT/pytest_output.txt
tail -1 $OUT/pytest_output.txt
echo "M1 packet rebuilt at $C"
