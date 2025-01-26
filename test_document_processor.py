import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
from document_processor import process_document

class TestDocumentProcessor(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'ADDY_API_KEY': 'test-addy-key'
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_successful_document_processing(self):
        """Test successful document processing"""
        # Mock file reading
        mock_pdf_data = b'test pdf content'
        m = mock_open(read_data=mock_pdf_data)
        
        with patch('builtins.open', m), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):  # 1KB file
            
            # Mock successful API response
            mock_response = {
                'success': True,
                'document': {
                    'wages': 75000,
                    'credit_score': 750,
                    'debt': 25000,
                    'property_value': 400000
                }
            }
            
            with patch('requests.post') as mock_post:
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.status_code = 200
                mock_post.return_value.raise_for_status = lambda: None
                
                result = process_document('test.pdf')
                
                self.assertTrue(result['success'])
                self.assertEqual(result['data']['income'], 75000.0)
                self.assertEqual(result['data']['credit_score'], 750)
                self.assertEqual(result['data']['debt'], 25000.0)
                self.assertEqual(result['data']['property_value'], 400000.0)

    def test_missing_file(self):
        """Test handling of missing file"""
        with patch('os.path.exists', return_value=False):
            result = process_document('nonexistent.pdf')
            self.assertFalse(result['success'])
            self.assertEqual(result['error_type'], 'FileNotFoundError')

    def test_error_handling(self):
        """Test error handling for API failures"""
        mock_pdf_data = b'test pdf content'
        m = mock_open(read_data=mock_pdf_data)
        
        with patch('builtins.open', m), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):  # 1KB file
            
            with patch('requests.post') as mock_post:
                mock_post.return_value.status_code = 500
                mock_post.return_value.json.return_value = {'error': 'API Error'}
                mock_post.return_value.raise_for_status = lambda: None
                
                result = process_document('test.pdf')
                
                self.assertFalse(result['success'])
                self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main() 