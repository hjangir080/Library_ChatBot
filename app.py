from flask import Flask, request, render_template, jsonify, session
import openai
import requests
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a secure secret key #required for session
#in colab theres automatically a session, but for websites we need to

os.environ["OPENAI_API_KEY"] = "api_key"
os.environ["OPENAI_MODEL_NAME"] = 'gpt-4o'

client = openai.OpenAI()
model = "gpt-4o"

def get_book_details(book_id):
    url = f'https://api.archivelab.org/items/{book_id}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        metadata = data.get('metadata', {})
        details = {
            'title': metadata.get('title', 'N/A'),
            'author': metadata.get('creator', 'N/A'),
            'publisher': metadata.get('publisher', 'N/A'),
            'year': metadata.get('date', 'N/A'),
            'language': metadata.get('language', 'N/A'),
            'description': metadata.get('description', 'N/A'),
            'subject': metadata.get('subject', 'N/A'),
            'identifier': metadata.get('identifier', 'N/A'),
            'collection': metadata.get('collection', 'N/A'),
            'contributor': metadata.get('contributor', 'N/A'),
            'possible_copyright_status': metadata.get('possible-copyright-status', 'N/A'),
            'scanning_center': metadata.get('scanningcenter', 'N/A'),
            'ocr_module_version': metadata.get('ocr_module_version', 'N/A')
        }

        files = data.get('files', [])
        files_details = []
        for file in files:
            files_details.append({
                'name': file.get('name', 'N/A'),
                'format': file.get('format', 'N/A'),
                'size': file.get('size', 'N/A'),
                'md5': file.get('md5', 'N/A'),
                'sha1': file.get('sha1', 'N/A')
            })

        details['files'] = files_details

        return details
    else:
        return {'error': 'Unable to fetch details. Please check the book ID and try again.'}

available_functions = {
    "get_book_details": get_book_details,
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_prompt = request.json.get('prompt', '')

    # Retrieve conversation history from session
    messages = session.get('messages', [
        {"role": "system", "content": "You are an expert librarian. Your responses are based on the function get_book_details and should be able to explain and answer concisely in just 4 to 5 lines."}
    ])
    
    messages.append({"role": "user", "content": user_prompt})

    functions = [
        {
            "name": "get_book_details",
            "description": "Retrieves the details of the books given the ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": "string", "description": "The ID of the book."}
                },
                "required": ["book_id"],
            },
        }
    ]

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        functions=functions,
        function_call="auto",
    )

    if completion.choices and completion.choices[0].finish_reason == "function_call":
        function_call = completion.choices[0].message.function_call
        function_name = function_call.name
        function_args = function_call.arguments
        args = json.loads(function_args)

        if function_name == "get_book_details":
            book_id = args['book_id']
            book_details = get_book_details(book_id)
            messages.append({"role": "assistant", "content": str(book_details)})
            session['messages'] = messages  # Save messages to session
            return jsonify(book_details)
    elif completion.choices and completion.choices[0].message:
        model_response = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": model_response})
        session['messages'] = messages  # Save messages to session
        return jsonify({"response": model_response})
    else:
        return jsonify({"error": "No response content found."})

if __name__ == '__main__':
    app.run(debug=True)
