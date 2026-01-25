import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

def create_indexes():
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    if not url or not api_key:
        print("❌ QDRANT_URL or QDRANT_API_KEY not found in environment.")
        return

    client = QdrantClient(url=url, api_key=api_key)
    
    # Define indexes to create for each collection
    # We need indexes for any field used in range filters (gte, lte, eq on numbers)
    
    collections_config = {
        "clients_v2": [
            ("income_annual", models.PayloadSchemaType.FLOAT),
            ("debt_to_income_ratio", models.PayloadSchemaType.FLOAT),
            ("missed_payments_last_12m", models.PayloadSchemaType.INTEGER),
            # Add others if needed
        ],
        "startups_v2": [
            ("arr_current", models.PayloadSchemaType.FLOAT),
            ("burn_multiple", models.PayloadSchemaType.FLOAT),
            ("runway_months", models.PayloadSchemaType.FLOAT), # Can be float or int
        ],
        "enterprises_v2": [
            ("revenue_annual", models.PayloadSchemaType.FLOAT),
            ("altman_z_score", models.PayloadSchemaType.FLOAT),
            ("legal_lawsuits_active", models.PayloadSchemaType.INTEGER),
        ]
    }

    print("🔧 Creating Qdrant payload indexes...")
    
    for collection_name, fields in collections_config.items():
        print(f"\nProcessing collection: {collection_name}")
        for field_name, field_type in fields:
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                print(f"  ✓ Created index for '{field_name}' ({field_type})")
            except Exception as e:
                # Often fails if index already exists or collection doesn't exist
                print(f"  ⚠️ Could not create index for '{field_name}': {e}")

    print("\n✅ Index creation complete.")

if __name__ == "__main__":
    create_indexes()
