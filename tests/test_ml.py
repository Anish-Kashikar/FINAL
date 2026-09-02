import unittest
from backend.ml.model import MODEL_FILE, METADATA_FILE, features, load_metadata, predict
from backend.main import assets, scoped_tasks


class MLRiskTests(unittest.TestCase):
    def test_model_artifacts_and_metrics_exist(self):
        self.assertTrue(MODEL_FILE.exists())
        self.assertTrue(METADATA_FILE.exists())
        self.assertIn("roc_auc", load_metadata())

    def test_prediction_is_bounded_and_deterministic(self):
        task = scoped_tasks(7)[0]
        first = predict(task, task["asset"])
        second = predict(task, task["asset"])
        self.assertTrue(0 <= first[0] <= 1)
        self.assertEqual(first[0], second[0])
        self.assertTrue(first[1])

    def test_features_do_not_leak_target(self):
        task = scoped_tasks(7)[0]
        self.assertNotIn("failure_within_30_days", features(task, task["asset"]))

