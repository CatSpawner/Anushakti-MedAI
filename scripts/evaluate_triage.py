from __future__ import annotations

import argparse
import pandas as pd

from hospital_ai_system.triage_rules import triage_rules
from hospital_ai_system.ml_triage import ml_triage


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    total = len(df)

    rules_dept_ok = 0
    rules_pri_ok = 0

    ml_dept_ok = 0
    ml_pri_ok = 0
    ml_used = 0

    for _, r in df.iterrows():
        s = str(r["symptoms_text"])
        exp_dept = str(r["expected_department"])
        exp_pri = str(r["expected_priority"])

        rr = triage_rules(s)
        rules_dept_ok += int(str(rr["department"]) == exp_dept)
        rules_pri_ok += int(str(rr["priority"]) == exp_pri)

        mr = ml_triage(s)
        if mr:
            ml_used += 1
            ml_dept_ok += int(mr.department == exp_dept)
            ml_pri_ok += int(mr.priority == exp_pri)

    print("RULES dept/prio accuracy:", rules_dept_ok / total, rules_pri_ok / total)
    if ml_used:
        print("ML dept/prio accuracy:", ml_dept_ok / ml_used, ml_pri_ok / ml_used)
    else:
        print("ML: model not found")


if __name__ == "__main__":
    main()