from pathlib import Path
import unittest

class ExplainerTests(unittest.TestCase):
    def test_standalone_learning_page_has_two_separate_models(self):
        page = Path(__file__).with_name('how-it-works.html')
        self.assertTrue(page.exists(), 'The learning page must exist')
        text = page.read_text()
        for term in ['LinearSVC', 'HistGradientBoostingClassifier', 'Isotonic', 'prefers-reduced-motion', 'Not investment advice', 'id="next"', 'id="play"', 'id="back"', 'id="example"']:
            self.assertIn(term, text)
        self.assertNotIn('<script src=', text)

if __name__ == '__main__':
    unittest.main()
