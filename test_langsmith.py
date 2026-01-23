"""
Test LangSmith tracing connection.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Set env vars explicitly
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_API_KEY'] = os.getenv('LANGCHAIN_API_KEY', '').strip().strip('"')
os.environ['LANGCHAIN_PROJECT'] = 'fairtrace'

print('Testing LangSmith connection...')
print(f'API Key starts with: {os.environ["LANGCHAIN_API_KEY"][:15]}...')
print(f'Project: {os.environ["LANGCHAIN_PROJECT"]}')
print(f'Tracing: {os.environ["LANGCHAIN_TRACING_V2"]}')

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

openai_key = os.getenv('OPENAI_API_KEY', '').strip().strip('"')
print(f'\nOpenAI key starts with: {openai_key[:15]}...')

llm = ChatOpenAI(model='gpt-4o-mini', api_key=openai_key)

print('\nCalling LLM with tracing...')
response = llm.invoke(
    [HumanMessage(content='Say hello in French')],
    config={'run_name': 'LangSmith Test Trace', 'tags': ['test']}
)
print(f'Response: {response.content}')
print('\n✓ Done! Check LangSmith project "fairtrace" for the trace.')
