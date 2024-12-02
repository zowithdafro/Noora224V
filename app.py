import os
from flask import Flask, jsonify, send_from_directory
from together import Together
import random

app = Flask(__name__)

# Initialize the Together AI client
TOGETHER_AI_API_KEY = '9cc99ec381bfed2471cc8178412207194aa0001f8ba0517a84b6a7ab31e2a1ce'  # Replace with your actual API key
client = Together(api_key=TOGETHER_AI_API_KEY)

# Path to the 'faces' folder in the same directory as app.py
FACE_IMAGES_FOLDER = "./faces"
people_folders = [os.path.join(FACE_IMAGES_FOLDER, folder) for folder in os.listdir(FACE_IMAGES_FOLDER) if os.path.isdir(os.path.join(FACE_IMAGES_FOLDER, folder))]

# Emotions and intensities
emotions = ["happy", "sad", "surprise", "anxious", "disgust", "angry", "contentment"]
intensities = [0.1 * i for i in range(1, 11)]  # 0.1, 0.2, ..., 1.0

# Generate 20 ambiguous statements with emotion and intensity
def generate_multiple_statements_and_emotions():
    prompt = """
    Generate 20 ambiguous statements that could be interpreted as either positive, negative, or neutral depending on the emotional tone and context.
    Each statement should be directed to a child and should not include any explicit emotional context. The meaning of the statement should change entirely
    based on the facial expression or tone of voice used when saying it.

    Examples of such statements might include:
    - "What are you doing?" (could be curious, frustrated, or playful)
    - "That’s what you chose?" (could be surprised, happy, or disappointed)
    - "Do you really think so?" (could be angry, interested, or skeptical)

    The following emotions should be assigned randomly to each statement:
    - Happy
    - Sad
    - Surprise
    - Anxious
    - Disgust
    - Angry
    - Contentment

    Each statement should also have an intensity value ranging from 0.1 to 1.0.

    Return the result in the following **exact format**:
    Statement: [Ambiguous statement]
    Emotion: [Emotion]
    Intensity: [Intensity]

    Ensure there are 20 such pairs.
    """
    # Generate statements using Together AI
    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse the response
    message_content = response.choices[0].message.content.strip()
    statements_and_emotions = []
    output_text = message_content.split("\n\n")
    for pair in output_text:
        lines = pair.split("\n")
        if len(lines) >= 3:
            statement = lines[0].replace("Statement:", "").strip()
            emotion = lines[1].replace("Emotion:", "").strip()
            intensity = float(lines[2].replace("Intensity:", "").strip())
            statements_and_emotions.append((statement, emotion, intensity))

    return statements_and_emotions

# Preload statements and emotions
statements_and_emotions = generate_multiple_statements_and_emotions()
current_index = 0

def get_image_path(emotion, intensity):
    person_folder = random.choice(people_folders)
    file_name = f"{emotion.lower()}_intensity_{intensity:.1f}.png"  # Ensure file name is lowercase

    # Search for the matching file
    for root, _, files in os.walk(person_folder):
        files_lowercase = [f.lower() for f in files]  # Ensure files are checked in lowercase
        if file_name in files_lowercase:
            full_path = os.path.join(root, files[files_lowercase.index(file_name)])
            return full_path
    return None  # Return None if no matching file is found

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/faces/<path:filename>')
def serve_faces(filename):
    return send_from_directory(FACE_IMAGES_FOLDER, filename)

@app.route('/generate', methods=['GET'])
def generate_expression():
    global current_index
    statement, emotion, intensity = statements_and_emotions[current_index]
    image_path = get_image_path(emotion, intensity)
    
    if image_path:
        relative_path = os.path.relpath(image_path, FACE_IMAGES_FOLDER)
        image_url = f"/faces/{relative_path}"
    else:
        image_url = None

    current_index = (current_index + 1) % len(statements_and_emotions)

    return jsonify({
        'statement': statement,
        'emotion': emotion,
        'intensity': intensity,
        'image_url': image_url
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
