from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from picking_logic import (
    DOWN, UP, EscapeProfile, PickingTransition,
    economy_pick_events, economy_pick_ramp_stages_v2,
    escape_profile_adjustment, escape_profile_crossing_status,
    normalize_picking_events,
)
from presets import OFF, TA, TI

PROFILES = (EscapeProfile.AUTO, EscapeProfile.USX, EscapeProfile.DSX, EscapeProfile.DBX)

def sn(stroke):
    return "D" if stroke == DOWN else "U" if stroke == UP else "."

def pn(state):
    return "TI" if state == TI else "TA" if state == TA else "."

def solve(states, profile):
    events = normalize_picking_events([states], [states], TI, TA, OFF, stage_id=f"diag:{profile.value}")
    decisions = economy_pick_events(events, cyclic=True, escape_profile=profile)
    return events, decisions

def stats(events, decisions, profile):
    attacks=[(e,d) for e,d in zip(events, decisions) if e.attack]
    out={"sweeps":0,"alternate_crossings":0,"compatible":0,"trapped":0}
    for i,(_e,d) in enumerate(attacks):
        t=d.transition_from_previous
        if t is PickingTransition.DIRECTIONAL_SWEEP:
            out["sweeps"]+=1
        elif t is PickingTransition.ALTERNATE_CROSSING:
            out["alternate_crossings"]+=1
            prev=attacks[i-1][1].stroke
            if prev in (DOWN,UP):
                status=escape_profile_crossing_status(profile, prev, t)
                if status in ("compatible","trapped"):
                    out[status]+=1
    return out

def discriminating(limit=8):
    found=[]
    for seq in product((TI,TA), repeat=5):
        states=list(seq)
        if len(set(states))<2:
            continue
        _,u=solve(states,EscapeProfile.USX)
        _,d=solve(states,EscapeProfile.DSX)
        if tuple(x.stroke for x in u)!=tuple(x.stroke for x in d):
            found.append(states)
            if len(found)>=limit:
                break
    return found

def self_test():
    failures=[]
    checks=[
        ("USX rewards UP escape", escape_profile_adjustment(EscapeProfile.USX,6,UP,5,DOWN)<0),
        ("USX penalizes DOWN escape", escape_profile_adjustment(EscapeProfile.USX,6,DOWN,5,UP)>0),
        ("DSX rewards DOWN escape", escape_profile_adjustment(EscapeProfile.DSX,6,DOWN,5,UP)<0),
        ("DSX penalizes UP escape", escape_profile_adjustment(EscapeProfile.DSX,6,UP,5,DOWN)>0),
        ("DBX accepts UP", escape_profile_crossing_status(EscapeProfile.DBX,UP,PickingTransition.ALTERNATE_CROSSING)=="compatible"),
        ("DBX accepts DOWN", escape_profile_crossing_status(EscapeProfile.DBX,DOWN,PickingTransition.ALTERNATE_CROSSING)=="compatible"),
        ("USX rewards downstroke sweep", escape_profile_adjustment(EscapeProfile.USX,6,DOWN,5,DOWN)<0),
        ("USX penalizes upstroke sweep", escape_profile_adjustment(EscapeProfile.USX,5,UP,6,UP)>0),
        ("DSX rewards upstroke sweep", escape_profile_adjustment(EscapeProfile.DSX,5,UP,6,UP)<0),
        ("DSX penalizes downstroke sweep", escape_profile_adjustment(EscapeProfile.DSX,6,DOWN,5,DOWN)>0),
        ("USX and DSX can differ", bool(discriminating(1))),
    ]
    for label,ok in checks:
        if not ok:
            failures.append(label)
    ramp_pattern=[[TA,TI,TI,TA],[TA,TI,TI,TA],[TA,TI,TI,TA],[TI,TA,TI,TA]]
    ramp=economy_pick_ramp_stages_v2(ramp_pattern,(1,2,3,4),TI,TA,OFF,escape_profile=EscapeProfile.USX)
    for beat in range(4):
        ref=ramp[4][beat]
        for active in (1,2,3,4):
            if beat<active and ramp[active][beat]!=ref:
                failures.append(f"USX Ramp persistent mismatch beat={beat} stage={active}")
                break
    return failures

def saved_profile(path):
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
        return str(data.get("picking",{}).get("escape_profile","auto"))
    except Exception:
        return "unavailable"

def build_report(git_head, settings):
    failures=self_test()
    lines=[
        "TittyTatter Picking Logic P7b Diagnostic",
        f"git_head={git_head}",
        f"saved_escape_profile={saved_profile(settings)}",
        "",
        "PROFILE RULES",
        "AUTO: no escape-motion preference",
        "USX: alternate string changes prefer previous stroke UP",
        "DSX: alternate string changes prefer previous stroke DOWN",
        "DBX: alternate string changes accept previous stroke UP or DOWN",
        "USX prefers downstroke sweeps; DSX prefers upstroke sweeps; DBX/AUTO keep sweep direction neutral.",
        "",
        "TRANSITION PROBES",
        f"USX after UP adjustment={escape_profile_adjustment(EscapeProfile.USX,6,UP,5,DOWN):g}",
        f"USX after DOWN adjustment={escape_profile_adjustment(EscapeProfile.USX,6,DOWN,5,UP):g}",
        f"DSX after DOWN adjustment={escape_profile_adjustment(EscapeProfile.DSX,6,DOWN,5,UP):g}",
        f"DSX after UP adjustment={escape_profile_adjustment(EscapeProfile.DSX,6,UP,5,DOWN):g}",
        "",
        "PROFILE-DISCRIMINATING CYCLIC PATTERNS",
    ]
    for i,states in enumerate(discriminating(),1):
        lines.append(f"CASE {i:02d} pattern={' '.join(pn(s) for s in states)}")
        for profile in PROFILES:
            events,decisions=solve(states,profile)
            s=stats(events,decisions,profile)
            strokes=" ".join(sn(d.stroke) for d in decisions)
            lines.append(f"  {profile.value.upper():4} strokes={strokes} sweeps={s['sweeps']} alt_cross={s['alternate_crossings']} compatible={s['compatible']} trapped={s['trapped']}")
    ramp_pattern=[[TA,TI,TI,TA],[TA,TI,TI,TA],[TA,TI,TI,TA],[TI,TA,TI,TA]]
    lines+=["","RAMP 1->2->3->4 PROFILE OUTPUT"]
    for profile in PROFILES:
        stages=economy_pick_ramp_stages_v2(ramp_pattern,(1,2,3,4),TI,TA,OFF,escape_profile=profile)
        lines.append(profile.value.upper())
        for active in (1,2,3,4):
            rows=["".join(sn(x) for x in row) for row in stages[active]]
            lines.append(f"  stage={active} rows={' | '.join(rows)}")
    lines+=["","SELF-TEST","PASS" if not failures else "FAIL"]
    lines += ["  "+x for x in failures]
    return "\n".join(lines)+"\n"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--git-head",default="unknown")
    p.add_argument("--output")
    p.add_argument("--settings",default=str(Path(__file__).with_name("tittytatter.settings.json")))
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    failures=self_test()
    if a.self_test:
        if failures:
            print("picking diagnostics FAIL")
            for x in failures: print("  "+x)
            return 1
        print("picking diagnostics OK")
        return 0
    report=build_report(a.git_head,a.settings)
    print(report,end="")
    if a.output:
        out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(report,encoding="utf-8")
        print(f"saved={out}")
    return 1 if failures else 0

if __name__=="__main__":
    raise SystemExit(main())
