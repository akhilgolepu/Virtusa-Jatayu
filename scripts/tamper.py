"""Tamper demo: silently change a dose inside one audit row, bypassing the append-only trigger.

Usage: python scripts/tamper.py --db data/jatayu.sqlite --seq 2 --dose 10
Then press "Verify chain" (or call AuditLog.verify()) and watch it name the broken row.
"""
import argparse
import json
import sqlite3


def set_doses(node, dose: float) -> int:
    """Rewrite every dose found in the payload (FHIR dosage.dose.value or a bare 'dose' number)."""
    changed = 0
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "dose" and isinstance(val, dict) and "value" in val:
                val["value"] = dose
                changed += 1
            elif key == "dose" and isinstance(val, (int, float)):
                node[key] = dose
                changed += 1
            else:
                changed += set_doses(val, dose)
    elif isinstance(node, list):
        changed += sum(set_doses(v, dose) for v in node)
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    ap.add_argument("--seq", type=int, required=True)
    ap.add_argument("--dose", type=float, required=True)
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    row = con.execute("SELECT payload_json FROM audit_log WHERE seq = ?", (args.seq,)).fetchone()
    if row is None:
        raise SystemExit(f"no row with seq {args.seq}")
    payload = json.loads(row[0])
    n = set_doses(payload, args.dose)
    trigger_sql = con.execute("SELECT sql FROM sqlite_master WHERE name = 'audit_no_update'").fetchone()[0]
    con.execute("DROP TRIGGER audit_no_update")
    con.execute("UPDATE audit_log SET payload_json = ? WHERE seq = ?",
                (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False), args.seq))
    con.execute(trigger_sql)
    con.commit()
    print(f"tampered seq {args.seq}: {n} dose value(s) set to {args.dose} (trigger dropped and restored)")


if __name__ == "__main__":
    main()
