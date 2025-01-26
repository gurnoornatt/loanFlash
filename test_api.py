import unittest
from unittest.mock import patch, MagicMock
import json
import jwt
import os
from datetime import datetime, timedelta
from api import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'API_USER': 'test_user',
            'API_PASSWORD': 'test_password',
            'API_SECRET_KEY': 'test_secret',
            'ADDY_API_KEY': 'test_addy_key'
        })
        self.env_patcher.start()
        
        # Generate test token
        self.test_token = jwt.encode({
            'user': 'test_user',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, 'test_secret')

    def tearDown(self):
        self.env_patcher.stop()

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue('timestamp' in data)

    def test_get_token_success(self):
        """Test successful token generation"""
        response = self.client.post(
            '/api/auth/token',
            headers={
                'Authorization': 'Basic dGVzdF91c2VyOnRlc3RfcGFzc3dvcmQ='  # test_user:test_password in base64
            }
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue('token' in data)

    def test_get_token_invalid_credentials(self):
        """Test token generation with invalid credentials"""
        response = self.client.post(
            '/api/auth/token',
            headers={
                'Authorization': 'Basic aW52YWxpZDppbnZhbGlk'  # invalid:invalid in base64
            }
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(data['error'], 'Invalid credentials')

    def test_process_document_success(self):
        """Test successful document processing"""
        # Mock PDF file
        mock_pdf = (b'%PDF-1.4\n...', 'test.pdf')
        
        # Mock successful document processing
        mock_result = {
            'success': True,
            'data': {
                'income': 75000.0,
                'credit_score': 750,
                'debt': 25000.0,
                'property_value': 400000.0
            }
        }
        
        with patch('api.process_document', return_value=mock_result):
            response = self.client.post(
                '/api/document/process',
                headers={'Authorization': f'Bearer {self.test_token}'},
                data={'file': mock_pdf},
                content_type='multipart/form-data'
            )
            data = json.loads(response.data)
            
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data['success'])
            self.assertEqual(data['data']['income'], 75000.0)

    def test_process_document_no_file(self):
        """Test document processing without file"""
        response = self.client.post(
            '/api/document/process',
            headers={'Authorization': f'Bearer {self.test_token}'}
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'No file provided')

    def test_process_query_success(self):
        """Test successful query processing"""
        test_query = "What is the maximum LTV for a single-family home in California?"
        
        # Mock NLP engine responses
        mock_entities = {'state': 'California', 'property_type': 'single-family'}
        mock_intent = 'ltv_inquiry'
        mock_guidelines = ['Guideline 1', 'Guideline 2']
        mock_response = "The maximum LTV is 97% for single-family homes in California."
        
        with patch('api.nlp_engine.extract_entities', return_value=mock_entities), \
             patch('api.nlp_engine.detect_intent', return_value=mock_intent), \
             patch('api.nlp_engine.search_guidelines', return_value=mock_guidelines), \
             patch('api.nlp_engine.generate_response', return_value=mock_response):
            
            response = self.client.post(
                '/api/nlp/query',
                headers={
                    'Authorization': f'Bearer {self.test_token}',
                    'Content-Type': 'application/json'
                },
                data=json.dumps({'query': test_query})
            )
            data = json.loads(response.data)
            
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data['success'])
            self.assertEqual(data['intent'], mock_intent)
            self.assertEqual(data['entities'], mock_entities)
            self.assertEqual(data['guidelines'], mock_guidelines)
            self.assertEqual(data['response'], mock_response)

    def test_process_query_no_query(self):
        """Test query processing without query"""
        response = self.client.post(
            '/api/nlp/query',
            headers={
                'Authorization': f'Bearer {self.test_token}',
                'Content-Type': 'application/json'
            },
            data=json.dumps({})
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'No query provided')

    def test_process_document_nlp_success(self):
        """Test successful document processing through NLP engine"""
        # Mock PDF file
        mock_pdf = (b'%PDF-1.4\n...', 'test.pdf')
        
        # Mock successful document processing
        mock_result = {
            'success': True,
            'classification': {
                'documentType': 'W2',
                'confidence': 0.95
            },
            'extraction': {
                'document_type': 'W2',
                'data': {
                    'wages': 75000,
                    'employer': 'Test Corp'
                }
            }
        }
        
        with patch('api.nlp_engine.process_document', return_value=mock_result):
            response = self.client.post(
                '/api/nlp/document',
                headers={'Authorization': f'Bearer {self.test_token}'},
                data={
                    'file': mock_pdf,
                    'document_type': 'W2',
                    'applicants': json.dumps([{'id': 1, 'name': 'John Doe'}])
                },
                content_type='multipart/form-data'
            )
            data = json.loads(response.data)
            
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data['success'])
            self.assertEqual(data['classification']['documentType'], 'W2')

if __name__ == '__main__':
    unittest.main() 