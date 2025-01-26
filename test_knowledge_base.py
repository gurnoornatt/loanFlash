import unittest
from unittest.mock import patch, MagicMock
from knowledge_base import KnowledgeBaseManager
import os
import json
from datetime import datetime
import pandas as pd

class TestKnowledgeBaseManager(unittest.TestCase):
    @patch('knowledge_base.create_client')
    def setUp(self, mock_create_client):
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key'
        })
        self.env_patcher.start()
        
        # Mock Supabase client
        self.mock_supabase = MagicMock()
        mock_create_client.return_value = self.mock_supabase
        
        # Create test instance
        self.kb = KnowledgeBaseManager()
        
        # Sample guideline data
        self.sample_guideline = {
            'rule_name': 'FHA-LTV-2024',
            'rule_text': 'For FHA loans, the maximum LTV is 96.5% with a credit score of 580 or higher.',
            'source': 'fha',
            'category': 'LTV',
            'state': None,
            'version_hash': 'abc123',
            'last_updated': datetime.now().isoformat()
        }
    
    def tearDown(self):
        self.env_patcher.stop()
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        dirty_text = "This is a  test\nwith multiple   spaces and\tspecial chars!@#$"
        clean_text = self.kb._clean_text(dirty_text)
        self.assertEqual(clean_text, "This is a test with multiple spaces and special chars")
    
    def test_detect_category(self):
        """Test category detection"""
        test_cases = [
            ("LTV Requirements", "Maximum loan-to-value ratio is 95%", "LTV"),
            ("Income Guidelines", "Monthly income must be verified", "income"),
            ("Credit Score", "Minimum FICO score required is 620", "credit_score"),
            ("Random Text", "No specific category indicators", "general")
        ]
        
        for title, content, expected in test_cases:
            category = self.kb._detect_category(title, content)
            self.assertEqual(category, expected)
    
    def test_detect_state(self):
        """Test state detection"""
        test_cases = [
            ("Guidelines for California residents", "California"),
            ("No state mentioned here", None),
            ("Requirements for New York properties", "New York")  # Changed to single state test
        ]
        
        for content, expected in test_cases:
            state = self.kb._detect_state(content)
            self.assertEqual(state, expected)
    
    @patch('knowledge_base.requests.get')
    def test_fetch_guidelines(self, mock_get):
        """Test guideline fetching"""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = """
        <h2>LTV Requirements</h2>
        <p>Maximum LTV is 95%</p>
        <h2>Credit Guidelines</h2>
        <p>Minimum credit score is 620</p>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        guidelines = self.kb.fetch_guidelines('fha')
        self.assertTrue(isinstance(guidelines, list))
        self.assertTrue(len(guidelines) > 0)
        self.assertIn('rule_name', guidelines[0])
        self.assertIn('rule_text', guidelines[0])
        self.assertEqual(guidelines[0]['rule_name'], 'LTV Requirements')
        self.assertIn('Maximum LTV is 95%', guidelines[0]['rule_text'])
    
    def test_update_knowledge_base(self):
        """Test knowledge base update process"""
        # Mock Supabase responses
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[])
        self.mock_supabase.table().select.return_value = mock_select
        
        # Mock guideline fetching
        with patch.object(self.kb, 'fetch_guidelines') as mock_fetch:
            mock_fetch.return_value = [self.sample_guideline]
            
            stats = self.kb.update_knowledge_base()
            
            self.assertIn('new_guidelines', stats)
            self.assertIn('updated_guidelines', stats)
            self.assertIn('errors', stats)
            self.assertIn('sources_processed', stats)
    
    def test_export_guidelines(self):
        """Test guideline export functionality"""
        # Mock Supabase response
        mock_result = MagicMock()
        mock_result.data = [self.sample_guideline]
        self.mock_supabase.table().select().execute.return_value = mock_result
        
        # Test CSV export
        csv_file = self.kb.export_guidelines('csv')
        self.assertTrue(csv_file.endswith('.csv'))
        self.assertTrue(os.path.exists(csv_file))
        
        # Test JSON export
        json_file = self.kb.export_guidelines('json')
        self.assertTrue(json_file.endswith('.json'))
        self.assertTrue(os.path.exists(json_file))
        
        # Clean up test files
        os.remove(csv_file)
        os.remove(json_file)
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test missing credentials
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                KnowledgeBaseManager()
        
        # Test failed guideline fetch
        with patch('knowledge_base.requests.get', side_effect=Exception("Connection error")):
            guidelines = self.kb.fetch_guidelines('fha')
            self.assertEqual(guidelines, [])
        
        # Test failed export
        self.mock_supabase.table().select().execute.return_value = MagicMock(data=[])
        with self.assertRaises(ValueError):
            self.kb.export_guidelines()

if __name__ == '__main__':
    unittest.main() 