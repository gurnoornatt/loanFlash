import unittest
from unittest.mock import patch, MagicMock
from nlp_engine import MortgageNLPEngine
import os
import json

class TestMortgageNLPEngine(unittest.TestCase):
    @patch('nlp_engine.create_client')
    def setUp(self, mock_create_client):
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'OPENAI_API_KEY': 'test-openai-key'
        })
        self.env_patcher.start()
        
        # Mock Supabase client
        self.mock_supabase = MagicMock()
        mock_create_client.return_value = self.mock_supabase
        
        # Create test instance
        self.engine = MortgageNLPEngine()
        
        # Sample guidelines for testing
        self.sample_guidelines = [
            {
                'id': '1',
                'rule_name': 'FNM-LTV-2023',
                'rule_text': 'Max LTV: 95% for primary residences',
                'source': 'Fannie Mae',
                'category': 'LTV',
                'state': None
            },
            {
                'id': '2',
                'rule_name': 'FNM-DTI-2023',
                'rule_text': 'Maximum DTI ratio: 45%',
                'source': 'Fannie Mae',
                'category': 'DTI',
                'state': None
            }
        ]
    
    def tearDown(self):
        self.env_patcher.stop()
    
    def test_intent_detection(self):
        """Test intent detection for different queries"""
        test_cases = [
            ('What is the maximum LTV ratio?', 'ltv_inquiry'),
            ('What DTI is allowed?', 'dti_inquiry'),
            ('Minimum credit score required?', 'credit_inquiry'),
            ('Tell me about loans', 'general_inquiry')
        ]
        
        for query, expected_intent in test_cases:
            intent = self.engine.detect_intent(query)
            self.assertEqual(intent, expected_intent, f"Failed to detect intent for: {query}")
    
    def test_entity_extraction(self):
        """Test entity extraction from queries"""
        query = "What is the maximum LTV for a single-family home in California?"
        entities = self.engine.extract_entities(query)
        
        self.assertEqual(entities['state'], 'California')
        self.assertEqual(entities['property_type'], 'single-family')
    
    def test_confidence_scoring(self):
        """Test confidence score calculation"""
        # Test with no guidelines or entities
        score1 = self.engine.calculate_confidence_score([], 'general_inquiry', {})
        self.assertEqual(score1, 0.4)  # Base score
        
        # Test with guidelines but no entities
        score2 = self.engine.calculate_confidence_score(self.sample_guidelines, 'ltv_inquiry', {})
        self.assertEqual(score2, 0.8)  # Base + guidelines + category match
        
        # Test with guidelines and entities
        score3 = self.engine.calculate_confidence_score(
            self.sample_guidelines,
            'ltv_inquiry',
            {'state': 'California', 'property_type': 'single-family'}
        )
        self.assertEqual(score3, 0.9)  # Base + guidelines + category + entities
        
        # Verify score is always between 0 and 1
        self.assertTrue(0.0 <= score1 <= 1.0)
        self.assertTrue(0.0 <= score2 <= 1.0)
        self.assertTrue(0.0 <= score3 <= 1.0)
    
    @patch('nlp_engine.openai.chat.completions.create')
    def test_response_generation(self, mock_openai):
        """Test response generation with OpenAI"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="The maximum LTV is 95% for primary residences."))
        ]
        mock_openai.return_value = mock_response
        
        answer, metadata = self.engine.generate_response(
            "What is the maximum LTV?",
            self.sample_guidelines
        )
        
        self.assertTrue(isinstance(answer, str))
        self.assertTrue(isinstance(metadata, dict))
        self.assertIn('guidelines_used', metadata)
        self.assertIn('confidence_score', metadata)
        self.assertEqual(metadata['model_used'], 'gpt-4o-mini')
        self.assertTrue(0.0 <= metadata['confidence_score'] <= 1.0)
    
    def test_guideline_search(self):
        """Test guideline search functionality"""
        # Mock Supabase response
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.or_.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=self.sample_guidelines)
        
        self.mock_supabase.table.return_value = mock_table
        
        guidelines = self.engine.search_guidelines('ltv_inquiry', {'state': 'California'})
        self.assertTrue(isinstance(guidelines, list))
        self.assertEqual(len(guidelines), 2)
    
    @patch('nlp_engine.openai.chat.completions.create')
    def test_end_to_end_query(self, mock_openai):
        """Test end-to-end query processing"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="The maximum LTV is 95%."))
        ]
        mock_openai.return_value = mock_response
        
        # Mock Supabase responses
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=self.sample_guidelines)
        self.mock_supabase.table().select.return_value = mock_select
        self.mock_supabase.table().insert().execute.return_value = MagicMock()
        
        result = self.engine.process_query(
            "What is the maximum LTV for a single-family home in California?",
            borrower_id="test-borrower"
        )
        
        self.assertTrue(result['success'])
        self.assertTrue(isinstance(result['answer'], str))
        self.assertEqual(result['intent'], 'ltv_inquiry')
        self.assertIn('entities', result)
        self.assertIn('metadata', result)
    
    @patch('nlp_engine.openai.chat.completions.create')
    def test_error_handling(self, mock_openai):
        """Test error handling in response generation"""
        # Mock OpenAI error
        mock_openai.side_effect = Exception("API Error")
        
        answer, metadata = self.engine.generate_response(
            "What is the maximum LTV?",
            self.sample_guidelines
        )
        
        self.assertTrue(isinstance(answer, str))
        self.assertIn('error', metadata)
        self.assertEqual(metadata['confidence_score'], 0.0)
        self.assertEqual(metadata['model_used'], 'gpt-4o-mini')

if __name__ == '__main__':
    unittest.main() 