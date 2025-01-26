import os
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv
import openai
from supabase import create_client
import logging
import json
import re
from unittest.mock import MagicMock
import base64
import requests

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
        
        # Load JSON guidelines
        self.fannie_mae_guidelines = self._load_json_guidelines('fannie_mae_guidelines.json')
        self.freddie_mac_guidelines = self._load_json_guidelines('freddie_mac_guidelines.json')
        
        # Initialize document API client
        self.addy_api_key = os.getenv('ADDY_API_KEY', 'external_document_api.zlm._w5NA+I2ekGSvB9I/WA/~')
        self.addy_api_base = 'https://addy-ai-external-api-dev.firebaseapp.com'
        
        # Define expanded categories
        self.categories = {
            'traditional': {
                'fha': ['ltv', 'dti', 'credit_score', 'income', 'assets'],
                'conventional': ['ltv', 'dti', 'credit_score', 'income', 'assets'],
                'va': ['eligibility', 'entitlement', 'funding_fee'],
                'usda': ['rural_eligibility', 'income_limits']
            },
            'alternative': {
                'crypto': ['collateral', 'ltv', 'volatility_requirements'],
                'private': ['investor_requirements', 'asset_based'],
                'bridge': ['exit_strategy', 'property_requirements']
            },
            'documents': {
                'income': ['W2', 'paystub', '1099', 'tax_return'],
                'assets': ['bank_statement', 'investment', 'retirement'],
                'property': ['appraisal', 'title', 'insurance'],
                'identity': ['government_id', 'visa', 'residency']
            },
            'state_specific': {}  # Will be populated from guidelines
        }
        
        # Define expanded intents
        self.intents = {
            'ltv_inquiry': r'(?i)(ltv|loan[- ]to[- ]value|down[- ]?payment)',
            'dti_inquiry': r'(?i)(dti|debt[- ]to[- ]income|monthly payment|income requirement)',
            'credit_inquiry': r'(?i)(credit[- ]score|fico|credit requirement)',
            'document_inquiry': r'(?i)(document|paperwork|form|statement|required|need to provide)',
            'state_specific': r'(?i)(?:in\s+|for\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            'property_type': r'(?i)(single[- ]family|multi[- ]family|condo|townhouse|investment property|primary residence)',
            'loan_type': r'(?i)(fha|conventional|jumbo|va|usda|crypto|private|bridge)',
            'alternative_inquiry': r'(?i)(crypto|blockchain|alternative|private|bridge|hard money)',
            'document_type': r'(?i)(W2|1099|bank statement|tax return|paystub)'
        }
    
    def _load_json_guidelines(self, filename: str) -> Dict:
        """Load and parse JSON guidelines file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {str(e)}")
            return {}
            
    def _classify_document(self, file_path: str, borrower_stated_type: str = None, applicants: List[Dict] = None) -> Dict[str, Any]:
        """Classify a document using Addy AI API"""
        try:
            # Read file as base64
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Prepare request
            headers = {
                'api-key': self.addy_api_key,
                'Content-Type': 'application/json'
            }
            
            # Build payload according to API spec
            payload = {
                'fileData': [file_data],
                'contentType': 'application/pdf',
                'modelDetail': 'high'
            }
            
            # Add optional parameters if provided
            if borrower_stated_type:
                payload['borrowerStatedDocumentType'] = borrower_stated_type
            
            if applicants:
                payload['applicants'] = applicants
            
            # Make API request
            response = requests.post(
                f"{self.addy_api_base}/document/classify",
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                raise ValueError(f"Classification failed: {result.get('reason', 'Unknown error')}")
            
            return result.get('classifications', [])[0]
            
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return {}
            
    def _extract_document_data(self, file_path: str, classification: Dict = None) -> Dict[str, Any]:
        """Extract data from a document using Addy AI API"""
        try:
            # Read file as base64
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Prepare request
            headers = {
                'api-key': self.addy_api_key,
                'Content-Type': 'application/json'
            }
            
            # Build payload according to API spec
            payload = {
                'fileData': file_data,
                'contentType': 'application/pdf'
            }
            
            # Add classification if provided
            if classification:
                payload['classification'] = {
                    'documentType': classification.get('documentType'),
                    'accountNumber': classification.get('accountNumber'),
                    'startPage': classification.get('startPage', 0),
                    'pages': classification.get('pages', 0),
                    'timePeriodStart': classification.get('timePeriodStart'),
                    'timePeriodEnd': classification.get('timePeriodEnd'),
                    'year': classification.get('year'),
                    'statementDate': classification.get('statementDate'),
                    'individuals': classification.get('individuals', []),
                    'applicantIds': classification.get('applicantIds', []),
                    'issuingEntity': classification.get('issuingEntity'),
                    'levelOfConfidence': classification.get('levelOfConfidence', 0),
                    'levelOfConfidenceExplanation': classification.get('levelOfConfidenceExplanation', '')
                }
            
            # Make API request
            response = requests.post(
                f"{self.addy_api_base}/document/extract",
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                raise ValueError(f"Extraction failed: {result.get('errorMessage', 'Unknown error')}")
            
            return {
                'document_type': result.get('documentType'),
                'confidence': result.get('levelOfConfidence'),
                'confidence_explanation': result.get('levelOfConfidenceExplanation'),
                'data': result.get('document', {})
            }
            
        except Exception as e:
            logger.error(f"Error extracting document data: {str(e)}")
            return {}
            
    def process_document(self, file_path: str, borrower_stated_type: str = None, applicants: List[Dict] = None) -> Dict[str, Any]:
        """Process a document through classification and extraction"""
        try:
            # First classify the document
            classification = self._classify_document(file_path, borrower_stated_type, applicants)
            if not classification:
                raise ValueError("Document classification failed")
            
            # Then extract data based on classification
            extraction = self._extract_document_data(file_path, classification)
            if not extraction:
                raise ValueError("Document extraction failed")
            
            return {
                'success': True,
                'classification': classification,
                'extraction': extraction
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
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
        guidelines = []
        
        try:
            # Search Supabase guidelines
            query = self.supabase.table('guidelines').select('*')
            
            # Build category filters based on intent and entities
            categories = []
            if intent == 'ltv_inquiry':
                categories.append('LTV')
            elif intent == 'dti_inquiry':
                categories.append('DTI')
            elif intent == 'credit_inquiry':
                categories.append('credit_score')
            elif intent == 'document_inquiry':
                doc_type = entities.get('document_type')
                if doc_type:
                    for cat, docs in self.categories['documents'].items():
                        if doc_type.lower() in [d.lower() for d in docs]:
                            categories.append(cat)
            
            # Add loan type specific categories
            if 'loan_type' in entities:
                loan_type = entities['loan_type'].upper()
                if loan_type in ['FHA', 'VA', 'USDA', 'CONVENTIONAL']:
                    categories.extend([f"{loan_type}_LTV", f"{loan_type}_DTI", f"{loan_type}_CREDIT"])
            
            # Apply category filter if we have categories
            if categories:
                category_filter = ",".join([f"category.eq.{cat}" for cat in categories])
                query = query.or_(category_filter)
            
            # Add state filter if present
            if 'state' in entities:
                query = query.or_(f"state.eq.{entities['state']},state.is.null")
            
            # Execute Supabase query
            try:
                result = query.execute()
                guidelines.extend(getattr(result, 'data', []))
            except Exception as e:
                logger.error(f"Error executing Supabase query: {str(e)}")
            
            # Search JSON guidelines
            json_results = []
            
            # Search Fannie Mae guidelines
            if self.fannie_mae_guidelines:
                fannie_matches = self._search_json_guidelines(
                    self.fannie_mae_guidelines,
                    intent,
                    entities
                )
                json_results.extend(fannie_matches)
            
            # Search Freddie Mac guidelines
            if self.freddie_mac_guidelines:
                freddie_matches = self._search_json_guidelines(
                    self.freddie_mac_guidelines,
                    intent,
                    entities
                )
                json_results.extend(freddie_matches)
            
            # Add document requirements if relevant
            if intent == 'document_inquiry' or 'document_type' in entities:
                doc_requirements = self._get_document_requirements(entities)
                if doc_requirements:
                    json_results.extend(doc_requirements)
            
            # Add alternative lending guidelines if relevant
            if 'loan_type' in entities and entities['loan_type'].lower() in ['crypto', 'private', 'bridge']:
                alt_requirements = self._get_alternative_requirements(entities['loan_type'])
                if alt_requirements:
                    json_results.extend(alt_requirements)
            
            # Combine and sort all guidelines
            guidelines.extend(json_results)
            return self._sort_guidelines_by_relevance(guidelines, intent, entities)
            
        except Exception as e:
            logger.error(f"Error searching guidelines: {str(e)}")
            return []
    
    def _search_json_guidelines(self, guidelines: Dict, intent: str, entities: Dict[str, Any]) -> List[Dict]:
        """Search through JSON guidelines for relevant matches"""
        matches = []
        
        try:
            # Extract relevant sections based on intent and entities
            relevant_sections = []
            
            if intent == 'ltv_inquiry':
                relevant_sections.extend(guidelines.get('ltv', []))
            elif intent == 'dti_inquiry':
                relevant_sections.extend(guidelines.get('dti', []))
            elif intent == 'credit_inquiry':
                relevant_sections.extend(guidelines.get('credit', []))
            
            # Add loan type specific sections
            if 'loan_type' in entities:
                loan_sections = guidelines.get(entities['loan_type'].lower(), [])
                relevant_sections.extend(loan_sections)
            
            # Add state specific sections
            if 'state' in entities:
                state_sections = guidelines.get('state_specific', {}).get(entities['state'], [])
                relevant_sections.extend(state_sections)
            
            # Convert sections to guideline format
            for section in relevant_sections:
                matches.append({
                    'rule_name': section.get('title', 'Unnamed Rule'),
                    'rule_text': section.get('content', ''),
                    'source': section.get('source', 'JSON Guidelines'),
                    'category': section.get('category', 'general'),
                    'state': section.get('state'),
                    'version': section.get('version')
                })
            
            return matches
            
        except Exception as e:
            logger.error(f"Error searching JSON guidelines: {str(e)}")
            return []
    
    def _get_document_requirements(self, entities: Dict[str, Any]) -> List[Dict]:
        """Get requirements for specific document types"""
        requirements = []
        
        try:
            doc_type = entities.get('document_type', '').lower()
            
            # Find category for document type
            category = None
            for cat, docs in self.categories['documents'].items():
                if doc_type in [d.lower() for d in docs]:
                    category = cat
                    break
            
            if category:
                requirements.append({
                    'rule_name': f"{doc_type.upper()} Requirements",
                    'rule_text': f"Standard requirements for {doc_type} documents in {category} category.",
                    'source': 'Document Guidelines',
                    'category': category,
                    'document_type': doc_type
                })
            
            return requirements
            
        except Exception as e:
            logger.error(f"Error getting document requirements: {str(e)}")
            return []
    
    def _get_alternative_requirements(self, loan_type: str) -> List[Dict]:
        """Get requirements for alternative lending types"""
        requirements = []
        
        try:
            loan_type = loan_type.lower()
            if loan_type in self.categories['alternative']:
                requirements.append({
                    'rule_name': f"{loan_type.upper()} Lending Requirements",
                    'rule_text': f"Alternative lending requirements for {loan_type} loans.",
                    'source': 'Alternative Lending Guidelines',
                    'category': 'alternative',
                    'loan_type': loan_type
                })
            
            return requirements
            
        except Exception as e:
            logger.error(f"Error getting alternative requirements: {str(e)}")
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
                'metadata': metadata,
                'guidelines_used': guidelines
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
                },
                'guidelines_used': []
            } 