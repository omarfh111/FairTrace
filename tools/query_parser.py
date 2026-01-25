"""
Query Parser - Extracts structured metadata filters from natural language.

Uses LLM to convert "high risk clients" into `{"missed_payments_last_12m": {"gte": 3}}`.
"""

from typing import Literal, Optional, List, Union
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Filter Schemas
class RangeFilter(BaseModel):
    gte: Optional[float] = None
    lte: Optional[float] = None
    eq: Optional[float] = None

class ClientFilters(BaseModel):
    missed_payments_last_12m: Optional[Union[RangeFilter, int]] = Field(None, description="Number of missed payments")
    debt_to_income_ratio: Optional[Union[RangeFilter, float]] = Field(None, description="DTI ratio (0.0 to 1.0)")
    income_annual: Optional[Union[RangeFilter, float]] = Field(None, description="Annual income")
    contract_type: Optional[str] = Field(None, description="CDI, CDD, Freelance")
    outcome: Optional[str] = Field(None, description="DEFAULT, PAID_OFF, NO_DEFAULT")

class StartupFilters(BaseModel):
    burn_multiple: Optional[Union[RangeFilter, float]] = Field(None, description="Burn multiple (Net Burn / Net New ARR)")
    runway_months: Optional[Union[RangeFilter, float]] = Field(None, description="Months of cash runway")
    arr_current: Optional[Union[RangeFilter, float]] = Field(None, description="Current Annual Recurring Revenue")
    sector: Optional[str] = Field(None, description="Industry sector")
    vc_backing: Optional[bool] = Field(None, description="True if VC backed")
    outcome: Optional[str] = Field(None, description="IPO, ACQUIRED, BANKRUPT, ACTIVE")

class EnterpriseFilters(BaseModel):
    altman_z_score: Optional[Union[RangeFilter, float]] = Field(None, description="Altman Z-Score (distress < 1.8)")
    legal_lawsuits_active: Optional[Union[RangeFilter, int]] = Field(None, description="Number of active lawsuits")
    revenue_annual: Optional[Union[RangeFilter, float]] = Field(None, description="Annual Revenue")
    industry_code: Optional[str] = Field(None, description="Industry sector code")
    outcome: Optional[str] = Field(None, description="DEFAULT, NO_DEFAULT")

class SearchQuery(BaseModel):
    query_text: str = Field(..., description="The cleaned search query text")
    collection: Literal["clients_v2", "startups_v2", "enterprises_v2"] = Field(..., description="Target collection")
    filters: Optional[Union[ClientFilters, StartupFilters, EnterpriseFilters]] = Field(None, description="Extracted filters")

class QueryParser:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.0)
        self.parser = PydanticOutputParser(pydantic_object=SearchQuery)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a precise query extractor for a credit risk vector database.
Extract metadata filters from the user's search query.

Collections & Schemas:
1. clients_v2 (Individuals): missed_payments_last_12m, debt_to_income_ratio, income_annual, contract_type
2. startups_v2 (Startups): burn_multiple, runway_months, arr_current, sector, vc_backing
3. enterprises_v2 (Companies): altman_z_score, legal_lawsuits_active, revenue_annual, industry_code

Rules:
- Infer logical ranges. "High risk client" -> missed_payments_last_12m >= 3 AND debt_to_income_ratio >= 0.4
- "Distressed enterprise" -> altman_z_score < 1.8
- "High burn startup" -> burn_multiple > 3.0 OR runway_months < 12
- If no specific filters apply, return None for filters.

{format_instructions}"""),
            ("human", "{query}")
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def parse(self, query: str) -> dict:
        """Parse natural language query into Qdrant filters."""
        try:
            result = self.chain.invoke({
                "query": query,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Convert Pydantic model to Qdrant-style dict
            if not result.filters:
                return {"collection": result.collection, "filters": None}
            
            raw_filters = result.filters.model_dump(exclude_none=True)
            qdrant_filters = {}
            
            for key, val in raw_filters.items():
                if isinstance(val, dict):
                    # Range filter logic (gte, lte, eq)
                    qdrant_filters[key] = val
                else:
                    # Direct match
                    qdrant_filters[key] = val
            
            return {
                "collection": result.collection,
                "filters": qdrant_filters if qdrant_filters else None
            }
            
        except Exception as e:
            print(f"Query parsing failed: {e}")
            return {"collection": "clients_v2", "filters": None} # Default backup

# Singleton
_parser: Optional[QueryParser] = None

def get_query_parser() -> QueryParser:
    global _parser
    if _parser is None:
        _parser = QueryParser()
    return _parser
