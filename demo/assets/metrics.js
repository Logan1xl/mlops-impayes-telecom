window.METRICS = {
 "test": {
  "n_test": 100000,
  "accuracy": 0.58161,
  "precision_macro": 0.4612356172584012,
  "recall_macro": 0.5048785161870154,
  "f1_macro": 0.4690313736394062,
  "f1_weighted": 0.5487217226083296,
  "recall_high": 0.6736005031898643,
  "precision_high": 0.4781083580471316,
  "auc_ovr_macro": 0.6501724091604152,
  "per_class": {
   "low": {
    "precision": 0.6987231730508014,
    "recall": 0.7540034446113819,
    "f1-score": 0.725311525107073,
    "support": 54578.0
   },
   "medium": {
    "precision": 0.2068753206772704,
    "recall": 0.0870316007597997,
    "f1-score": 0.12251967546871677,
    "support": 23164.0
   },
   "high": {
    "precision": 0.4781083580471316,
    "recall": 0.6736005031898643,
    "f1-score": 0.5592629203424287,
    "support": 22258.0
   },
   "accuracy": 0.58161,
   "macro avg": {
    "precision": 0.4612356172584011,
    "recall": 0.5048785161870153,
    "f1-score": 0.4690313736394061,
    "support": 100000.0
   },
   "weighted avg": {
    "precision": 0.5356870910034799,
    "recall": 0.58161,
    "f1-score": 0.5487217226083296,
    "support": 100000.0
   }
  },
  "confusion_matrix": {
   "labels": [
    "low",
    "medium",
    "high"
   ],
   "matrix": [
    [
     41152,
     6447,
     6979
    ],
    [
     11761,
     2016,
     9387
    ],
    [
     5983,
     1282,
     14993
    ]
   ]
  },
  "latency": {
   "p50_ms": 1.3724375021411106,
   "p95_ms": 1.54432739582262,
   "mean_ms": 1.40341833975981
  },
  "permutation_importance": {
   "operator": -0.00174,
   "account_type": 0.00019,
   "avg_monthly_spend_ngn": 0.006,
   "recharge_frequency_per_month": 0.01657,
   "late_payment_count": 0.01744,
   "payment_consistency_score": 0.02151,
   "tenure_months": 0.05029
  },
  "quality_gate": {
   "checks": {
    "f1_macro >= min": true,
    "recall_high >= min": true,
    "latency_p95 <= max": true,
    "no_regression_vs_production": true
   },
   "production_f1": null,
   "passed": true
  },
  "model": {
   "model_name": "impayes-default-risk",
   "version": 1,
   "model_type": "logreg",
   "run_id": "2805ad8037a34f63a0248c7b6dcd0d7a",
   "data_version": "517425048d17a19e74ea7d8eb3492de7",
   "git_commit": "03bb77f"
  }
 },
 "comparison": [
  {
   "model": "logreg",
   "run_id": "2805ad8037a34f63a0248c7b6dcd0d7a",
   "f1_macro": 0.46966169675536196,
   "recall_high": 0.6727468775271812,
   "auc_ovr_macro": 0.6505423620587844,
   "fit_seconds": 0.8912404580041766
  },
  {
   "model": "random_forest",
   "run_id": "5aca4d0d1ccf4c249657e96e133ca244",
   "f1_macro": 0.45278418339369814,
   "recall_high": 0.6677149788839968,
   "auc_ovr_macro": 0.6502039607543032,
   "fit_seconds": 10.226949584000977
  },
  {
   "model": "hist_gbm",
   "run_id": "4608a8a6c4e74b7c86e9d130cc50c7fa",
   "f1_macro": 0.45745163514433457,
   "recall_high": 0.6671758468865128,
   "auc_ovr_macro": 0.6476770424940342,
   "fit_seconds": 2.0940951250013313
  }
 ],
 "summary": {
  "accuracy": 0.5816,
  "f1_macro": 0.469,
  "recall_high": 0.6736,
  "precision_high": 0.4781,
  "auc_ovr_macro": 0.6502,
  "latency_p95_ms": 1.54,
  "quality_gate": true
 },
 "split": {
  "train": {
   "rows": 350000,
   "class_share": {
    "low": 0.5458,
    "medium": 0.2316,
    "high": 0.2226
   }
  },
  "val": {
   "rows": 50000,
   "class_share": {
    "low": 0.5458,
    "medium": 0.2316,
    "high": 0.2226
   }
  },
  "test": {
   "rows": 100000,
   "class_share": {
    "low": 0.5458,
    "medium": 0.2316,
    "high": 0.2226
   }
  }
 }
};
