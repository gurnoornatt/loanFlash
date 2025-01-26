from dotenv import load_dotenv
import os
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Fetch all guidelines
result = supabase.table('guidelines').select('*').execute()

print(f"\nFound {len(result.data)} guidelines:")
for guideline in result.data:
    print(f"\nRule: {guideline['rule_name']}")
    print(f"Text: {guideline['rule_text'][:100]}...")
    print(f"Category: {guideline['category']}")
    print(f"State: {guideline['state']}")
    print("-" * 80) 