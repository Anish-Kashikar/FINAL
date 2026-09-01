import unittest

from backend.main import apply_scenario, audit_trail, block_conflicts, experiment, finish, overlaps, run, scoped_tasks, trains, windows


class OptimizerValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = experiment(7)

    def test_utilization_is_never_over_capacity(self):
        for plan in (self.result["baseline"]["blocks"], self.result["railopt"]["blocks"]):
            self.assertTrue(all(0 <= block["utilization_percentage"] <= 100 for block in plan))

    def test_railopt_has_no_invalid_assignments(self):
        self.assertEqual(self.result["railopt"]["violations"], [])
        self.assertEqual(self.result["railopt"]["metrics"]["constraint_violations"], 0)

    def test_train_conflicts_are_unique_real_pairs(self):
        records = [record for block in windows for record in block_conflicts(block, finish(7))]
        self.assertEqual(len(records), len({record["conflict_id"] for record in records}))
        self.assertTrue(all(record["block_id"] != record["train_id"] for record in records))
        self.assertFalse(overlaps(finish(1), finish(1), finish(2), finish(3)))

    def test_optimizer_prioritizes_critical_work_and_avoids_occupied_blocks(self):
        baseline = self.result["baseline"]["metrics"]
        optimized = self.result["railopt"]["metrics"]
        self.assertGreaterEqual(optimized["critical_tasks_completed"], baseline["critical_tasks_completed"])
        self.assertEqual(optimized["train_block_conflicts"], 0)

    def test_experiment_is_deterministic_for_same_seed_data(self):
        repeat = experiment(7)
        self.assertEqual(self.result["comparison"], repeat["comparison"])
        self.assertEqual(len(scoped_tasks(7)), 672)

    def test_scenario_isolated_and_audited(self):
        before = len(trains)
        scenario = apply_scenario("unexpected_train", 7)
        self.assertEqual(len(trains), before)
        self.assertEqual(scenario["replanned"]["train_block_conflicts"], 0)
        self.assertTrue(any(event["event_type"] == "SCENARIO_APPLIED" for event in audit_trail()))

    def test_plan_versions_are_persisted(self):
        result = run(7)
        self.assertTrue(result["plan_id"].startswith("PLAN-"))


if __name__ == "__main__":
    unittest.main()
