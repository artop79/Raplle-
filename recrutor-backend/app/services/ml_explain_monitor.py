import shap
import lime.lime_tabular
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime

# Пути для журналов и мониторинга
FP_FN_LOG = 'ml_fp_fn_log.jsonl'
DRIFT_LOG = 'ml_drift_log.jsonl'

class MLExplainMonitor:
    def __init__(self, model, feature_names):
        self.model = model
        self.feature_names = feature_names
        self.shap_explainer = shap.TreeExplainer(model)
        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=np.zeros((1, len(feature_names))),
            feature_names=feature_names,
            mode='classification'
        )

    def explain_shap(self, X):
        shap_values = self.shap_explainer.shap_values(X)
        return shap_values

    def explain_lime(self, X_row):
        exp = self.lime_explainer.explain_instance(X_row, self.model.predict_proba, num_features=8)
        return exp.as_list()

    def save_shap_plot(self, X_row, candidate_id):
        shap_values = self.shap_explainer.shap_values(X_row)
        plt.figure()
        shap.summary_plot(shap_values, X_row, feature_names=self.feature_names, show=False)
        fname = f'shap_{candidate_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(fname, bbox_inches='tight')
        plt.close()
        return fname

    def log_fp_fn(self, candidate_id, features, true_label, pred_label, prob):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'candidate_id': candidate_id,
            'features': features,
            'true_label': true_label,
            'pred_label': pred_label,
            'prob': float(prob)
        }
        with open(FP_FN_LOG, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_drift(self, drift_metrics):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'drift_metrics': drift_metrics
        }
        with open(DRIFT_LOG, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    @staticmethod
    def check_drift(reference_scores, current_scores, reference_hr, current_hr):
        # Сравниваем распределения с помощью простых метрик (например, среднее, std, KS-тест)
        from scipy.stats import ks_2samp
        drift = {}
        drift['score_mean_ref'] = float(np.mean(reference_scores))
        drift['score_mean_cur'] = float(np.mean(current_scores))
        drift['score_ks_p'] = float(ks_2samp(reference_scores, current_scores).pvalue)
        drift['hr_mean_ref'] = float(np.mean(reference_hr))
        drift['hr_mean_cur'] = float(np.mean(current_hr))
        drift['hr_ks_p'] = float(ks_2samp(reference_hr, current_hr).pvalue)
        return drift

    @staticmethod
    def get_fp_fn_log():
        if not os.path.exists(FP_FN_LOG):
            return []
        with open(FP_FN_LOG, 'r') as f:
            return [json.loads(line) for line in f]

    @staticmethod
    def get_drift_log():
        if not os.path.exists(DRIFT_LOG):
            return []
        with open(DRIFT_LOG, 'r') as f:
            return [json.loads(line) for line in f]
