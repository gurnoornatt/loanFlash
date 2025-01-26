import os
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv
import openai
from supabase import create_client
import logging
import json
import re
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class MortgageNLPEngine:
    def __init__(self):
        # Initialize OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        if not all([supabase_url, supabase_key]):
            raise ValueError("Missing Supabase credentials")
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Define common intents and entities
        self.intents = {
            'ltv_inquiry': r'(?i)(ltv|loan[- ]to[- ]value|down[- ]?payment)',
            'dti_inquiry': r'(?i)(dti|debt[- ]to[- ]income|monthly payment|income requirement)',
            'credit_inquiry': r'(?i)(credit[- ]score|fico|credit requirement)',
            'state_specific': r'(?i)(?:in\s+|for\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            'property_type': r'(?i)(single[- ]family|multi[- ]family|condo|townhouse|investment property|primary residence)',
            'loan_type': r'(?i)(fha|conventional|jumbo|va|usda)'
        }
    
    def extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract relevant entities from the query"""
        entities = {}
        
        # Extract state if present
        state_match = re.search(self.intents['state_specific'], query)
        if state_match and len(state_match.group(1)) <= 20:  # Reasonable state name length
            entities['state'] = state_match.group(1).strip()
        
        # Extract property type if present
        property_match = re.search(self.intents['property_type'], query)
        if property_match:
            entities['property_type'] = property_match.group(1).lower()
            
        # Extract loan type if present
        loan_match = re.search(self.intents['loan_type'], query)
        if loan_match:
            entities['loan_type'] = loan_match.group(1).lower()
        
        return entities
    
    def detect_intent(self, query: str) -> str:
        """Detect the primary intent of the query"""
        # Initialize scores for each intent
        scores = {
            'ltv_inquiry': 0,
            'dti_inquiry': 0,
            'credit_inquiry': 0,
            'general_inquiry': 0
        }
        
        # Check for intent-specific keywords
        for intent, pattern in self.intents.items():
            if intent not in ['state_specific', 'property_type', 'loan_type']:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    scores[intent] = len(matches)
        
        # Additional context-based scoring
        if re.search(r'(?i)(how\s+much|down\s+payment|qualify)', query):
            scores['ltv_inquiry'] += 1
        if re.search(r'(?i)(income|afford|payment)', query):
            scores['dti_inquiry'] += 1
        if re.search(r'(?i)(qualify|requirements)', query):
            scores['credit_inquiry'] += 1
        
        # Get the intent with the highest score
        max_score = max(scores.values())
        if max_score > 0:
            for intent, score in scores.items():
                if score == max_score:
                    return intent
        
        return 'general_inquiry'
    
    def search_guidelines(self, intent: str, entities: Dict[str, Any]) -> List[Dict]:
        """Search for relevant guidelines based on intent and entities"""
        try:
            # Create base query
            query = self.supabase.table('guidelines').select('*')
            
            # Build category filters based on intent and entities
            categories = []
            if intent == 'ltv_inquiry':
                categories.append('LTV')
            elif intent == 'dti_inquiry':
                categories.append('DTI')
            elif intent == 'credit_inquiry':
                categories.append('credit_score')
            
            # Add loan type specific categories
            if 'loan_type' in entities:
                loan_type = entities['loan_type'].upper()
                categories.extend([f"{loan_type}_LTV", f"{loan_type}_DTI", f"{loan_type}_CREDIT"])
            
            # Apply category filter if we have categories
            if categories:
                category_filter = ",".join([f"category.eq.{cat}" for cat in categories])
                query = query.or_(category_filter)
            
            # Add state filter if present
            if 'state' in entities:
                query = query.or_(f"state.eq.{entities['state']},state.is.null")
            
            # Execute query
            try:
                result = query.execute()
                guidelines = getattr(result, 'data', [])
                
                # Sort guidelines by relevance
                return self._sort_guidelines_by_relevance(guidelines, intent, entities)
                
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"Error searching guidelines: {str(e)}")
            return []
    
    def _sort_guidelines_by_relevance(self, guidelines: List[Dict], intent: str, entities: Dict[str, Any]) -> List[Dict]:
        """Sort guidelines by relevance to the query"""
        def calculate_relevance(guideline: Dict) -> float:
            score = 0.0
            
            # Category match
            if guideline.get('category', '').lower() in intent:
                score += 1.0
            
            # State match
            if 'state' in entities:
                if guideline.get('state') == entities['state']:
                    score += 1.0
                elif guideline.get('state') is None:  # General guidelines
                    score += 0.5
            
            # Loan type match
            if 'loan_type' in entities:
                loan_type = entities['loan_type'].upper()
                if loan_type in guideline.get('rule_name', ''):
                    score += 1.0
            
            # Property type match
            if 'property_type' in entities:
                if entities['property_type'] in guideline.get('rule_text', '').lower():
                    score += 0.5
            
            return score
        
        # Sort guidelines by relevance score
        return sorted(guidelines, key=calculate_relevance, reverse=True)
    
    def calculate_confidence_score(self, guidelines: List[Dict], intent: str, entities: Dict[str, Any]) -> float:
        """Calculate a confidence score based on multiple factors"""
        base_score = 0.4  # Base confidence
        
        # Adjust based on guidelines found
        if guidelines:
            base_score = round(base_score + 0.3, 2)
            
            # Boost if we have state-specific guidelines
            if 'state' in entities and any(g.get('state') == entities['state'] for g in guidelines):
                base_score = round(base_score + 0.1, 2)
                
            # Boost if we have category-specific guidelines
            if any(g.get('category', '').lower() in intent for g in guidelines):
                base_score = round(base_score + 0.1, 2)
        
        # Adjust based on entity matches
        if entities:
            base_score = round(base_score + 0.1, 2)
            
        return round(min(base_score, 1.0), 2)  # Cap at 1.0

    def generate_response(self, query: str, guidelines: List[Dict]) -> Tuple[str, Dict[str, Any]]:
        """Generate a response using OpenAI GPT"""
        # Prepare context from guidelines
        context = "\n".join([
            f"Rule: {g['rule_name']}\n{g['rule_text']}\n"
            f"Source: {g['source']}\nCategory: {g['category']}"
            for g in guidelines
        ])
        
        # Extract entities and intent
        intent = self.detect_intent(query)
        entities = self.extract_entities(query)
        
        # Prepare system prompt with context
        system_prompt = """You are a mortgage guideline expert. Your role is to:
1. Provide accurate, specific answers based on the provided guidelines
2. If no specific guidelines are available, provide general information but clearly state that it's not based on specific guidelines
3. Structure your response with:
   - Direct answer to the question
   - Specific requirements or conditions
   - Additional relevant context
   - Any important caveats or exceptions
4. If the query mentions a specific state or loan type, emphasize those specific requirements first"""

        # Prepare user prompt
        user_prompt = f"""Based on the following mortgage guidelines:

{context}

Question: {query}

Relevant context detected:
- Intent: {intent}
- State: {entities.get('state', 'Not specified')}
- Property Type: {entities.get('property_type', 'Not specified')}
- Loan Type: {entities.get('loan_type', 'Not specified')}

Please provide a structured response that directly addresses the question."""

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Calculate confidence score
            confidence_score = self.calculate_confidence_score(guidelines, intent, entities)
            
            metadata = {
                'guidelines_used': [g['id'] for g in guidelines],
                'confidence_score': confidence_score,
                'model_used': 'gpt-4o-mini',
                'intent': intent,
                'entities_found': entities,
                'response_length': len(answer.split())
            }
            
            return answer, metadata
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return (
                "I apologize, but I encountered an error while processing your question. "
                "Please try rephrasing your question or contact support if the issue persists.",
                {
                    'error': str(e),
                    'confidence_score': 0.0,
                    'model_used': 'gpt-4o-mini',
                    'intent': intent,
                    'entities_found': entities
                }
            )
    
    def process_query(self, query: str, borrower_id: str = None) -> Dict[str, Any]:
        """Process a user query and return a response"""
        try:
            # Extract intent and entities
            intent = self.detect_intent(query)
            entities = self.extract_entities(query)
            logger.info(f"Detected intent: {intent}, entities: {entities}")
            
            # Search relevant guidelines
            guidelines = self.search_guidelines(intent, entities)
            logger.info(f"Found {len(guidelines)} relevant guidelines")
            
            # Generate response
            answer, metadata = self.generate_response(query, guidelines)
            
            # Store the decision if borrower_id is provided
            if borrower_id:
                decision_data = {
                    'borrower_id': borrower_id,
                    'question': query,
                    'answer': answer,
                    'metadata': {
                        **metadata,
                        'intent': intent,
                        'entities': entities
                    }
                }
                self.supabase.table('loan_decisions').insert(decision_data).execute()
            
            return {
                'success': True,
                'answer': answer,
                'intent': intent,
                'entities': entities,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'metadata': {
                    'confidence_score': 0.0,
                    'model_used': 'gpt-4o-mini'
                }
            } 