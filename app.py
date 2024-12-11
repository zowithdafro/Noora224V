import os
from flask import Flask, jsonify, send_from_directory,request
from together import Together
import random

app = Flask(__name__)

TOGETHER_AI_API_KEY = '9cc99ec381bfed2471cc8178412207194aa0001f8ba0517a84b6a7ab31e2a1ce'
client = Together(api_key=TOGETHER_AI_API_KEY)


FACE_IMAGES_FOLDER = "./faces"
people_folders = [os.path.join(FACE_IMAGES_FOLDER, folder) for folder in os.listdir(FACE_IMAGES_FOLDER) if os.path.isdir(os.path.join(FACE_IMAGES_FOLDER, folder))]

emotions = ["happy", "sad", "surprise", "anxious", "disgust", "angry", "contentment"]
intensities = [0.1 * i for i in range(1, 11)] 

predefined_statements = [
    ("Do you know what time it is?", [
        ("angry", 1.0, "You are running late to a meeting."),
        ("happy", 0.9, "You see someone who does not have a watch.")
    ]),
    ("What are you doing?", [
        ("angry", 1.0, "You accidentally picked up someone else’s phone."),
        ("contentment", 0.8, "You are building a cool project, and a friend sees.")
    ]),
    ("Why are you here?", [
        ("contentment", 0.7, "Your friend runs into you at the mall."),
        ("disgust", 0.9, "You are at the school dance, and a bully comes by.")
    ]),
    ("What did you do?", [
        ("angry", 1.0, "You spilled juice on the floor."),
        ("happy", 0.8, "You made something cool for your final project, and someone asks about it.")
    ]),
    ("What’s that smell?", [
        ("disgust", 0.9, "There is a bad smell in the air."),
        ("happy", 0.7, "Your parent just baked cookies.")
    ]),
    ("Are you wearing that?", [
        ("disgust", 0.7, "You are wearing your favorite outfit to the dance, and your classmate comes by."),
        ("contentment", 0.9, "Your friend is wondering how they should dress for the recital, and you have on your outfit.")
    ]),
    ("You really outdid yourself this time.", [
        ("happy", 0.9, "You got an A+ on an assignment."),
        ("angry", 1.0, "You messed up the group project.")
    ]),
    ("I did not know this would happen", [
        ("sad", 0.8, "Your friend heard bad news."),
        ("surprise", 1.0, "Your friend heard shocking news.")
    ]),
    ("Come here", [
        ("happy", 1.0, "Your sibling wants to show you something awesome."),
        ("angry", 0.8, "Your parent saw that you didn’t wash the dishes.")
    ]),
    ("I didn’t expect to see you here", [
        ("surprise", 0.8, "You are on vacation in another country and see your friend randomly."),
        ("angry", 1.0, "You went to a group hangout, and someone you barely know approaches.")
    ])
]

def generate_statements_from_list():
    formatted_statements = []
    for statement, emotion_pairs in predefined_statements:
        for emotion, intensity, context in emotion_pairs:
            formatted_statements.append({
                "Statement": statement,
                "Emotion": emotion.capitalize(),
                "Intensity": round(intensity, 1),
                "Context": context
            })
    return formatted_statements

statements_and_emotions = generate_statements_from_list()
current_index = 0

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
    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}]
    )

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

'''
statements_and_emotions = generate_multiple_statements_and_emotions()
current_index = 0
'''
def get_image_path(emotion, intensity):
    person_folder = random.choice(people_folders)
    file_name = f"{emotion.lower()}_intensity_{intensity:.1f}.png"

    for root, _, files in os.walk(person_folder):
        files_lowercase = [f.lower() for f in files] 
        if file_name in files_lowercase:
            full_path = os.path.join(root, files[files_lowercase.index(file_name)])
            return full_path
    return None 

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
    statement_data = predefined_statements[current_index]
    statement = statement_data[0]
    emotions_and_intensities = statement_data[1]

    emotions = [item[0] for item in emotions_and_intensities]
    emotion = emotions_and_intensities[0][0] 
    intensity = emotions_and_intensities[0][1] 
    context = emotions_and_intensities[0][2]

    image_path = get_image_path(emotion, intensity)
    if image_path:
        relative_path = os.path.relpath(image_path, FACE_IMAGES_FOLDER)
        image_url = f"/faces/{relative_path}"
    else:
        image_url = None

    current_index = (current_index + 1) % len(predefined_statements)

    return jsonify({
        'statement': statement,
        'image_url': image_url,
        'emotions': emotions,
        'correct_emotion': emotion,
        'intensity': intensity,
        'context': context
    })



@app.route('/evaluate', methods=['POST'])
def evaluate_response():
    data = request.get_json()
    user_reply = data.get('user_reply')
    statement = data.get('statement')
    
    print(statement)
    emotion = data.get('correct_emotion')
    intensity = data.get('intensity')
    context = data.get('context')

    prompt = f"""
        Statement: "{statement}"
        Emotion: {emotion}
        Intensity: {intensity}
        Context: "{context}"

        User's Response: "{user_reply}"

        Task:
        1. Evaluate whether the user's response aligns with the intended emotion, tone, and context of the statement.
        2. Avoid suggesting responses that are rude, aggressive, or disrespectful. Instead, focus on examples that maintain a calm, respectful tone while reflecting the emotion and context.
        3. If the response generally aligns, mark it as "Correct" and suggest how it could better fit the tone while remaining respectful.
        4. If the response does not align at all, mark it as "Incorrect" and suggest a respectful response that matches the tone and context.

        Expected format:
        Evaluation: [Correct/Incorrect]
        Feedback: [Detailed feedback sentence that encourages a more effective and respectful response.]
        """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    message_content = response.choices[0].message.content.strip()
    evaluation_lines = message_content.split("\n")
    evaluation = {}
    for line in evaluation_lines:
        if line.startswith("Evaluation:"):
            evaluation['evaluation'] = line.replace("Evaluation:", "").strip()
        elif line.startswith("Feedback:"):
            evaluation['feedback'] = line.replace("Feedback:", "").strip()

    return jsonify(evaluation)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
