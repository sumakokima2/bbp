from flask import Flask, render_template, redirect, url_for, request, flash,  jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, User, Book, Column, Plan, UserNote
from flask_migrate import Migrate
import os
import json
import random
import openai
from datetime import datetime
import requests
import numpy as np

from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# データベースの初期化
db.init_app(app)

migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid login credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        data = {
        "gender": "",
        "occupation": "",
        "education": "",
        "hobbies": "",
        "favorite_books_movies_music": "",
        "values_beliefs": "",
        "reading_frequency": "",
        "preferred_genres": "",
        "reading_purpose": "",
        "reading_style": "",
        "daily_routine": "",
        "living_environment":"",
        "stress_tolerance": "",
        "social_role": "",
        "cultural_background": "",
        "learning_style": "",
        "reading_goals": "",
        "book_expectation": ""
    }
        visibility = {
        "gender": True,
        "occupation": True,
        "education": True,
        "hobbies": True,
        "favorite_books_movies_music": True,
        "values_beliefs": True,
        "reading_frequency": True,
        "preferred_genres": True,
        "reading_purpose": True,
        "reading_style": True,
        "daily_routine": True,
        "living_environment":True,
        "stress_tolerance": True,
        "social_role": True,
        "cultural_background": True,
        "learning_style": True,
        "reading_goals": True,
        "book_expectation": True
    }
        new_user = User(username=username, email=email, password=password,data = data, visibility = visibility)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!')
        return redirect(url_for('login'))
    return render_template('register.html')


# 辞書を渡す
key_translation = {
    "gender": "性別",
    "occupation": "職業",
    "education": "学歴",
    "hobbies": "趣味",
    "favorite_books_movies_music": "好きな本・映画・音楽",
    "values_beliefs": "価値観・信条",
    "reading_frequency": "読書頻度",
    "preferred_genres": "好きなジャンル",
    "reading_purpose": "読書目的",
    "reading_style": "読書スタイル",
    "daily_routine": "日常の習慣",
    "living_environment": "生活環境",
    "stress_tolerance": "ストレス耐性",
    "social_role": "社会的役割",
    "cultural_background": "文化的背景",
    "learning_style": "学習スタイル",
    "reading_goals": "読書の目標",
    "book_expectation": "本への期待"
}

@app.route('/home')
@login_required
def home():
    plans = Plan.query.order_by(Plan.created_at.desc()).all()  # データベースから全てのプランを取得
    persona = User.query.all()
    notes = UserNote.query.filter_by(user_id=current_user.id).all()

    
    return render_template('home.html', user=current_user, plans = plans,persona = persona, notes = notes,key_translation = key_translation)

@app.route('/profile')
@login_required
def profile():
    read_books = current_user.read_books
    notes = UserNote.query.filter_by(user_id=current_user.id).all()

# ユーザーが書いたコラムを取得
    user_columns = Column.query.filter_by(user_id=current_user.id).all()
    plans = current_user.plans
    return render_template('profile.html', user=current_user, read_books=read_books,user_columns=user_columns, plans= plans, notes = notes)



# JSON ファイルを読み込む関数
def load_learning_types():
    json_path = os.path.join(app.static_folder, 'data', 'learning_type.json')
    with open(json_path, 'r', encoding='utf-8') as file:
        learning_types = json.load(file)
    
    return learning_types


# JSON ファイルを読み込む関数
def load_vector():
    json_path = os.path.join(app.static_folder, 'data', 'vector.json')
    with open(json_path, 'r', encoding='utf-8') as file:
        vector = json.load(file)
    
    return vector



@app.route('/process_user_type', methods=['POST'])
def process_user_type():
    # リクエストデータをJSON形式で取得
    data = request.get_json()
    learning_types = load_learning_types()["type"]


    question = (
        "目的: ユーザーの回答をもとに、以下の学習タイプから最も近いものを提案してください。\n"
        + " \n\n####ユーザーの回答: \n" + json.dumps(data, ensure_ascii=False)
        + " \n\n####学習タイプ: \n" + json.dumps(learning_types, ensure_ascii=False)
        +
        "\n\n#### 選定基準\n"
            +"1. 各学習タイプは以下の要素に基づいて判断してください:\n"
            +"   - 傾向 \n - 欠点・注意点\n\n"

            +"2. ユーザーの回答は1～5の評価で与えられます:\n"
            +"   - 5: 非常に当てはまる\n   - 4: 当てはまる\n   - 3: どちらとも言えない\n   - 2: 当てはまらない\n   - 1: 全く当てはまらない\n\n"

            +"3. 学習タイプの「傾向」と「欠点・注意点」をユーザーの回答と比較し、最も一致する「タイプ名」を一つ選んでください。\n\n"

            +"#### 注意\n"
            "- 出力は学習タイプの「タイプ名」のみとします。\n- 例: 協力型の学習者"
        )
    
    # OpenAI APIキーを設定
    openai.api_key = {app.config['SECRET_KEY']}
    # OpenAI GPT-3に質問を送信してレスポンスを取得
    #response = openai.Completion.create(
    #  engine="text-davinci-003",
    #  prompt=question,
    #  max_tokens=500
    #)

    # OpenAI ChatGPT APIへのリクエスト
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # モデルを指定
        messages=[
            {"role": "system", "content": question}
        ]
    )
    # レスポンスを整形
    formatted_response = response['choices'][0]['message']['content']#response.choices[0].text.strip()

    print("Received data:", formatted_response)
    current_user.type = formatted_response
    db.session.commit()

    # learningTypesはリスト、learningTypeは文字列であると仮定
    researcherType = next((item for item in learning_types if item["タイプ"] == formatted_response), None)

    # 質問IDごとの選択結果を処理
    #selected_items = {}
    #for key, value in data.items():
    #    if key.startswith("question_"):  # "question_"で始まるキーを処理
    #        question_id = key.split("_")[1]  # 質問IDを取得
    #        selected_items[question_id] = value  # 質問IDと回答を格納

    # 結果を作成
    #result = {
    #    "selected_items": selected_items,
    ##    "message": "診断が完了しました！"
    #}

    # JSONレスポンスを返す
    return jsonify(researcherType)

def cosine_similarity(vecA, vecB):
    """コサイン類似度を計算する関数"""
    vecA = np.array(vecA)
    vecB = np.array(vecB)
    dot_product = np.dot(vecA, vecB)
    normA = np.linalg.norm(vecA)
    normB = np.linalg.norm(vecB)
    return dot_product / (normA * normB)

def fetch_embeddings(text, api_key):
    """OpenAI APIから埋め込みベクトルを取得"""
    url = "https://api.openai.com/v1/embeddings"
    payload = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"APIリクエストが失敗しました: {response.status_code}, {response.text}")
    
    json_response = response.json()
    if not json_response or not json_response.get("data") or not json_response["data"][0].get("embedding"):
        raise ValueError("不正なAPIレスポンス")
    
    return json_response["data"][0]["embedding"]

@app.route('/create_column', methods=['POST'])
def create_column():
    print(current_user)
 # リクエストデータをJSON形式で取得
    data = request.get_json()
    print(data)
    # OpenAI APIキーを設定
    openai.api_key = {app.config['SECRET_KEY']}
# データの前処理
    persona = data.get("persona", "")
    selectedPersona = data.get("selectedPersona", "")
    theme = data.get("theme", "")
    important = data.get("important", "")
    curious = data.get("curious", "")
    confusing = data.get("confusing", "")
    other = data.get("other", "")
    
    selectedPersona1 = User.query.filter_by(username=selectedPersona).first()

    important = ", ".join(important)
    curious = ", ".join(curious)
    confusing = ", ".join(confusing)
    other = ", ".join(other)
    original_text = data.get("userinput", "")

    book = data.get("book", "")
    #previous_results = data.get("previous_results", [])
    try:
    # 指定の形式に変換
        book_ids = [int(id) for id in book]
        filtered_books = Book.query.filter(Book.id.in_(book_ids)).all()        
        print(filtered_books[0].yoyaku)
        message = [{
                        "role": "system",
                        "content": "あなたは、有名出版社のコラムニストです。読者が読んだ本の内容は#本に書かれている通りです。この本の主要なアイデアを深堀りし、読者が見落としがちな点や重要なテーマに光を当て、新しい視点を提供する形で解説してください。プロンプトでは、読者のパーソナルな関心や性質などを書きます。これを考慮して、読者に適切な300字以内のコラムを、フィードバックの3要素に基づき、書いてください。"
                    },
                    {
                        "role": "user",
                        "content": f"""
                        読者は、{current_user.data}、です。読者は、{current_user.type}の性格を持っています。
                        読者のために、次の項目のコンテキストを含むように、読書をサポートしてください。
                        テーマは{theme}です。

                        #読者が大事だと思ったこと
                        {important}

                        #読者が詳しく知りたいと思ったこと
                        {curious}

                        #読者がわからないと思ったこと
                        {confusing}

                        #読者のメモ
                        {other}

                        #読者からの要望
                        {original_text}

                        #本
                         {filtered_books[0].yoyaku if len(filtered_books) > 0 else ''}{filtered_books[1].yoyaku if len(filtered_books) > 1 else ''}{filtered_books[2].yoyaku if len(filtered_books) > 2 else ''}
                        
                        #禁止事項
                        本の批評や批判を行わないこと。

                        #フィードバックの3要素
                        ・目標確認
                        利用者が求める知識に関連した情報を提示する。読んだ内容の要約や知識獲得時の課題を整理し、利用者の学習目標を明確化する
                        ・現状の評価
                        利用者の理解度や現在の状況に基づいてフィードバックを提供する。バイアスや疑問点の解消、反証を含めた情報を提示することで、より深い知識を獲得できるよう支援する
                        ・次のステップ
                        利用者が次に学ぶべき知識や行動に関する提案を行う。関心事項を広げるための関連情報や書籍を紹介し、学びを促進する


                        """

                        
                        
                    }
                ]
         # OpenAI APIキーを設定
        openai.api_key = {app.config['SECRET_KEY']}
        # OpenAI GPT-3に質問を送信してレスポンスを取得
        #response = openai.Completion.create(
        #  engine="text-davinci-003",
        #  prompt=question,
        #  max_tokens=500
        #)

        # OpenAI ChatGPT APIへのリクエスト
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # モデルを指定
            messages = message
        )
        # レスポンスを整形
        formatted_response =response['choices'][0]['message']['content']#response.choices[0].text.strip()
        print("Received data:", formatted_response)

        

        message = [{
                        "role": "system",
                        "content": f"""
                        以下のようなコメントを受け取りました。
                        {persona}または{selectedPersona1.data}のような人としての知恵を深めるためには次にどのようなことを学べがいいか、
                        技術やアイデア、学問分野などを具体的に100文字以内で「~はいかがでしょうか」として提案してください。
                        なお具体的な技術名やツールもカッコがきで補足するようにしてください。
                        また、提案する内容を実施することで{persona}として達成できる/できるようになることも書いてください
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""

                        #コメント
                        {formatted_response}

                        """ 
                        
                    }
                ]
        # OpenAI ChatGPT APIへのリクエスト
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # モデルを指定
            messages = message
        )
        # レスポンスを整形
        formatted_response1 =response['choices'][0]['message']['content']#response.choices[0].text.strip()
        print("Received data:", formatted_response1)

        # filtered_booksが空の場合の対処
        

        print("user:",current_user)
        user1 = User.query.filter_by(username=current_user.username).first()
        books = filtered_books if filtered_books else []
        print("books:",books)
        new_column = Column(
            title="formatted_response",
            content= formatted_response + "-----" + formatted_response1,
            user_id= user1.id,
            books = books
        )

        db.session.add(new_column)
        db.session.commit() 

        return jsonify({
            "status": "success",
            "column" : formatted_response,
            "advice":formatted_response1
        })
        # Planオブジェクトを作成
        name = f"Plan based on query: {query_text}"
        description = f"Generated plan using OpenAI embeddings for query: {query_text}"
        books = [user_notes[i].custom_text for i in top_indices]
        new_plan = Plan(
            name=name,
            description=description,
            created_by_user_id=current_user.id,
            created_by=current_user.username,
            books=books
        )
        db.session.add(new_plan)
        db.session.commit()

        return jsonify({
            "status": "success",
            "top_indices": top_indices,
            "plan_id": new_plan.id
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/create_plan', methods=['POST'])
def create_plan():
    # リクエストデータをJSON形式で取得
    data = request.get_json()
    print(data)
# OpenAI APIキーを設定
    openai.api_key = {app.config['SECRET_KEY']}
# データの前処理
    important = data.get("important", "")
    curious = data.get("curious", "")
    confusing = data.get("confusing", "")
    other = data.get("other", "")
    
    important = ", ".join(important)
    curious = ", ".join(curious)
    confusing = ", ".join(confusing)
    other = ", ".join(other)
    
    original_text = data.get("userinput", "")
    #previous_results = data.get("previous_results", [])
    text =  important + curious + confusing + other +original_text
    try:
        print(text)
        # クエリテキストの埋め込みベクトルを取得
        query_vector = fetch_embeddings(text, openai.api_key)
        # データベクトルと類似度を計算
        books = Book.query.with_entities(Book.id,Book.vector).all()
        print(len(books))
    # 指定の形式に変換
    
        vector_data = [{"id": book.id, "全体のベクトル": book.vector}  for book in books]
        results = []
        print(len(vector_data))
        for index, item in enumerate(vector_data):
            vecB = item.get("全体のベクトル")
            book_id = item.get("id") 
            if not isinstance(vecB, list):
                print(f"要約のベクトル化が配列ではありません: index {index}")
                similarity = -1
            else:
                similarity = cosine_similarity(query_vector, vecB)
            
            results.append({"id": book_id, "similarity": similarity})

        # 類似度順に並べ替えてトップ3を取得
        results.sort(key=lambda x: x["similarity"], reverse=True)
        filtered_results = [
            result for result in results 
        ][:3]

       #filtered_results = [
        #    result for result in results if result["index"] not in previous_results
        #][:3]

        # 結果のインデックスのみ抽出
        top_indices = [result["id"] for result in filtered_results]
        print(f"Top Book IDs: {top_indices}")


        displayContent = []

        for book_id in top_indices:
            book = Book.query.get(book_id)
            if book:
                displayContent.append(book.yoyaku)
        
        gender = current_user.data["gender"]
        preferred_genres = current_user.data["preferred_genres"]

        message = [
    {
        "role": "system",
        "content": f"""あなたはjsonデータジェネレータです。以下のリソースを読むための「私のため」の読書プランを考え、日本語で次のjson構造で出力してくださいjson以外の文字は含めないでください。
        プランの名前・目的・テーマを作成する際は、リソースのコンテキストに準拠し、「私」がその内容に興味を持つようにしてください。

        「私」：30代女性, {gender},{preferred_genres}に興味を持っている

        大事だと思っていることのメモ：{important}
        わからないと思っていることのメモ：{confusing}
        もっと知りたいと思っていることのメモ：{curious}

■1つ目のリソース:
    {displayContent[0]}

■2つ目のリソース:
    {displayContent[1]}

■3つ目のリソース:
    {displayContent[2]}

JSON構造の説明:
    {{planname: このプラン全体の名前。
    plans: [各プランの情報を格納する配列です。
       {{name: 1つ目のリソースを元にしたプランの名前。
         purpose: 1つ目のリソースを元にしたプランの目的。このプランを実行することで成長することなど、ユーザがプランを実行したくなるような言葉を簡単に添えてください。
         themes: 各プランのテーマ別の活動を格納する配列(3つ)。
        }},
        {{name: 2つ目のリソースを元にしたプランの名前。
         purpose: 2つ目のリソースを元にしたプランの目的。このプランを実行することで成長することなど、ユーザがプランを実行したくなるような言葉を簡単に添えてください。
         themes: 各プランのテーマ別の活動を格納する配列(3つ)。
        }},
        {{name: 3つ目のリソースを元にしたプランの名前。
         purpose: 3つ目のリソースを元にしたプランの目的。このプランを実行することで成長することなど、ユーザがプランを実行したくなるような言葉を簡単に添えてください。
         themes: 各プランのテーマ別の活動を格納する配列(3つ)。
        }}
    ]}}
"""
    },
    {
        "role": "user",
        "content": f"""{text}に関心を持つ人のための読書プラン(ファーザーリーディング)を3パターン作ってください、指定したjson構造で出力して。3つのプランは内容が重複しないようにし、互いに影響を受けないようにしてください。
"""
    }
]
         # OpenAI APIキーを設定
        openai.api_key = {app.config['SECRET_KEY']}
        # OpenAI GPT-3に質問を送信してレスポンスを取得
        #response = openai.Completion.create(
        #  engine="text-davinci-003",
        #  prompt=question,
        #  max_tokens=500
        #)

        # OpenAI ChatGPT APIへのリクエスト
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # モデルを指定
            messages = message
        )
        # レスポンスを整形
        formatted_response = json.loads(response['choices'][0]['message']['content'])#response.choices[0].text.strip()


        #for item in formatted_response:
          #  new_plan = Plan(
         #       name=item.name,
         #       purpose=item.purpose,
        #        themes = item.themes
        #        created_by_user_id=current_user.id,
        #        created_by=current_user.username,
        #        books= top_indices
        #    )
        print(type(formatted_response))
        
        # `created_by` フィールドに正しいインスタンスを取得して渡す
        user1 = User.query.filter_by(username=current_user.username).first()
        # `books` フィールドに正しいBookモデルのインスタンスを渡す
        book_instances = db.session.query(Book).filter(Book.id.in_([top_indices[0],top_indices[1],top_indices[2]])).all()
        print (book_instances)

        # トップインデックスから対応するBookインスタンスを取得
        book_instances = [Book.query.get(book_id) for book_id in top_indices if Book.query.get(book_id) is not None]
        print (book_instances)

        new_plan = Plan(
            name=formatted_response["planname"],
            data=formatted_response["plans"],
            created_by=user1,
            created_by_user_id =user1.id,
            books=book_instances  
        )

        db.session.add(new_plan)
        db.session.commit()

        return jsonify({
            "status": "success",
            "top_indices": top_indices,
            "plan" : {
                "name":formatted_response["planname"],
                "data":formatted_response["plans"],
            "created_by":user1.username, 
            }
        })
        # Planオブジェクトを作成
        name = f"Plan based on query: {query_text}"
        description = f"Generated plan using OpenAI embeddings for query: {query_text}"
        books = [user_notes[i].custom_text for i in top_indices]
        new_plan = Plan(
            name=name,
            description=description,
            created_by_user_id=current_user.id,
            created_by=current_user.username,
            books=books
        )
        db.session.add(new_plan)
        db.session.commit()

        return jsonify({
            "status": "success",
            "top_indices": top_indices,
            "plan_id": new_plan.id
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    question = (
        "私の名前は？"
        )
    
    # OpenAI APIキーを設定
    openai.api_key = {app.config['SECRET_KEY']}
    # OpenAI GPT-3に質問を送信してレスポンスを取得
    #response = openai.Completion.create(
    #  engine="text-davinci-003",
    #  prompt=question,
    #  max_tokens=500
    #)

    # OpenAI ChatGPT APIへのリクエスト
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # モデルを指定
        messages=[
            {"role": "system", "content": question}
        ]
    )
    # レスポンスを整形
    formatted_response = response['choices'][0]['message']['content']#response.choices[0].text.strip()

    print("Received data:", formatted_response)
    #current_user.type = formatted_response
    #db.session.commit()

    name = ""
    description = ""
    books = []
    new_plan = Plan(name=name, description=description, created_by_user_id=current_user.id, created_by = current_user.username, books = books)
    db.session.add(new_plan)
    db.session.commit()

    return jsonify(formatted_response)





@app.route('/account_edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    if request.method == 'POST':
        current_user.username = request.form['username']
        current_user.email = request.form['email']
        current_user.data = {key.replace('data_', '', 1): request.form[key] for key in request.form if key.startswith('data_')}
        current_user.visibility = {
            key.replace('visibility_', '', 1): ('on' in request.form.getlist(key))
    for key in request.form if key.startswith('visibility_')
        }        #current_user.type = request.form['type']
        db.session.commit()
        flash('Account updated successfully!')
        return redirect(url_for('profile'))
    
    # JSON ファイルからデータを読み込む
    learning_types = load_learning_types()["questions"]


    # ランダムに10個取得してリストにする
    random_questions = list(enumerate(random.sample(learning_types, 10)))

    # JSON ファイルからデータを読み込む
    learning_types1 = load_learning_types()["type"]


    # learningTypesはリスト、learningTypeは文字列であると仮定
    researcherType = next((item for item in learning_types1 if item["タイプ"] == current_user.type), None)


    return render_template('account_edit.html', user=current_user, random_questions = random_questions,researcherType =researcherType)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('home'))
    users = User.query.all()
    # GETリクエストの場合: データを表示
    books = Book.query.all()
    users = User.query.all()
    plans = Plan.query.all()
    columns = Column.query.all()
    notes = UserNote.query.all()
    return render_template('admin_dashboard.html', books=books, users=users, plans=plans, columns = columns, notes = notes)

@app.route('/update_book_a/<int:book_id>', methods=['POST'])
@login_required
def update_book_a(book_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    book = Book.query.get_or_404(book_id)
    data = request.json
    book.title = data.get('title', book.title)
    book.author = data.get('author', book.author)
    book.published_date = data.get('published_date', book.published_date)

    db.session.commit()
    return jsonify({'message': 'Book updated successfully'})



@app.route('/admin_dashboard/book/add_a', methods=['GET', 'POST'])
@login_required
def add_book_a():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        user_id = request.form["user_id"]
        author = request.form['author']
        published_date_str  = request.form['published_date']
        # 日付文字列をdateオブジェクトに変換
        if published_date_str:
            published_date = datetime.strptime(published_date_str, '%Y-%m-%d').date()
        else:
            published_date = None

        new_book = Book(title=title, author=author, published_date=published_date, user_id=user_id)
        db.session.add(new_book)
        db.session.commit()
        flash('書籍が追加されました。', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_book_a.html')

@app.route('/delete_book_a/<int:book_id>', methods=['POST'])
@login_required
def delete_book_a(book_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    return jsonify({'message': 'Book deleted successfully'})


@app.route("/api/books", methods=["GET"])
def get_books():
    books = Book.query.all()
    books_data = [
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "vector": book.vector,
            "content": book.content
        }
        for book in books
    ]
    return jsonify(books_data)


#ノート管理画面
@app.route('/update_note_a/<int:note_id>', methods=['POST'])
@login_required
def update_note_a(note_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    note = UserNote.query.get_or_404(note_id)
    data = request.json
    note.title = data.get('title', note.title)
    note.author = data.get('author', note.author)
    note.published_date = data.get('published_date', note.published_date)

    db.session.commit()
    return jsonify({'message': 'note updated successfully'})



@app.route('/admin_dashboard/note/add_a', methods=['GET', 'POST'])
@login_required
def add_note_a():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        user_id = request.form["user_id"]
        author = request.form['author']
        published_date_str  = request.form['published_date']
        # 日付文字列をdateオブジェクトに変換
        if published_date_str:
            published_date = datetime.strptime(published_date_str, '%Y-%m-%d').date()
        else:
            published_date = None

        new_note = UserNote(title=title, author=author, published_date=published_date, user_id=user_id)
        db.session.add(new_note)
        db.session.commit()
        flash('書籍が追加されました。', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_note_a.html')

@app.route('/delete_note_a/<int:note_id>', methods=['POST'])
@login_required
def delete_note_a(note_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    note = note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'note deleted successfully'})


#コラム管理画面
@app.route('/update_column_a/<int:column_id>', methods=['POST'])
@login_required
def update_column_a(column_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    column = Column.query.get_or_404(column_id)
    data = request.json
    column.title = data.get('title', column.title)
    column.author = data.get('author', column.author)
    column.published_date = data.get('published_date', column.published_date)

    db.session.commit()
    return jsonify({'message': 'column updated successfully'})



@app.route('/admin_dashboard/column/add_a', methods=['GET', 'POST'])
@login_required
def add_column_a():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        user_id = request.form["user_id"]
        author = request.form['author']
        published_date_str  = request.form['published_date']
        # 日付文字列をdateオブジェクトに変換
        if published_date_str:
            published_date = datetime.strptime(published_date_str, '%Y-%m-%d').date()
        else:
            published_date = None

        new_column = Column(title=title, author=author, published_date=published_date, user_id=user_id)
        db.session.add(new_column)
        db.session.commit()
        flash('書籍が追加されました。', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_column_a.html')

@app.route('/delete_column_a/<int:column_id>', methods=['POST'])
@login_required
def delete_column_a(column_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    column = Column.query.get_or_404(column_id)
    db.session.delete(column)
    db.session.commit()
    return jsonify({'message': 'column deleted successfully'})





#プラン管理画面f
@app.route('/update_plan_a/<int:plan_id>', methods=['POST'])
@login_required
def update_plan_a(plan_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    plan = Plan.query.get_or_404(plan_id)
    data = request.json
    plan.title = data.get('title', plan.title)
    plan.author = data.get('author', plan.author)
    plan.published_date = data.get('published_date', plan.published_date)

    db.session.commit()
    return jsonify({'message': 'plan updated successfully'})



@app.route('/admin_dashboard/plan/add_a', methods=['GET', 'POST'])
@login_required
def add_plan_a():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        user_id = request.form["user_id"]
        author = request.form['author']
        published_date_str  = request.form['published_date']
        # 日付文字列をdateオブジェクトに変換
        if published_date_str:
            published_date = datetime.strptime(published_date_str, '%Y-%m-%d').date()
        else:
            published_date = None

        new_plan = Plan(title=title, author=author, published_date=published_date, user_id=user_id)
        db.session.add(new_plan)
        db.session.commit()
        flash('書籍が追加されました。', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_plan.html')

@app.route('/delete_plan_a/<int:plan_id>', methods=['POST'])
@login_required
def delete_plan_a(plan_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    plan = Plan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    return jsonify({'message': 'plan deleted successfully'})




@app.route('/promote/<int:user_id>', methods=['POST'])
@login_required
def promote_to_admin(user_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('home'))

    user = User.query.get(user_id)
    if user:
        user.is_admin = True
        db.session.commit()
        flash(f'{user.username} has been promoted to admin.')
    else:
        flash('User not found.')
    return redirect(url_for('admin_dashboard'))



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))




@app.route('/add_read_book', methods=['POST'])
def add_read_book():
    data = request.json
    user_id = data.get('user_id')
    book_id = data.get('book_id')

    # ユーザーと書籍の存在を確認
    user = User.query.get(user_id)
    book = Book.query.get(book_id)

    if not user or not book:
        return jsonify({"error": "User or Book not found"}), 404

    # ユーザーに書籍を追加
    user.read_books.append(book)
    db.session.commit()

    return jsonify({"message": f"User {user_id} read Book {book_id} successfully"}), 201


@app.route('/get_read_books/<int:user_id>', methods=['GET'])
def get_read_books(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # 読んだ書籍を取得
    read_books = [{"id": book.id, "title": book.title, "author": book.author} for book in user.read_books]
    return jsonify({"user_id": user_id, "read_books": read_books})

@app.route('/add_column', methods=['POST'])
def add_column():
    data = request.json
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    title = data.get('title')
    content = data.get('content')

    # ユーザーと書籍の存在確認
    user = User.query.get(user_id)
    book = Book.query.get(book_id)

    if not user or not book:
        return jsonify({"error": "User or Book not found"}), 404

    # 新しいコラムを作成
    new_column = Column(
        title=title,
        content=content,
        user_id=user_id,
        book_id=book_id
    )
    db.session.add(new_column)
    db.session.commit()

    return jsonify({"message": "Column added successfully"}), 201

@app.route('/get_columns_by_user/<int:user_id>', methods=['GET'])
def get_columns_by_user(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # ユーザーが書いたコラムを取得
    columns = [
        {"id": column.id, "title": column.title, "content": column.content, "book_id": column.book_id}
        for column in user.columns
    ]
    return jsonify({"user_id": user_id, "columns": columns})

@app.route('/get_columns_by_book/<int:book_id>', methods=['GET'])
def get_columns_by_book(book_id):
    book = Book.query.get(book_id)

    if not book:
        return jsonify({"error": "Book not found"}), 404

    # 書籍に関連するコラムを取得
    columns = [
        {"id": column.id, "title": column.title, "content": column.content, "user_id": column.user_id}
        for column in book.columns
    ]
    return jsonify({"book_id": book_id, "columns": columns})

# ハイライトされたメモを保存
@app.route('/save_note', methods=['POST'])
@login_required
def save_note():
    data = request.json
    highlight_text = data.get('highlight_text')
    source_type = data.get('source_type')
    source_id = data.get('source_id')
    memo_type = data.get('memo_type')
    custom_text = data.get('custom_text')

    # メモをデータベースに保存
    new_note = UserNote(user_id=current_user.id, 
    source_type = source_type,
    source_id = source_id,
    custom_text = custom_text,
    memo_type = memo_type,
    highlight_text=highlight_text)
    db.session.add(new_note)
    db.session.commit()

    return jsonify({'message': 'Note saved successfully!'})




@app.cli.command('bookseed')
def bookseed():
    vector = load_vector()
    books = []
    for item in vector:
        print(item["著者"])
        book = Book(
            title=item["タイトル1"],
            author=item["著者"],
            content = item["本文"],
            yoyaku = item["章の要約"],
            vector = item["全体のベクトル"],
            published_date=datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            user_id=1
        )    
     # 書籍を挿入
        db.session.add(book)
    db.session.commit()


@app.cli.command('seed')

def seed():
    db.drop_all()  # すべてのテーブルを削除
    db.create_all()  # すべてのテーブルを再作成
    print("データベースをリセットしました。")
    """Add sample data to the database."""


    db.session.commit()


    dataa = {
        "gender": random.choice(["男", "女", "他"]),
        "occupation": "b",
        "education": "c",
        "hobbies": "d",
        "favorite_books_movies_music": random.choice(["演歌", "舞踊", "映画"]),
        "values_beliefs": "e",
        "reading_frequency": "f",
        "preferred_genres": "g",
        "reading_purpose": "h",
        "reading_style": "i",
        "daily_routine": "j",
        "living_environment":"k",
        "stress_tolerance": "l",
        "social_role": "m",
        "cultural_background": "n",
        "learning_style": "o",
        "reading_goals": "p",
        "book_expectation": "q"
    }

    visibility = {
        "gender": True,
        "occupation": random.choice([True, False]),
        "education": random.choice([True, False]),
        "hobbies": random.choice([True, False]),
        "favorite_books_movies_music": random.choice([True, False]),
        "values_beliefs": random.choice([True, False]),
        "reading_frequency": random.choice([True, False]),
        "preferred_genres": random.choice([True, False]),
        "reading_purpose": random.choice([True, False]),
        "reading_style": random.choice([True, False]),
        "daily_routine": random.choice([True, False]),
        "living_environment":random.choice([True, False]),
        "stress_tolerance": random.choice([True, False]),
        "social_role": random.choice([True, False]),
        "cultural_background": random.choice([True, False]),
        "learning_style": random.choice([True, False]),
        "reading_goals": random.choice([True, False]),
        "book_expectation": random.choice([True, False])
    }

    visibility1 = {
        "gender": True,
        "occupation": random.choice([True, False]),
        "education": False,
        "hobbies": random.choice([True, False]),
        "favorite_books_movies_music": False,
        "values_beliefs": random.choice([True, False]),
        "reading_frequency": random.choice([True, False]),
        "preferred_genres": random.choice([True, False]),
        "reading_purpose": random.choice([True, False]),
        "reading_style": random.choice([True, False]),
        "daily_routine": random.choice([True, False]),
        "living_environment":random.choice([True, False]),
        "stress_tolerance": random.choice([True, False]),
        "social_role": random.choice([True, False]),
        "cultural_background": random.choice([True, False]),
        "learning_style": random.choice([True, False]),
        "reading_goals": random.choice([True, False]),
        "book_expectation": random.choice([True, False])
    }

    visibility2 = {
        "gender":  False,
        "occupation": random.choice([True, False]),
        "education": False,
        "hobbies": random.choice([True, False]),
        "favorite_books_movies_music": False,
        "values_beliefs": random.choice([True, False]),
        "reading_frequency": random.choice([True, False]),
        "preferred_genres":  False,
        "reading_purpose": random.choice([True, False]),
        "reading_style": random.choice([True, False]),
        "daily_routine": random.choice([True, False]),
        "living_environment":random.choice([True, False]),
        "stress_tolerance": random.choice([True, False]),
        "social_role": random.choice([True, False]),
        "cultural_background": random.choice([True, False]),
        "learning_style": random.choice([True, False]),
        "reading_goals": random.choice([True, False]),
        "book_expectation": random.choice([True, False])
    }

    # Add sample users
    sample_users = [
        User(username='sumakokima', email='makiko@example.com', password='password', is_admin=True, data = dataa,visibility = visibility),
        User(username='admin', email='admin@example.com', password='password', is_admin=True, data = dataa,visibility = visibility1),
        User(username='user1', email='user1@example.com', password='password', profile_image='default.jpg', data = dataa,visibility = visibility2),
        User(username='user2', email='user2@example.com', password='password', profile_image='default.jpg', data = dataa,visibility = visibility),
        User(username="Alice", email="alice@example.com", password="password1",data = dataa,visibility = visibility),
        User(username="Bob", email="bob@example.com", password="password2",data = dataa,visibility = visibility),
        User(username="Charlie", email="charlie@example.com", password="password3",data = dataa,visibility = visibility)
    ]

    db.session.bulk_save_objects(sample_users)
    db.session.commit()
    print("Sample data added to the database!")


    

    # ユーザーと書籍の読書履歴（user_books中間テーブル）のシードデータ
    read_books_data = [
        {"user_id": 1, "book_id": 1},
        {"user_id": 1, "book_id": 2},
        {"user_id": 2, "book_id": 2},
        {"user_id": 2, "book_id": 3},
        {"user_id": 3, "book_id": 1},
        {"user_id": 3, "book_id": 4}
    ]

    # コラムのシードデータ
    columns = [
        {
            "title": "Flask入門とPythonプログラミングの比較",
            "content": "FlaskとPythonプログラミングを比較して学んだことをまとめました。",
            "user_id": 1,
            "book_ids": [1, 2,3]
        },
        {
            "title": "データベース設計の基本",
            "content": "データベース設計の重要なポイントを解説します。",
            "user_id": 2,
            "book_ids": [2, 3,5]
        },
        {
            "title": "Webアプリ開発におけるフレームワークの活用",
            "content": "Webアプリ開発で使用したフレームワークの利点をまとめました。",
            "user_id": 3,
            "book_ids": [1, 4,6]
        }
    ]

   

    # 読書履歴を挿入
    for data in read_books_data:
        user = User.query.get(data["user_id"])
        book = Book.query.get(data["book_id"])
        if book not in user.read_books:
            user.read_books.append(book)
        
    # コラムを挿入
    for column_data in columns:
        user = User.query.get(column_data["user_id"])
        related_books = Book.query.filter(Book.id.in_(column_data["book_ids"])).all()

        new_column = Column(
            title=column_data["title"],
            content=column_data["content"],
            user_id=column_data["user_id"]
        )
        # コラムに関連付ける書籍を設定
        new_column.books.extend(related_books)

        db.session.add(new_column)
    db.session.commit()


    user1 = User.query.filter_by(username='sumakokima').first()
    user2 = User.query.filter_by(id=2).first()
    user3 = User.query.filter_by(id=3).first()
    book1 = Book.query.filter_by(id=1).first()
    book2 = Book.query.filter_by(id=2).first()
    book3 = Book.query.filter_by(id=3).first()
    book4 = Book.query.filter_by(id=4).first()
    book5 = Book.query.filter_by(id=5).first()

    if not (user1 and user2 and book1 and book2):
        print("Error: Required users or books not found.")
        return



    # プランを作成
    sample_plan = Plan(
        name = "Web開発の基本プラン",
        data=[
            {
              "name":"FlaskとPythonを使ったWeb開発の基本を学ぶプランです。",
              "theme":"FlaskとPythonを使う。",
              "purpose":"基本を学びましょう。"
              },
              {
                  "name":"FlaskとPythonを使ったWeb開発の基本を学ぶプランです。",
              "theme":"FlaskとPythonを使う。",
              "purpose":"基本を学びましょう。"
              },
              {
                  "name":"FlaskとPythonを使ったWeb開発の基本を学ぶプランです。",
              "theme":"FlaskとPythonを使う。",
              "purpose":"基本を学びましょう。"
              }
              ],
        created_by=user1,
        created_by_user_id =user1.id
    )
    # プランに利用者と本を追加
    sample_plan.users.extend([user1, user2])
    sample_plan.books.extend([book1, book2])

    db.session.add(sample_plan)

    db.session.commit()
    print("Sample plan added to the database!")


    column1 = Column.query.filter_by(id=1).first()


    # 自分メモ作成
    note1 = UserNote(
        user_id=user1.id,
        source_type="book",
        source_id=book1.id,
        highlight_text="Pythonは初心者に最適な言語。",
        custom_text=None
    )
    note2 = UserNote(
        user_id=user1.id,
        source_type="custom",
        source_id=None,
        highlight_text=None,
        custom_text="次に学びたいこと: データ分析と機械学習。"
    )
    note3 = UserNote(
        user_id=user2.id,
        source_type="column",
        source_id=column1.id,
        highlight_text="Flaskは拡張性が高い。",
        custom_text=None
    )
    db.session.add_all([note1, note2, note3])
    db.session.commit()

    print("Seed data inserted successfully!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # データベースのテーブルを作成
    app.run(debug=True, port=8000)
