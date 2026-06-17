import unittest

from src.database.pipeline_health import record_pipeline_event


class PipelineHealthTests(unittest.TestCase):
    def test_record_pipeline_event_requires_component(self):
        with self.assertRaises(ValueError):
            record_pipeline_event("", "success")

    def test_record_pipeline_event_requires_status(self):
        with self.assertRaises(ValueError):
            record_pipeline_event("collector", "")


if __name__ == "__main__":
    unittest.main()
