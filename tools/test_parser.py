from tools.query_parser import get_query_parser
import json

def test():
    parser = get_query_parser()
    
    queries = [
        "Show me high risk clients with missed payments",
        "Find startups with burn rate over 5x",
        "Distressed enterprises in Tech industry",
        "Clients with DTI above 0.5 and income under 50k",
        "Startup with less than 6 months runway"
    ]
    
    print("Testing Query Parser...\n")
    for q in queries:
        print(f"Query: {q}")
        res = parser.parse(q)
        print(f"Filters: {json.dumps(res, indent=2)}\n")

if __name__ == "__main__":
    test()
