from ragas.metrics import LLMContextRecall, Faithfulness, FactualCorrectness, SemanticSimilarity
from ragas import evaluate
from datasets import Dataset
from ragas import EvaluationDataset
from langchain_aws import ChatBedrockConverse
from langchain_aws import BedrockEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
import json
import os

def create_evaluation_json(input_file: str = "/Users/khanhvg/Documents/MLOps/fsds-llm/src/utils/faq/faq_enriched.json",
                         output_file: str = "/Users/khanhvg/Documents/MLOps/fsds-llm/src/utils/faq/faq_evaluation.json"):
    """Create evaluation JSON with required Ragas columns"""
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    evaluation_data = []
    for item in data:
        questions = [item['original_question']] + item['variations']
        for question in questions:
            eval_item = {
                'question': question,
                'ground_truth': item['answer'],
                'contexts': [item['answer']],  # Original context
                'retrieved_contexts': [item['answer']],  # Retrieved context for evaluation
                'reference': item['answer'],  # Reference answer
                'user_input': question,  # Original user question
                'response': item['answer']  # Response for factual correctness
            }
            evaluation_data.append(eval_item)
    
    # Save the evaluation data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation_data, f, ensure_ascii=False, indent=2)
    
    return output_file

def load_faq_dataset(file_path: str = "/Users/khanhvg/Documents/MLOps/fsds-llm/src/utils/faq/faq_evaluation.json"):
    """Load FAQ dataset and convert to Ragas EvaluationDataset format"""
    # Read JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert to HuggingFace Dataset
    hf_dataset = Dataset.from_list(data)
    
    # Convert to Ragas EvaluationDataset
    return EvaluationDataset.from_hf_dataset(hf_dataset)

def get_bedrock_response(llm, question, context):
    """Get response from Bedrock for a given question and context"""
    prompt = f"""Based on the following context, answer the question.
    
Context: {context}

Question: {question}

Answer:"""
    
    try:
        response = llm.invoke(prompt)
        # Handle AIMessage object by accessing its content
        if hasattr(response, 'content'):
            return response.content.strip()
        elif isinstance(response, str):
            return response.strip()
        else:
            print(f"Unexpected response type: {type(response)}")
            return str(response)
    except Exception as e:
        print(f"Error getting response from Bedrock: {e}")
        return ""

def create_evaluation_dataset(qa_chain, raw_dataset):
    """Create evaluation dataset with actual model responses"""
    evaluation_data = []
    
    for item in raw_dataset:
        try:
            response = get_bedrock_response(
                qa_chain, 
                item['question'], 
                item['contexts'][0]
            )
            
            eval_item = {
                'question': item['question'],
                'ground_truth': item['ground_truth'],
                'contexts': item['contexts'],
                'retrieved_contexts': item['contexts'],
                'reference': item['reference'],
                'user_input': item['user_input'],
                'response': response  # Actual model response
            }
            evaluation_data.append(eval_item)
            
        except Exception as e:
            print(f"Error processing question: {item['question']}")
            print(f"Error: {e}")
    
    return Dataset.from_list(evaluation_data)

def setup_evaluators(config):
    """Setup LLM and embedding evaluators"""
    llm = ChatBedrockConverse(
        credentials_profile_name=config["credentials_profile_name"],
        region_name=config["region_name"],
        base_url=f"https://bedrock-runtime.{config['region_name']}.amazonaws.com",
        model=config["llm"],
        temperature=config["temperature"],
    )
    
    evaluator_llm = LangchainLLMWrapper(llm)
    
    evaluator_embeddings = LangchainEmbeddingsWrapper(BedrockEmbeddings(
        credentials_profile_name=config["credentials_profile_name"],
        region_name=config["region_name"],
        model_id=config["embeddings"],
    ))
    
    return llm, evaluator_llm, evaluator_embeddings

def main():
    # Configuration
    config = {
        "credentials_profile_name": "default",
        "region_name": "ap-northeast-1",
        "llm": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "embeddings": "cohere.embed-multilingual-v",
        "temperature": 0.4,
    }
    
    try:
        # Create evaluation JSON first
        eval_json_path = create_evaluation_json()
        print(f"Created evaluation JSON at: {eval_json_path}")
        
        # Load raw dataset
        with open(eval_json_path, 'r', encoding='utf-8') as f:
            raw_dataset = json.load(f)
        
        # Setup evaluators and get LLM
        llm, evaluator_llm, evaluator_embeddings = setup_evaluators(config)
        
        # Create evaluation dataset with actual responses
        eval_dataset = create_evaluation_dataset(llm, raw_dataset)
        
        # Convert to Ragas EvaluationDataset
        ragas_dataset = EvaluationDataset.from_hf_dataset(eval_dataset)
        
        # Define metrics
        metrics = [
            LLMContextRecall(llm=evaluator_llm), 
            FactualCorrectness(llm=evaluator_llm), 
            Faithfulness(llm=evaluator_llm),
            SemanticSimilarity(embeddings=evaluator_embeddings)
        ]
        
        # Run evaluation
        results = evaluate(dataset=ragas_dataset, metrics=metrics)
        
        # Convert results to DataFrame and display
        df = results.to_pandas()
        print("\nEvaluation Results:")
        print(df)
        
    except FileNotFoundError as e:
        print(f"Error: Could not find the FAQ dataset file. Please check the file path.")
        print(f"Details: {str(e)}")
    except Exception as e:
        print(f"An error occurred during evaluation: {str(e)}")

if __name__ == "__main__":
    main()