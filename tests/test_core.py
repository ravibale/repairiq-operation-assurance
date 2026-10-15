import csv
import tempfile
import unittest
from pathlib import Path
from repairiq.core import create_report, load_estimate

HEADERS = ["document_id","revision","vehicle_id","line_number","panel","description","labour_hours","hourly_rate_gbp"]

def sample_rows():
    return [
        ["D1","1","V1","1","front bumper","Remove and refit front bumper","2","65"],
        ["D1","1","V1","2","front bumper","Front bumper removal","1","65"],
        ["D1","1","V1","3","front bumper","Refit front bumper","1","65"],
        ["D1","1","V1","4","front bumper","Replace front headlamp","1.5","65"],
        ["D1","1","V1","5","front bumper","Front headlamp replacement","1.5","65"],
        ["D1","1","V1","6","front bumper","Unknown OEM operation","1","65"],
    ]

class RepairIQCoreTest(unittest.TestCase):
    def make_csv(self, rows):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / 'estimate.csv'
        with path.open('w', newline='', encoding='utf8') as f:
            writer = csv.writer(f); writer.writerow(HEADERS); writer.writerows(rows)
        self.addCleanup(directory.cleanup)
        return path

    def test_detects_overlapping_and_duplicate_operations_with_sources(self):
        result = create_report(self.make_csv(sample_rows()))
        self.assertEqual([x['rule_id'] for x in result['findings']], ['DUP-001', 'OVL-002'])
        self.assertEqual(result['findings'][0]['source_lines'], [4,5])
        self.assertEqual(result['findings'][1]['source_lines'], [1,2,3])
        self.assertEqual(result['mapped_lines'], 5)
        self.assertEqual(result['unmapped_line_numbers'], [6])
        self.assertEqual(result['findings'][0]['reviewer_decision'], 'PENDING_HUMAN_REVIEW')
        self.assertEqual(len(result['source_sha256']), 64)

    def test_different_panels_do_not_trigger_duplicate(self):
        rows = sample_rows()[3:5]
        rows[1][4] = 'rear quarter'
        result = create_report(self.make_csv(rows))
        self.assertEqual(result['findings'], [])

    def test_unknown_operations_abstain(self):
        rows = [sample_rows()[-1]]
        result = create_report(self.make_csv(rows))
        self.assertEqual(result['mapped_lines'], 0)
        self.assertEqual(result['findings'], [])

    def test_invalid_negative_hours_rejected(self):
        rows = sample_rows()[:1]
        rows[0][6] = '-1'
        with self.assertRaisesRegex(ValueError, 'non-negative'):
            load_estimate(self.make_csv(rows))

    def test_mixed_documents_rejected(self):
        rows = sample_rows()[:2]
        rows[1][0] = 'D2'
        with self.assertRaisesRegex(ValueError, 'single document'):
            load_estimate(self.make_csv(rows))

    def test_duplicate_line_numbers_rejected(self):
        rows = sample_rows()[:2]
        rows[1][3] = '1'
        with self.assertRaisesRegex(ValueError, 'unique'):
            load_estimate(self.make_csv(rows))

    def test_same_input_yields_same_findings(self):
        path = self.make_csv(sample_rows())
        self.assertEqual(create_report(path), create_report(path))

if __name__ == '__main__':
    unittest.main()
