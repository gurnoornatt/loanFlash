import unittest
from unittest.mock import patch, mock_open, MagicMock
import requests
import os
from document_processor import process_document

class TestDocumentProcessor(unittest.TestCase):
    def setUp(self):
        self.mock_pdf_path = "test.pdf"
        
        # Mock API response data
        self.mock_api_response = {
            "income": "120000",
            "credit_score": "750",
            "debt": "50000",
            "property_value": "500000"
        }

    @patch('requests.post')
    @patch('document_processor.create_client')
    @patch('os.path.exists')
    def test_successful_document_processing(self, mock_exists, mock_create_client, mock_post):
        # Mock file existence check
        mock_exists.return_value = True
        
        # Mock the API response
        mock_post.return_value.json.return_value = self.mock_api_response
        mock_post.return_value.raise_for_status.return_value = None
        
        # Create a mock Supabase client
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_insert = MagicMock()
        
        # Setup the mock chain
        mock_create_client.return_value = mock_supabase
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = {"status": "success"}
        
        # Mock environment variables
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'ADDY_API_KEY': 'test-addy-key'
        }):
            # Mock file open
            with patch('builtins.open', mock_open(read_data=b'fake pdf content')):
                result = process_document(self.mock_pdf_path)
        
        # Verify the result structure
        self.assertTrue(result['success'], f"Process failed with error: {result.get('error', 'Unknown error')}")
        self.assertEqual(result['data']['income'], 120000.0)
        self.assertEqual(result['data']['credit_score'], 750)
        self.assertEqual(result['data']['debt'], 50000.0)
        self.assertEqual(result['data']['property_value'], 500000.0)
        
        # Verify API calls were made correctly
        mock_post.assert_called_once()
        mock_create_client.assert_called_once_with('https://test.supabase.co', 'test-key')
        mock_supabase.table.assert_called_once_with('borrowers')
        mock_table.insert.assert_called_once()
    
    @patch('os.path.exists')
    def test_missing_file(self, mock_exists):
        # Mock file not existing
        mock_exists.return_value = False
        
        result = process_document("nonexistent.pdf")
        self.assertFalse(result['success'])
        self.assertEqual(result['error_type'], 'FileNotFoundError')
    
    def test_missing_env_vars(self):
        # Test with empty environment
        with patch.dict('os.environ', {}, clear=True):
            result = process_document(self.mock_pdf_path)
            self.assertFalse(result['success'])
            self.assertEqual(result['error_type'], 'ValueError')
            self.assertIn('Missing required environment variables', result['error'])

if __name__ == '__main__':
    unittest.main() 