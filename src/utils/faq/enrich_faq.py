import os
import json
import sys
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # Tải biến môi trường từ file .env
api_key = os.getenv("OPENAI_API_KEY")

class FAQEnricher:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def generate_variations(self, question: str, answer: str, category: str) -> Dict:
        """Generate variations of a question using ChatGPT"""
        prompt = f"""Hãy tạo các biến thể câu hỏi tiếng Việt cho FAQ sau:
Câu hỏi gốc: {question}
Câu trả lời: {answer}
Danh mục: {category}

Yêu cầu:
1. Tạo các cách hỏi tự nhiên khác nhau mà người dùng Việt có thể sử dụng
2. Bao gồm cách hỏi trang trọng (dùng "làm ơn cho hỏi", "xin hỏi"...)
3. Sử dụng từ đồng nghĩa và cách diễn đạt phổ biến trong tiếng Việt
4. Phù hợp với văn hóa và phong cách giao tiếp của người Việt
5. Giữ nguyên hoàn toàn ý nghĩa so với câu hỏi gốc

Các biến thể cần xem xét:
- Ngôn ngữ trang trọng trong kinh doanh
- Phong cách chat trực tuyến thông thường
- Câu hỏi ngắn gọn trực tiếp
- Cách nói chuyện tự nhiên
- Khác biệt vùng miền (nếu phù hợp) ở Việt Nam
- Văn phong dân dã Việt Nam

Trả về JSON theo định dạng sau:
{{
    "original_question": "câu hỏi gốc",
    "answer": "câu trả lời gốc", 
    "metadata": "danh mục",
    "variations": [
        "biến thể 1",
        "biến thể 2",
        ...
    ]
}}

Chỉ trả về JSON, không thêm bất kỳ nội dung nào khác."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý chuyên tạo biến thể câu hỏi tiếng Việt."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        # Parse response
        response_text = response.choices[0].message.content
        return json.loads(response_text)

    def enrich_faq(self, input_faq: List[Dict]) -> List[Dict]:
        """Enrich a list of FAQ with variations"""
        enriched_faq = []

        for faq in input_faq:
            try:
                variations = self.generate_variations(
                    faq.get("question"), 
                    faq.get("answer"), 
                    faq.get("metadata")
                )
                enriched_faq.append(variations)
            except Exception as e:
                print(f"Error generating variations for FAQ: {faq}. Error: {e}")
                continue

        return enriched_faq



def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "faq.json"  # Default to faq.json if no argument is provided
    
    try:
        with open(input_file, "r", encoding="utf-8") as file:
            input_faq = json.load(file)

        enricher = FAQEnricher()
        print(f"Enriching {len(input_faq)} FAQs...")
        enriched_faq = enricher.enrich_faq(input_faq)

        output_file = input_file.rsplit(".", 1)[0] + "_enriched.json"
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(enriched_faq, file, indent=2, ensure_ascii=False)

        print(f"Enriched FAQs saved to {output_file}")
    except FileNotFoundError:
        print(f"Error: Could not find file '{input_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: '{input_file}' is not a valid JSON file")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
