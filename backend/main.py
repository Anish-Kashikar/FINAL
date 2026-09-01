"""Deterministic, simulation-only scheduling API for the RAILSYNC AI demo."""
import csv
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from ortools.sat.python import cp_model

ROOT = Path(__file__).resolve().parents[1]; DATA = ROOT / "seed_data"; START = datetime(2026, 9, 1)
PRIORITY_WEIGHTS = {"severity": 30, "urgency": 20, "failure": 20, "criticality": 20, "traffic": 10}
OBJECTIVE_WEIGHTS = {"critical_bonus": 100000, "high_bonus": 25000, "priority_score": 1000}
SCALE = {"Low": 30, "Medium": 60, "High": 85, "Critical": 100}
app = FastAPI(title="RAILSYNC AI API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

def read(name):
    with open(DATA / name, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
assets, tasks, trains, windows, locations = map(read, ["assets.csv", "maintenance_tasks.csv", "trains.csv", "railway_blocks.csv", "locations.csv"])
by_asset = {x["asset_id"]: x for x in assets}; by_loc = {x["location_id"]: x for x in locations}; latest = {}; approvals = {}
def dt(x): return datetime.strptime(x, "%Y-%m-%d %H:%M:%S")
def finish(days): return START + timedelta(days=days)
def overlaps(a, b, c, d): return max(a, c) < min(b, d)
def minutes(task): return int(task["estimated_duration_minutes"])

def score(task):
    urgency = max(0, min(100, 120 - max(0, (dt(task["deadline"]) - START).total_seconds() / 3600)))
    factors = {"severity": SCALE[task["severity"]], "urgency": urgency, "failure": float(task["failure_probability"]) * 100, "criticality": SCALE[task["asset_criticality"]], "traffic": SCALE[task["traffic_impact"]]}
    total = round(sum(factors[k] * PRIORITY_WEIGHTS[k] / 100 for k in PRIORITY_WEIGHTS), 1)
    level = "CRITICAL" if total >= 75 else "HIGH" if total >= 58 else "MEDIUM" if total >= 40 else "LOW"
    return total, level, factors
def view(task):
    value, level, factors = score(task)
    return {**task, "asset": by_asset.get(task["asset_id"], {}), "location": by_loc.get(task["location_id"], {}), "priority_score": value, "priority_level": level, "reason": f"{task['severity']} severity, {int(float(task['failure_probability'])*100)}% failure risk and {task['asset_criticality'].lower()} criticality.", "contributing_factors": factors}
def scoped_tasks(days): return sorted((view(t) for t in tasks if t["status"] != "Completed" and dt(t["earliest_start"]) < finish(days)), key=lambda t: (-t["priority_score"], t["task_id"]))
def feasible(task, block, cutoff): return block["corridor"] == task["corridor"] and dt(block["start_time"]) < cutoff and minutes(task) <= int(block["duration_minutes"]) and dt(block["start_time"]) >= dt(task["earliest_start"]) and dt(block["end_time"]) <= dt(task["deadline"])

def block_conflicts(block, cutoff):
    """A unique conflict is a genuine train-to-maintenance-block overlap."""
    out = []
    for train in trains:
        if train["corridor"] != block["corridor"] or dt(train["scheduled_start"]) >= cutoff: continue
        if overlaps(dt(block["start_time"]), dt(block["end_time"]), dt(train["scheduled_start"]), dt(train["scheduled_end"])):
            m = int((min(dt(block["end_time"]), dt(train["scheduled_end"])) - max(dt(block["start_time"]), dt(train["scheduled_start"]))).total_seconds() / 60)
            out.append({"conflict_id": f"{block['block_id']}:{train['train_id']}", "conflict_type": "TRAIN_BLOCK", "severity": "HIGH" if train["priority"] == "High" else "MEDIUM", "block_id": block["block_id"], "train_id": train["train_id"], "corridor": block["corridor"], "overlap_minutes": m, "explanation": f"{train['train_number']} occupies this maintenance block for {m} minutes."})
    return out
def conflicts(days): return [record for block in windows if dt(block["start_time"]) < finish(days) for record in block_conflicts(block, finish(days))]

def decorate(assignments, cutoff, label):
    result = []
    for block, chosen in assignments:
        if not chosen: continue
        used = sum(minutes(t) for t in chosen); utilization = round(used / int(block["duration_minutes"]) * 100, 1)
        if utilization > 100: raise ValueError(f"Utilization overflow: {block['block_id']}")
        result.append({**block, "tasks": chosen, "solver_status": label, "priority": max(t["priority_level"] for t in chosen), "departments": sorted({t["required_department"] for t in chosen}), "scheduled_minutes": used, "utilization_percentage": utilization, "train_conflicts": block_conflicts(block, cutoff), "group_reason": f"{len(chosen)} task(s) use {used} of {block['duration_minutes']} available minutes without department double-booking."})
    return result

def baseline_plan(days):
    """Manual proxy: earliest-first, same feasible windows/capacity, no train conflict screen."""
    cutoff = finish(days); pool = sorted(scoped_tasks(days), key=lambda t: (dt(t["earliest_start"]), t["task_id"])); used = set(); assignments = []
    for block in sorted((b for b in windows if dt(b["start_time"]) < cutoff), key=lambda b: (dt(b["start_time"]), b["block_id"])):
        chosen = []; used_minutes = 0; departments = set()
        for task in pool:
            if task["task_id"] in used or not feasible(task, block, cutoff) or task["required_department"] in departments: continue
            if len(chosen) >= int(block["capacity"]) or used_minutes + minutes(task) > int(block["duration_minutes"]): continue
            chosen.append(task); used.add(task["task_id"]); used_minutes += minutes(task); departments.add(task["required_department"])
        assignments.append((block, chosen))
    return decorate(assignments, cutoff, "BASELINE")

def railopt_plan(days):
    cutoff = finish(days); pool = scoped_tasks(days); safe = [b for b in windows if dt(b["start_time"]) < cutoff and not block_conflicts(b, cutoff)]
    model = cp_model.CpModel(); assigned = {}
    for ti, task in enumerate(pool):
        choices = []
        for bi, block in enumerate(safe):
            if feasible(task, block, cutoff):
                assigned[ti, bi] = model.NewBoolVar(f"t{ti}b{bi}"); choices.append(assigned[ti, bi])
        if choices: model.Add(sum(choices) <= 1)
    for bi, block in enumerate(safe):
        vars_ = [assigned[ti, bi] for ti in range(len(pool)) if (ti, bi) in assigned]
        if vars_:
            model.Add(sum(vars_) <= int(block["capacity"]))
            model.Add(sum(minutes(pool[ti]) * assigned[ti, bi] for ti in range(len(pool)) if (ti, bi) in assigned) <= int(block["duration_minutes"]))
        for department in {t["required_department"] for t in pool}:
            same = [assigned[ti, bi] for ti, task in enumerate(pool) if task["required_department"] == department and (ti, bi) in assigned]
            if same: model.Add(sum(same) <= 1)
    def objective(ti, var):
        task = pool[ti]; bonus = OBJECTIVE_WEIGHTS["critical_bonus"] if task["priority_level"] == "CRITICAL" else OBJECTIVE_WEIGHTS["high_bonus"] if task["priority_level"] == "HIGH" else 0
        return (int(task["priority_score"] * OBJECTIVE_WEIGHTS["priority_score"]) + bonus) * var
    model.Maximize(sum(objective(ti, var) for (ti, _), var in assigned.items()))
    solver = cp_model.CpSolver(); solver.parameters.max_time_in_seconds = 4; solver.parameters.num_search_workers = 1; status = solver.Solve(model)
    label = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE"}.get(status, solver.StatusName(status))
    return decorate([(block, [pool[ti] for ti in range(len(pool)) if (ti, bi) in assigned and status in (cp_model.OPTIMAL, cp_model.FEASIBLE) and solver.Value(assigned[ti, bi])]) for bi, block in enumerate(safe)], cutoff, label)

def validate(blocks, days):
    errors = []; seen = set(); cutoff = finish(days)
    for block in blocks:
        if not 0 <= block["utilization_percentage"] <= 100 or sum(minutes(t) for t in block["tasks"]) > int(block["duration_minutes"]): errors.append({"type": "BLOCK_DURATION", "block_id": block["block_id"]})
        if len(block["tasks"]) > int(block["capacity"]): errors.append({"type": "BLOCK_CAPACITY", "block_id": block["block_id"]})
        if len({t["required_department"] for t in block["tasks"]}) != len(block["tasks"]): errors.append({"type": "DEPARTMENT_DOUBLE_BOOKING", "block_id": block["block_id"]})
        for task in block["tasks"]:
            if task["task_id"] in seen: errors.append({"type": "TASK_DUPLICATED", "task_id": task["task_id"]})
            if not feasible(task, block, cutoff): errors.append({"type": "INFEASIBLE_WINDOW", "task_id": task["task_id"]})
            seen.add(task["task_id"])
    return errors
def metrics(days, blocks):
    pool = scoped_tasks(days); planned = [t for b in blocks for t in b["tasks"]]; block_minutes = sum(int(b["duration_minutes"]) for b in blocks); scheduled = sum(minutes(t) for t in planned); errors = validate(blocks, days)
    critical_total = sum(t["priority_level"] == "CRITICAL" for t in pool); high_total = sum(t["priority_level"] == "HIGH" for t in pool); total_risk = sum(t["priority_score"] * float(t["failure_probability"]) for t in pool); mitigated = sum(t["priority_score"] * float(t["failure_probability"]) for t in planned)
    m = {"tasks_scheduled": len(planned), "tasks_unscheduled": len(pool)-len(planned), "overall_task_completion": round(100*len(planned)/len(pool),1) if pool else 0, "critical_tasks_completed": sum(t["priority_level"] == "CRITICAL" for t in planned), "high_priority_tasks_completed": sum(t["priority_level"] == "HIGH" for t in planned), "planned_blocks": len(blocks), "block_utilization": round(100*scheduled/block_minutes,1) if block_minutes else 0, "train_block_conflicts": sum(len(b["train_conflicts"]) for b in blocks), "constraint_violations": len(errors), "feasible": not errors, "asset_availability": round(88 + (10*mitigated/total_risk if total_risk else 0), 2)}
    m["critical_task_coverage"] = round(100*m["critical_tasks_completed"]/critical_total,1) if critical_total else 0; m["high_priority_coverage"] = round(100*m["high_priority_tasks_completed"]/high_total,1) if high_total else 0
    m["plan_score"] = round(.35*m["critical_task_coverage"]+.2*m["high_priority_coverage"]+.2*m["overall_task_completion"]+.15*m["block_utilization"]+(10 if m["feasible"] and not m["train_block_conflicts"] else 0),1)
    return m, errors
def compare(a, b, lower=False):
    diff = b-a; return {"baseline": a, "railopt": b, "difference": diff, "percentage": round(100*diff/a,1) if a else None, "direction": "lower" if lower else "higher"}
def experiment(days):
    base, opt = baseline_plan(days), railopt_plan(days); bm, be = metrics(days, base); om, oe = metrics(days, opt)
    fields = [("tasks_scheduled",False),("critical_tasks_completed",False),("high_priority_tasks_completed",False),("train_block_conflicts",True),("block_utilization",False),("asset_availability",False),("constraint_violations",True)]
    return {"planning_horizon_days":days,"generated_at":datetime.now().isoformat(timespec="seconds"),"methodology":"Baseline schedules earliest first-feasible work using the same data, windows, duration, capacity and department constraints. RAILSYNC uses CP-SAT with the same inputs and excludes train-occupied blocks.","objective_weights":OBJECTIVE_WEIGHTS,"baseline":{"blocks":base,"metrics":bm,"violations":be},"railopt":{"blocks":opt,"metrics":om,"violations":oe},"comparison":{key:compare(bm[key],om[key],lower) for key,lower in fields}}
def current(days):
    global latest
    if latest.get("planning_horizon_days") != days: latest = experiment(days)
    return latest
def quality():
    issues=[]
    for block in windows:
        if dt(block["end_time"])-dt(block["start_time"]) != timedelta(minutes=int(block["duration_minutes"])): issues.append({"type":"BLOCK_DURATION","record":block["block_id"],"severity":"HIGH"})
    return issues

@app.get("/api/health")
def health(): return {"status":"healthy","dataset":"DEMO / SIMULATION DATA","validation_issues":len(quality())}
@app.get("/api/assets")
def get_assets(): return [{"asset":a,"location":by_loc.get(a["location_id"])} for a in assets]
@app.get("/api/maintenance")
def maintenance(horizon:int=Query(7,ge=1,le=30)): return scoped_tasks(horizon)
@app.get("/api/trains")
def train_ops(horizon:int=Query(7,ge=1,le=30)):
    active=[t for t in trains if dt(t["scheduled_start"])<finish(horizon)]; corridors=sorted({t["corridor"] for t in active})
    return {"trains":active,"windows":[b for b in windows if dt(b["start_time"])<finish(horizon)],"occupancy":[{"corridor":c,"trains":sum(t["corridor"]==c for t in active),"passenger":sum("Passenger" in t["train_name"] and t["corridor"]==c for t in active),"freight":sum("Freight" in t["train_name"] and t["corridor"]==c for t in active)} for c in corridors]}
@app.get("/api/conflicts")
def get_conflicts(horizon:int=Query(7,ge=1,le=30)): return conflicts(horizon)
@app.get("/api/data-quality")
def data_quality(): return {"status":"VALID" if not quality() else "REVIEW","issues":quality(),"records":{"assets":len(assets),"tasks":len(tasks),"trains":len(trains),"blocks":len(windows)}}
@app.post("/api/experiment/run")
@app.post("/api/optimizer/run")
def run(horizon:int=Query(7,ge=1,le=30)):
    global latest; latest=experiment(horizon); return latest
@app.get("/api/experiment")
@app.get("/api/optimizer/latest")
def get_plan(horizon:int=Query(7,ge=1,le=30)): return current(horizon)
@app.post("/api/plans/{block_id}/approval")
def approve(block_id:str,action:str=Query(...,pattern="^(approve|reject|modify)$")):
    block=next((b for b in current(7)["railopt"]["blocks"] if b["block_id"]==block_id),None)
    if not block: raise HTTPException(status_code=404,detail="Recommended block not found")
    approvals[block_id]={"action":action,"timestamp":datetime.now().isoformat(timespec="seconds")}; block["approval"]=approvals[block_id]; return {"block_id":block_id,**approvals[block_id]}
@app.get("/api/analytics")
def analytics(horizon:int=Query(7,ge=1,le=30)):
    x=current(horizon); return {"assets":len(assets),"tasks":len(tasks),"by_severity":[{"name":k,"value":sum(t["severity"]==k for t in tasks)} for k in SCALE],"by_condition":[{"name":k,"value":sum(a["condition"]==k for a in assets)} for k in ["Good","Fair","Poor","Critical"]],"baseline":x["baseline"]["metrics"],"railopt":x["railopt"]["metrics"],"comparison":x["comparison"]}
