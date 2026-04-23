from google import genai
from google.genai import types

def get_genai_response(prompt):

    client = genai.Client(api_key="AIzaSyC_ylU914dmAznodJZquUgpklV1yfOAqCM")

    response = client.models.generate_content(
        model="gemini-2.0-flash", config=types.GenerateContentConfig(
        system_instruction="Bạn là một trợ lý ảo thông minh của một công ty du lịch, hãy trả lời câu hỏi của người dùng một cách tự nhiên, chính xác và chuyên nghiệp.",),
        contents=prompt
    )
    cleaned_response = response.text.replace('\n', ' ')
    return cleaned_response


