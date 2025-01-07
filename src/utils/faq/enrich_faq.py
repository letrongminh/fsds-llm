import boto3
import json
from typing import List, Dict


class FAQEnricher:
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client(
            service_name="bedrock-runtime", region_name=region_name
        )
        self.model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

    def generate_variations(self, question: str, answer: str, category: str) -> Dict:
        """Generate variations of a question using Claude"""
        prompt = f"""Given this FAQ:
    Question: {question}
    Answer: {answer}
    Category: {category}

    Generate an enriched set of alternative questions in Vietnamese that mean the same thing. The questions should:
    1. Include different ways Vietnamese users might naturally ask this question
    2. Cover formal ways of asking (using "làm ơn cho hỏi", "xin hỏi", etc.)
    3. Include common Vietnamese synonyms and phrasings
    4. Match Vietnamese communication styles and cultural context
    5. Maintain exactly the same meaning as the original question

    The variations should consider:
    - Formal business language (using respectful forms)
    - Common online chat style
    - Short direct questions
    - Natural conversational Vietnamese
    - Regional variations (if appropriate)

    Return the result as a JSON object with this exact format:
    {{
    "original_question": "câu hỏi gốc",
    "answer": "câu trả lời gốc",
    "category": "danh mục",
    "variations": [
        "biến thể 1",
        "biến thể 2",
        etc...
    ]
    }}

    Return ONLY the JSON object, no other text or comments."""

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                }
            ),
        )

        response_body = json.loads(response.get("body").read())
        enriched_faq = json.loads(response_body["content"][0]["text"])

        return enriched_faq

    def enrich_faq(self, input_faq: List[Dict]) -> List[Dict]:
        """Enrich a list of FAQ with variations"""
        enriched_faq = []

        for faq in input_faq:
            try:
                variations = self.generate_variations(
                    faq.get("question"), faq.get("answer"), faq.get("category")
                )
                enriched_faq.append(variations)
            except Exception as e:
                print(f"Error generating variations for FAQ: {faq}. Error: {e}")
                continue

        return enriched_faq


def main():
    input_file = input("Enter path FAQ JSON file: ")
    with open(input_file, "r", encoding="utf-8") as file:
        input_faq = json.load(file)

    enricher = FAQEnricher()
    print(f"Enriching {len(input_faq)} FAQs...")
    enriched_faq = enricher.enrich_faq(input_faq)

    output_file = input_file.rsplit(".", 1)[0] + "_enriched.json"
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(enriched_faq, file, indent=2, ensure_ascii=False)

    print(f"Enriched FAQs saved to {output_file}")


if __name__ == "__main__":
    main()
