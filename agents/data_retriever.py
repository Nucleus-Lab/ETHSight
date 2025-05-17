import dspy
from agents.config import ModelConfig, get_model_config
from agents.utils import BitqueryAPI
import os
from datetime import datetime

class GraphQLQuery(dspy.Signature):
    """You are an expert in Bitquery GraphQL. The user is asking for specific data about Uniswap tokens, and you need to write a GraphQL query to retrieve the data from the Bitquery.
    
    # Example Output
    {
    EVM(dataset: combined, network: eth) {
        DEXTradeByTokens(
        orderBy: {descendingByField: "volumeUsd"}
        limit: {count: 10}
        where: {
            Trade: {Dex: {ProtocolFamily: {is: "Uniswap"}}},
            Block: {Time: {since: "2025-05-09T09:15:55Z"}}
        }
        ) {
        Trade {
            Currency {
            SmartContract
            Symbol
            Name
            }
            Dex {
            ProtocolName
            }
        }
        volumeUsd: sum(of: Trade_Side_AmountInUSD)
        count
        }
      }
    }
    
    # Guidelines
    1. You should directly return the GraphQL query, without any other text.
    """
    query = dspy.InputField(prefix="User's prompt:")
    current_time = dspy.InputField(prefix="Current date and time:")
    graphql_query = dspy.OutputField(prefix="The GraphQL query:")

class BitqueryDataRetriever():
    def __init__(self):
        model_config = get_model_config(ModelConfig.GPT4O)
        model = f"openai/{model_config['model_name']}"
        lm = dspy.LM(model=model, api_key=model_config['api_key'], base_url=model_config['base_url'])
        dspy.configure(lm=lm)
        self.generate_query = dspy.Predict(GraphQLQuery)
        self.BitqueryAPI = BitqueryAPI(os.getenv("BITQUERY_API_KEY"))
        
    def get_data(self, query: str):
        query = self.generate_query(query=query, current_time=datetime.now().isoformat()).graphql_query
        
        print(query)
        return self.BitqueryAPI.request(query=query)
    



