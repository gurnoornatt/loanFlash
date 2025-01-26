import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from supabase import create_client
import logging
import json
import re
from datetime import datetime
import hashlib
import requests
from bs4 import BeautifulSoup
import pandas as pd
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class KnowledgeBaseManager:
    def __init__(self):
        # Initialize Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        if not all([supabase_url, supabase_key]):
            raise ValueError("Missing Supabase credentials")
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Define source URLs
        self.sources = {
            'fha': 'https://www.hud.gov/sites/documents/4155-1_2.PDF',
            'fannie_mae': 'https://singlefamily.fanniemae.com/media/document/pdf/selling-guide',
            'freddie_mac': 'https://guide.freddiemac.com/app/guide/',
            'va': 'https://www.benefits.va.gov/WARMS/docs/admin26/handbook/ChapterLendersHanbookChapter3.pdf',
            'usda': 'https://www.rd.usda.gov/files/3555-1chapter11.pdf',
            'california': 'https://www.calhfa.ca.gov/homeownership/programs/handbook.pdf'
        }
        
        # Define document types and their patterns
        self.document_types = {
            'income': [
                'W2', 'Form 1099', 'PayStub', 'Tax Return', 
                'Social Security Award', 'VA Benefits'
            ],
            'assets': [
                'Bank Statement', 'Brokerage Statement', 
                'Retirement Statement', 'Annuity Statement'
            ],
            'property': [
                'Mortgage Statement', 'HOA Statement', 
                'Insurance Declaration', 'Property Note'
            ],
            'identity': [
                'Government ID', 'VA Certificate', 
                'Work Visa', 'Resident Alien Card'
            ]
        }
        
        # Add API configuration
        self.api_config = {
            'base_url': 'https://addy-ai-external-api-dev.firebaseapp.com',
            'api_key': os.getenv('ADDY_API_KEY', 'external_document_api.zlm._w5NA+I2ekGSvB9I/WA/~'),
            'endpoints': {
                'classify': '/document/classify',
                'extract': '/document/extract'
            }
        }
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash of the content for version tracking"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # First, normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove commas from numbers
        text = re.sub(r'(\d),(\d)', r'\1\2', text)
        
        # Handle special cases
        text = re.sub(r'[!@#^&*()_+=:]', '', text)  # Remove most special characters including colon
        text = re.sub(r'\$(?!\d)', '', text)  # Remove $ not followed by a number
        text = re.sub(r'(?<!\d)%', '', text)  # Remove % not preceded by a number
        
        # Clean up any resulting double spaces and trailing punctuation
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[.,;:]+$', '', text)  # Remove trailing punctuation
        
        return text.strip()
    
    def fetch_guidelines(self, source: str) -> List[Dict[str, Any]]:
        """Fetch guidelines from a specific source"""
        try:
            if source not in self.sources:
                raise ValueError(f"Invalid source: {source}")

            response = requests.get(self.sources[source])
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract relevant sections
            guidelines = []
            sections = soup.find_all(['h2', 'h3', 'p'])
            
            current_section = None
            current_text = []
            
            for section in sections:
                if section.name in ['h2', 'h3']:
                    if current_section:
                        # Process previous section
                        text_content = ' '.join(current_text)
                        guidelines.append({
                            'rule_name': current_section,
                            'rule_text': text_content,
                            'source': source,
                            'category': self._detect_category(current_section, text_content),
                            'state': self._detect_state(text_content),
                            'version_hash': self._generate_content_hash(text_content),
                            'last_updated': datetime.now().isoformat()
                        })
                    current_section = section.text.strip()
                    current_text = []
                else:
                    current_text.append(self._clean_text(section.text))
            
            # Process the last section if exists
            if current_section and current_text:
                text_content = ' '.join(current_text)
                guidelines.append({
                    'rule_name': current_section,
                    'rule_text': text_content,
                    'source': source,
                    'category': self._detect_category(current_section, text_content),
                    'state': self._detect_state(text_content),
                    'version_hash': self._generate_content_hash(text_content),
                    'last_updated': datetime.now().isoformat()
                })
            
            return guidelines
            
        except Exception as e:
            logger.error(f"Error fetching guidelines from {source}: {str(e)}")
            return []
    
    def _detect_category(self, title: str, content: str) -> str:
        """Detect the category of a guideline based on its content"""
        # Define category patterns
        patterns = {
            'LTV': r'(?i)(ltv|loan[- ]to[- ]value|down[- ]?payment)',
            'DTI': r'(?i)(dti|debt[- ]to[- ]income|monthly payment)',
            'credit_score': r'(?i)(credit[- ]score|fico)',
            'property_type': r'(?i)(property type|single family|multi family)',
            'income': r'(?i)(income|employment|salary)',
            'assets': r'(?i)(assets|reserves|funds)',
            'eligibility': r'(?i)(eligibility|qualify|requirements)'
        }
        
        # Check title and content against patterns
        combined_text = f"{title} {content}"
        matches = {}
        
        for category, pattern in patterns.items():
            if re.search(pattern, combined_text):
                matches[category] = len(re.findall(pattern, combined_text))
        
        if matches:
            return max(matches.items(), key=lambda x: x[1])[0]
        return 'general'
    
    def _detect_state(self, content: str) -> Optional[str]:
        """Detect if the guideline is state-specific"""
        # Complete list of US states
        states = [
            'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
            'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
            'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
            'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
            'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
            'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
            'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
            'Wisconsin', 'Wyoming'
        ]
        
        for state in states:
            pattern = f"(?i)\\b{state}\\b"
            if re.search(pattern, content):
                return state
        return None
    
    def update_knowledge_base(self) -> Dict[str, Any]:
        """Update the knowledge base with latest guidelines"""
        stats = {
            'new_guidelines': 0,
            'updated_guidelines': 0,
            'errors': 0,
            'sources_processed': []
        }
        
        try:
            for source in self.sources:
                logger.info(f"Fetching guidelines from {source}")
                guidelines = self.fetch_guidelines(source)
                
                for guideline in guidelines:
                    try:
                        # Check if guideline exists
                        existing = self.supabase.table('guidelines')\
                            .select('id, version_hash')\
                            .eq('rule_name', guideline['rule_name'])\
                            .execute()
                        
                        if not existing.data:
                            # Insert new guideline
                            self.supabase.table('guidelines').insert(guideline).execute()
                            stats['new_guidelines'] += 1
                        elif existing.data[0]['version_hash'] != guideline['version_hash']:
                            # Update existing guideline
                            self.supabase.table('guidelines')\
                                .update(guideline)\
                                .eq('id', existing.data[0]['id'])\
                                .execute()
                            stats['updated_guidelines'] += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing guideline: {str(e)}")
                        stats['errors'] += 1
                
                stats['sources_processed'].append(source)
                
        except Exception as e:
            logger.error(f"Error updating knowledge base: {str(e)}")
            stats['errors'] += 1
        
        return stats
    
    def export_guidelines(self, format: str = 'csv') -> str:
        """Export guidelines to a file"""
        try:
            # Fetch all guidelines
            result = self.supabase.table('guidelines').select('*').execute()
            
            if not result.data:
                raise ValueError("No guidelines found to export")
            
            # Convert to DataFrame
            df = pd.DataFrame(result.data)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"guidelines_export_{timestamp}.{format}"
            
            # Export based on format
            if format == 'csv':
                df.to_csv(filename, index=False)
            elif format == 'json':
                df.to_json(filename, orient='records', indent=2)
            elif format == 'excel':
                df.to_excel(filename, index=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting guidelines: {str(e)}")
            raise

    def classify_document(self, file_path: str) -> Dict[str, Any]:
        """Classify a document using Addy AI API"""
        try:
            # Read file as base64
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Prepare request
            headers = {
                'api-key': self.api_config['api_key'],
                'Content-Type': 'application/json'
            }
            
            payload = {
                'fileData': [file_data],
                'contentType': 'application/pdf',
                'modelDetail': 'high'
            }
            
            # Make API request
            response = requests.post(
                f"{self.api_config['base_url']}{self.api_config['endpoints']['classify']}",
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