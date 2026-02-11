"""
Test script to verify OpenAI API connection
Run this after setting up your .env file to ensure everything works
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.environ.get("OPENAI_API_KEY")

print("=" * 60)
print("TimeTableAI - OpenAI API Connection Test")
print("=" * 60)

if not api_key:
    print("\n❌ ERROR: OPENAI_API_KEY not found!")
    print("\nTroubleshooting:")
    print("1. Make sure .env file exists in the project root")
    print("2. Check that .env contains: OPENAI_API_KEY=your-key-here")
    print("3. Restart your terminal/IDE after creating .env")
    print("4. Ensure there are no spaces around the = sign")
    exit(1)

print(f"\n✅ API Key found: {api_key[:20]}...{api_key[-4:]}")
print(f"   Length: {len(api_key)} characters")

try:
    from openai import OpenAI
    
    print("\n🔄 Testing connection to OpenAI...")
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Say 'Hello TimeTableAI!' in one sentence."}
        ],
        max_tokens=50
    )
    
    print("\n✅ SUCCESS! OpenAI API is working!")
    print(f"\n📝 AI Response: {response.choices[0].message.content}")
    print(f"\n📊 Token Usage:")
    print(f"   - Prompt tokens: {response.usage.prompt_tokens}")
    print(f"   - Completion tokens: {response.usage.completion_tokens}")
    print(f"   - Total tokens: {response.usage.total_tokens}")
    print(f"\n💰 Estimated cost of this test: ~$0.001")
    print("\n" + "=" * 60)
    print("✅ Your TimeTableAI app is ready to use full AI features!")
    print("=" * 60)
    
except ImportError:
    print("\n❌ ERROR: OpenAI package not installed")
    print("Run: pip install openai")
    
except Exception as e:
    print(f"\n❌ ERROR connecting to OpenAI:")
    print(f"   {str(e)}")
    print("\n🔍 Possible issues:")
    print("1. Invalid API key - check for typos")
    print("2. No billing method added to OpenAI account")
    print("3. API key doesn't have proper permissions")
    print("4. Internet connection problem")
    print("5. Rate limit exceeded (wait a few minutes)")
    print("\n📚 Visit: https://platform.openai.com/account/api-keys")

