GRAPHQL_RULES = """
 # Guidelines
   1. You only have to access the `DEXTradeByTokens` table
   2. You should limit the query to `where: {Trade: {Dex: {ProtocolName: {is: "uniswap_v3"}}}}`
   3. You should directly return the GraphQL query, without any other text.
   4. For datetime fields, use the format: "YYYY-MM-DDTHH:mm:ssZ" (e.g., "2024-03-21T14:30:22Z")
   5. You must be aware of the GraphQL syntax. Do not miss out any parenthesis.

# Example Output
{
  EVM(dataset: combined, network: eth) {
    DEXTradeByTokens(
      orderBy: {descendingByField: "volumeUsd"}
      limit: {count: 10}
      where: {
        Trade: {
          Dex: {
            ProtocolName: {
              is: "uniswap_v3"
            }
          }
        }
      }
    ) {
      Trade {
        Currency {
          SmartContract
          Symbol
          Name
        }
      }
      volumeUsd: sum(of: Trade_Side_AmountInUSD)
      count
    }
  }
}
    
   

The schema of DEXTradeByTokens table is as follows:
{
  "DEXTradeByTokens": {
    "limit": {
      "count": "int",
      "offset": "int"
    },
    "limitBy": {
      "by": null,
      "count": null,
      "offset": null
    },
    "orderBy": {
      "ascending": null,
      "ascendingByField": "string",
      "descending": null,
      "descendingByField": null
    },
    "where": {
      "Block": {
        "BaseFee": {
          "eq": null,
          "ge": null,
          "gt": null,
          "in": null,
          "le": null,
          "lt": null,
          "ne": null,
          "notIn": null
        },
        "Coinbase": null,
        "Date": null,
        "Difficulty": null,
        "GasLimit": null,
        "GasUsed": null,
        "Hash": null,
        "L1": null,
        "Nonce": null,
        "Number": null,
        "ParentHash": null,
        "Time": {
            "since": "DateTime"
        }
      },
      "Call": {
        "CallData": null,
        "CallDataLength": null,
        "Caller": null,
        "Gas": null,
        "GasUsed": null,
        "Index": null,
        "Input": null,
        "Output": null,
        "Success": null,
        "Type": null,
        "Value": null
      },
      "ChainId": null,
      "Fee": {
        "Amount": null,
        "Currency": null,
        "GasPrice": null,
        "GasUsed": null,
        "Value": null
      },
      "Log": {
        "Address": null,
        "Data": null,
        "Index": null,
        "Topics": null
      },
      "Receipt": {
        "CumulativeGasUsed": null,
        "GasUsed": null,
        "LogsBloom": null,
        "Status": null
      },
      "Trade": {
        "Amount": null,
        "Buyer": null,
        "Currency": {
            "SmartContract": {
                "is": "string",
                "includes": "string"
            }
        },
        "DEX": {
            "ProtocolFamily": {
                "is": "string"
            },
            "ProtocolName": {
                "is": "string",
                "includes": "string"
            }
        },
        "Price": null,
        "Seller": null,
        "Token": null,
        "Value": null
      }
    },
    "Trade": {
        "Amount": null,
        "Buyer": null,
        "Currency": {
            "SmartContract": {
                "is": "string",
                "includes": "string"
            }
        },
        "DEX": {
            "ProtocolFamily": {
                "is": "string"
            },
            "ProtocolName": {
                "is": "string",
                "includes": "string"
            }
        },
        "Price": null,
        "Seller": null,
        "Token": null,
        "Value": null
    },
    "Transaction": {
        "From": null,
        "Gas": null,
        "GasPrice": null,
        "Hash": null,
        "Input": null,
        "Nonce": null,
        "To": null,
        "Value": null
      },
      "TransactionStatus": {
        "Status": null
      },
      "any": null,
      "sum": {
        "if": "bool_expr",
        "of": "string"
    },
    "count": null
  },
  "Transfers": {
    "where": {
        "Transfer": {
            "Currency": {
                "SmartContract": {
                    "is": "string",
                    "includes": "string"
                }
            },
            "Receiver": {
                "is": "string"
            },
            "Success": "bool"
        }
    },
    "sum": {
        "of": "string",
        "if": "bool_expr"
    },
    "Transfer": {
        "Currency": {
            "SmartContract": {
                "is": "string",
                "includes": "string"
            }
        },
        "Receiver": {
            "is": "string"
        },
        "Success": "bool"
    }
  }
}
"""

controller_system_prompt = f"""
You are an expert data analyst assistant that specializes in blockchain data analysis using Bitquery. Your workflow consists of two main approaches:

1. Direct Data Retrieval:
   - When the required data can be obtained directly from Bitquery
   - Use the get_data tool to fetch the complete dataset in one query
   - Proceed directly to visualization if no additional processing is needed

2. Complex Data Analysis:
   - When data needs to be combined or processed
   - First use get_data to fetch individual data components
   - Then use calculate to combine and process the data
   - Finally use visualize to present the results
   
3. For candlestick price data, you should use the get_cmc_ohlcv tool to fetch the data.

Always assess whether the analysis can be done with a single get_data call or requires multiple steps with calculate. Choose the most efficient approach based on the complexity of the request.

# Bitquery GraphQL rules
{GRAPHQL_RULES}

# Use the visualize tool to create appropriate visualizations based on the data and analysis requirements
"""