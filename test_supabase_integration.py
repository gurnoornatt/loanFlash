import os
from dotenv import load_dotenv
from supabase import create_client
import logging
import json
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not all([supabase_url, supabase_key]):
            raise ValueError("Missing Supabase credentials")
        
        client = create_client(supabase_url, supabase_key)
        logger.info("✅ Successfully connected to Supabase")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {str(e)}")
        return None

def test_guidelines_table(client):
    """Test CRUD operations on guidelines table"""
    try:
        # Test data
        test_guideline = {
            'id': str(uuid.uuid4()),
            'rule_name': 'TEST-RULE-001',
            'rule_text': 'This is a test guideline.',
            'source': 'test',
            'category': 'test',
            'state': None,
            'version_hash': 'test123',
            'last_updated': datetime.now().isoformat()
        }
        
        # Test INSERT
        logger.info("Testing INSERT operation...")
        result = client.table('guidelines').insert(test_guideline).execute()
        if not result.data:
            raise Exception("Insert failed")
        logger.info("✅ INSERT successful")
        
        # Test SELECT
        logger.info("Testing SELECT operation...")
        result = client.table('guidelines')\
            .select('*')\
            .eq('rule_name', 'TEST-RULE-001')\
            .execute()
        if not result.data:
            raise Exception("Select failed")
        logger.info("✅ SELECT successful")
        
        # Test UPDATE
        logger.info("Testing UPDATE operation...")
        update_data = {'rule_text': 'Updated test guideline'}
        result = client.table('guidelines')\
            .update(update_data)\
            .eq('rule_name', 'TEST-RULE-001')\
            .execute()
        if not result.data:
            raise Exception("Update failed")
        logger.info("✅ UPDATE successful")
        
        # Test DELETE
        logger.info("Testing DELETE operation...")
        result = client.table('guidelines')\
            .delete()\
            .eq('rule_name', 'TEST-RULE-001')\
            .execute()
        logger.info("✅ DELETE successful")
        
        return True
    except Exception as e:
        logger.error(f"❌ Table operations failed: {str(e)}")
        return False

def test_query_performance(client):
    """Test query performance with filters"""
    try:
        start_time = datetime.now()
        
        # Test category filter
        logger.info("Testing category filter...")
        result = client.table('guidelines')\
            .select('*')\
            .eq('category', 'LTV')\
            .execute()
        logger.info(f"Found {len(result.data)} LTV guidelines")
        
        # Test state filter
        logger.info("Testing state filter...")
        result = client.table('guidelines')\
            .select('*')\
            .eq('state', 'California')\
            .execute()
        logger.info(f"Found {len(result.data)} California guidelines")
        
        # Test combined filters
        logger.info("Testing combined filters...")
        result = client.table('guidelines')\
            .select('*')\
            .eq('category', 'LTV')\
            .eq('state', 'California')\
            .execute()
        logger.info(f"Found {len(result.data)} California LTV guidelines")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"✅ Query performance test completed in {duration:.2f} seconds")
        
        return True
    except Exception as e:
        logger.error(f"❌ Query performance test failed: {str(e)}")
        return False

def main():
    """Run all Supabase integration tests"""
    logger.info("Starting Supabase integration tests...")
    
    # Test connection
    client = test_supabase_connection()
    if not client:
        return False
    
    # Test table operations
    if not test_guidelines_table(client):
        return False
    
    # Test query performance
    if not test_query_performance(client):
        return False
    
    logger.info("✅ All Supabase integration tests completed successfully")
    return True

if __name__ == '__main__':
    main() 