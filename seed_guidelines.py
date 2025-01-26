import os
from dotenv import load_dotenv
from supabase import create_client
import uuid

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Initial guidelines data
guidelines = [
    {
        'id': str(uuid.uuid4()),
        'rule_name': 'FHA-LTV-2024',
        'rule_text': 'For FHA loans, the maximum LTV is 96.5% with a credit score of 580 or higher. For credit scores between 500-579, the maximum LTV is 90%.',
        'source': 'FHA Handbook',
        'category': 'LTV',
        'state': None
    },
    {
        'id': str(uuid.uuid4()),
        'rule_name': 'FHA-DTI-2024',
        'rule_text': 'The maximum DTI ratio for FHA loans is 43%. However, ratios up to 50% may be allowed with strong compensating factors.',
        'source': 'FHA Handbook',
        'category': 'DTI',
        'state': None
    },
    {
        'id': str(uuid.uuid4()),
        'rule_name': 'FHA-CREDIT-2024',
        'rule_text': 'Minimum credit score requirement is 580 for maximum financing (96.5% LTV). Scores between 500-579 are limited to 90% LTV.',
        'source': 'FHA Handbook',
        'category': 'credit_score',
        'state': None
    },
    {
        'id': str(uuid.uuid4()),
        'rule_name': 'CA-LTV-2024',
        'rule_text': 'In California, conforming loans follow standard LTV limits: 97% for fixed-rate mortgages, 95% for ARMs on single-family primary residences.',
        'source': 'California Lending Guide',
        'category': 'LTV',
        'state': 'California'
    },
    {
        'id': str(uuid.uuid4()),
        'rule_name': 'CONV-LTV-2024',
        'rule_text': 'For conventional loans on investment properties: Single-family: 85% LTV, 2-4 units: 75% LTV. Primary residence: up to 97% LTV for qualified buyers.',
        'source': 'Fannie Mae Guidelines',
        'category': 'LTV',
        'state': None
    }
]

def seed_guidelines():
    try:
        print("\nClearing existing guidelines...")
        # Delete all records where id exists
        delete_result = supabase.table('guidelines').delete().filter('id', 'not.is', 'null').execute()
        print(f"Delete result: {delete_result}")
        
        print("\nInserting new guidelines...")
        result = supabase.table('guidelines').insert(guidelines).execute()
        print(f"Insert result: {result}")
        
        print(f"\nSuccessfully added {len(guidelines)} guidelines to the database.")
        return True
    except Exception as e:
        print(f"\nError seeding guidelines: {str(e)}")
        print(f"Error type: {type(e)}")
        return False

if __name__ == '__main__':
    seed_guidelines() 