# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import glob
import json
import argparse
import numpy as np
import pandas as pd
import joblib
from datetime import timedelta
from azureml.core.model import Model

model = None
explainer = None
collector = None

def init():
    global model, explainer, collector
    print("Started batch scoring by running init()")
    
    parser = argparse.ArgumentParser('batch_scoring')
    parser.add_argument('--model_name', type=str, help='Model to use for batch scoring')
    parser.add_argument('--enable_monitoring', type=str, help="Enable Monitoring", default="false")
    parser.add_argument('--table_name', type=str, help="Table Name for logging data")
    args, _ = parser.parse_known_args()
    
    model_path = Model.get_model_path(args.model_name)
    print(f"Model path: {model_path}")

    if 'model.pkl' in model_path:
        model = joblib.load(model_path)
    else:
        model = joblib.load(os.path.join(model_path, 'model.pkl'))

        # load the explainer
    explainer_path = os.path.join(Model.get_model_path(args.model_name), "explainer")
    #explainer = joblib.load(explainer_path)

    if (args.enable_monitoring.lower() == 'true' or args.enable_monitoring == '1' or args.enable_monitoring.lower() == 'yes'):
        from obs.collector import Online_Collector
        collector = Online_Collector(args.table_name)
        
def run(file_list):
    
    print(f"Files to process: {file_list}")
    results = pd.DataFrame(columns=["Sno", "ProbaGoodCredit", "ProbaBadCredit", "FeatureImportance"])
    all_results = []
    for filename in file_list:
        
        df = pd.read_csv(filename)
        sno = df["Sno"]
        df = df.drop("Sno", axis=1)
        
        proba = model.predict_proba(df)
        proba = pd.DataFrame(data=proba, columns=["ProbaGoodCredit", "ProbaBadCredit"])

        #explanation = explainer.explain_local(df)
        # sorted feature importance values and feature names
        #sorted_local_importance_names = explanation.get_ranked_local_names()
        #sorted_local_importance_values = explanation.get_ranked_local_values()
        # get explanations in dictionnary
        #explanations = []
        #for i, j in zip(sorted_local_importance_names[0], sorted_local_importance_values[0]):
        #    explanations.append(dict(zip(i, j)))
        #explanation = pd.DataFrame(data=explanations, columns=["FeatureImportance"])

        #result = pd.concat([sno, proba, explanation], axis=1)
        result = pd.concat([sno, proba], axis=1)
        results = results.append(result)
        all_results.append(pd.concat([df, proba], axis=1))
        print(f"Batch scored: {filename}")

    if collector:
        full_results = pd.concat(all_results)
        full_results["timestamp"] = [pd.to_datetime('now') - timedelta(days=x) for x in range(len(full_results))]
        collector.batch_collect(full_results)

    return results
