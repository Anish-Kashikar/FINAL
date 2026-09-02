"""Run: python -m backend.ml.train"""
import csv, json
from datetime import datetime
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib
from .model import DATA, ARTIFACTS, MODEL_FILE, METADATA_FILE, SEED, generate_history

def read(name):
    with open(DATA / name, newline="", encoding="utf-8") as file: return list(csv.DictReader(file))
def train():
    tasks, assets = read("maintenance_tasks.csv"), read("assets.csv"); history=generate_history(tasks,assets)
    x,y=zip(*history); x_train,x_test,y_train,y_test=train_test_split(list(x),list(y),test_size=.25,stratify=y,random_state=SEED)
    pipeline=Pipeline([("vectorizer",DictVectorizer(sparse=True)),("model",RandomForestClassifier(n_estimators=40,min_samples_leaf=3,random_state=SEED,n_jobs=1,class_weight="balanced"))])
    pipeline.fit(x_train,y_train); predictions=pipeline.predict(x_test); probabilities=pipeline.predict_proba(x_test)[:,1]
    metrics={"model":"RandomForestClassifier","training_data":"Simulated Historical Data","target":"failure_within_30_days","trained_at":datetime.now().isoformat(timespec="seconds"),"random_seed":SEED,"training_samples":len(x_train),"test_samples":len(x_test),"positive_class_count":sum(y),"accuracy":round(accuracy_score(y_test,predictions),3),"precision":round(precision_score(y_test,predictions,zero_division=0),3),"recall":round(recall_score(y_test,predictions,zero_division=0),3),"f1":round(f1_score(y_test,predictions,zero_division=0),3),"roc_auc":round(roc_auc_score(y_test,probabilities),3)}
    ARTIFACTS.mkdir(parents=True,exist_ok=True); joblib.dump(pipeline,MODEL_FILE); METADATA_FILE.write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    with open(DATA / "ml_training_history.csv","w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=[*x[0].keys(),"failure_within_30_days"]); writer.writeheader(); [writer.writerow({**row,"failure_within_30_days":target}) for row,target in history]
    return metrics
if __name__ == "__main__": print(json.dumps(train(),indent=2))
