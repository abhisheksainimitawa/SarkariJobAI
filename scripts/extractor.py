import os
import json
import google.generativeai as genai
from jobai_schema import JobCriteria

SYSTEM_PROMPT = """You are an expert at extracting structured eligibility criteria from Indian government job notifications.

Extract the following from the provided job notification text and return valid JSON matching the schema:
- age limits (min, max) with category-wise relaxations
- educational qualifications required
- gender eligibility
- eligible categories (Gen/OBC/SC/ST/EWS)
- domicile/state restrictions
- required exams already cleared
- experience requirements
- job type (civil/defence/police/paramilitary/railways/banking)

For each field, assign an extraction_confidence score between 0-1.
If a field is not mentioned, use sensible defaults (e.g., gender: ["any"]).
Set low_confidence_fields for any field with confidence < 0.7.
"""


def extract_criteria(raw_text: str) -> JobCriteria | None:
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, f"Job notification text:\n\n{raw_text[:8000]}"],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        data = json.loads(response.text)
        return JobCriteria.model_validate(data)
    except Exception as e:
        print(f"[Extractor] failed: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <text_or_file>")
        sys.exit(1)

    arg = sys.argv[1]
    if arg.startswith("--file="):
        text = open(arg[7:]).read()
    else:
        text = arg

    result = extract_criteria(text)
    if result:
        print(result.model_dump_json(indent=2))
    else:
        print("Extraction failed")
        sys.exit(1)
