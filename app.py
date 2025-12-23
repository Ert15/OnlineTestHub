from doctest import testmod
from flask import Flask, render_template, request, redirect, session
import psycopg2
import re
import sqlite3
from flask_babel import Babel, _

app = Flask(__name__)
app.secret_key = 'secretkey'

# Инициализация Flask-Babel
babel = Babel(app)

# Поддерживаемые языки
LANGUAGES = ['en', 'ru']

# Функция для получения языка
def get_locale():
    return session.get('lang', 'ru')  # По умолчанию русский язык

babel.init_app(app, locale_selector=get_locale)

# Маршрут для изменения языка
@app.route('/set_language/<language>')
def set_language(language):
    if language in LANGUAGES:
        session['lang'] = language
    return redirect(request.referrer)  # Перенаправляем на предыдущую страницу


# Создадим тест заранее в коде (без использования базы данных)
test_data = {
    'title': 'Math Test',
    'description': 'Test your basic math knowledge.',
    'questions': [
        {
            'question_text': 'What is 1 + 1?',
            'options': ['1', '2', '3', '4'],
            'correct_answer': '2'
        },
        {
            'question_text': 'What is 2 + 3?',
            'options': ['4', '5', '6', '7'],
            'correct_answer': '5'
        },
        {
            'question_text': 'What is 10 - 5?',
            'options': ['3', '4', '5', '6'],
            'correct_answer': '5'
        }
    ]
}

# Подключение к базе данных
conn = psycopg2.connect(
    host="localhost",
    database="postgres",  
    user="postgres",
    password="1515"
)


# Функция для подключения к базе данных SQLite


# Функции для валидации данных
def is_valid_email(email):
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email) is not None

def is_valid_name(name):
    return re.match(r'^[A-Za-zА-Яа-яЁё\s]+$', name) is not None


@app.route('/')
def home():
    if 'user' in session:
        if session['user']['role'] == 'Admin':
            return redirect('/admin_dashboard')
       
        elif session['user']['role'] == 'Student':
            return redirect('/student_dashboard')
        else:
            return redirect('/teacher_dashboard')  # Для админа перенаправляем на панель управления
        return redirect('/profile')  # Для других пользователей перенаправляем на профиль
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not is_valid_name(fullname):
            return "❌ Имя не должно содержать цифр!"

        if not is_valid_email(email):
            return "❌ Введите корректный email!"

        if not fullname or not email or not password:
            return "❌ Все поля обязательны!"

        cur = conn.cursor()
        cur.execute(
            'INSERT INTO "User" (FullName, Email, Password, Role) VALUES (%s, %s, %s, %s)',
            (fullname, email, password, role)
        )
        conn.commit()
        cur.close()
        return redirect('/login')  # После регистрации, перенаправляем на страницу входа

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        password = request.form.get('password')

        if not fullname or not password:
            return "Все поля обязательны!"

        cur = conn.cursor()
        cur.execute(
            'SELECT UserID, FullName, Email, Role FROM "User" WHERE FullName=%s AND Password=%s',
            (fullname, password)
        )
        user = cur.fetchone()
        cur.close()

        if user:
            session['user'] = {
                'id': user[0],
                'fullname': user[1],
                'email': user[2],
                'role': user[3]
            }
            return redirect('/')  # Перенаправляем на главную страницу
        else:
            return "❌ Неверное имя или пароль"

    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user', None)
    return redirect('/login')


@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/login')

    user_data = session['user']
    return render_template('profile.html', user=user_data)


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user' not in session or session['user']['role'] != 'Admin':
        return redirect('/login')  # Перенаправляем на страницу входа, если нет сессии или не admin

    cur = conn.cursor()

    # Количество студентов
    cur.execute('SELECT COUNT(*) FROM "User" WHERE Role = %s', ('Student',))
    student_count = cur.fetchone()[0]

    # Количество тестов
    cur.execute('SELECT COUNT(*) FROM "Test"')
    test_count = cur.fetchone()[0]

    # Количество учителей
    cur.execute('SELECT COUNT(*) FROM "User" WHERE Role = %s', ('Teacher',))
    teacher_count = cur.fetchone()[0]

    cur.close()

    # Отправляем данные в шаблон
    return render_template('admin_dashboard.html', student_count=student_count, test_count=test_count, teacher_count=teacher_count)

@app.route('/admin/users', methods=['GET'])
def admin_users():
    if 'user' not in session or session['user']['role'] != 'Admin':
        return redirect('/login')  # Перенаправляем на страницу входа, если нет сессии или не admin

    search_query = request.args.get('search', '')  # Получаем поисковый запрос из GET-параметра
    cur = conn.cursor()

    # Если есть запрос на поиск, фильтруем по имени, email или роли
    if search_query:
        cur.execute('''
            SELECT UserID, FullName, Email, Role
            FROM "User"
            WHERE FullName ILIKE %s OR Email ILIKE %s OR Role ILIKE %s
        ''', ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
    else:
        cur.execute('SELECT UserID, FullName, Email, Role FROM "User"')

    users = cur.fetchall()
    cur.close()

    return render_template('admin_users.html', users=users)



@app.route('/admin/tests', methods=['GET'])
def admin_tests():
    if 'user' not in session or session['user']['role'] == 'Student':
        return redirect('/login')  # Перенаправляем на страницу входа, если нет сессии или не admin

    search_query = request.args.get('search', '')  # Получаем поисковый запрос из GET-параметра
    cur = conn.cursor()

    # Если есть запрос на поиск, фильтруем по названию или описанию тестов
    if search_query:
        cur.execute('''
            SELECT TestID, Title, Description
            FROM "Test"
            WHERE Title ILIKE %s OR Description ILIKE %s
        ''', ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cur.execute('SELECT TestID, Title, Description FROM "Test"')

    tests = cur.fetchall()
    cur.close()

    return render_template('admin_tests.html', tests=tests)



@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not is_valid_name(fullname):
            return "❌ Имя не должно содержать цифр!"
        if not is_valid_email(email):
            return "❌ Введите корректный email!"
        if not fullname or not email or not password:
            return "❌ Все поля обязательны!"

        cur = conn.cursor()
        cur.execute(
            'INSERT INTO "User" (FullName, Email, Password, Role) VALUES (%s, %s, %s, %s)',
            (fullname, email, password, role)
        )
        conn.commit()
        cur.close()
        return redirect('/admin/users')  # Перенаправляем обратно на страницу пользователей

    return render_template('add_user.html')


@app.route('/admin/add_test', methods=['GET', 'POST'])
def add_test():
    if request.method == 'POST':
        test_name = request.form.get('test_name')
        description = request.form.get('description')
        teacher_id = session['user']['id']  # Учитель — это тот, кто создает тест

        if not test_name or not description:
            return "❌ Все поля обязательны!"

        cur = conn.cursor()
        cur.execute(
            'INSERT INTO "Test" (Title, Description, TeacherID) VALUES (%s, %s, %s)',
            (test_name, description, teacher_id)
        )
        conn.commit()
        cur.close()
        return redirect('/admin/tests')  # Перенаправляем обратно на страницу тестов

    return render_template('add_test.html')


@app.route('/admin/delete_user/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    try:
        cur = conn.cursor()

        # Удаляем все записи из таблицы Answer, которые ссылаются на StudentTest, связанные с пользователем
        cur.execute('DELETE FROM "Answer" WHERE StudentTestID IN (SELECT StudentTestID FROM "StudentTest" WHERE StudentID = %s)', (user_id,))

        # Удаляем все записи из таблицы StudentTest, которые ссылаются на пользователя
        cur.execute('DELETE FROM "StudentTest" WHERE StudentID = %s', (user_id,))

        # Удаляем все записи из таблицы RecentActivity, которые ссылаются на пользователя
        cur.execute('DELETE FROM "RecentActivity" WHERE UserID = %s', (user_id,))

        # Теперь удаляем самого пользователя
        cur.execute('DELETE FROM "User" WHERE UserID = %s', (user_id,))

        # Сохраняем изменения в базе данных
        conn.commit()
        cur.close()

        return redirect('/admin/users')  # После удаления перенаправляем на страницу пользователей

    except Exception as e:
        conn.rollback()  # Откатываем транзакцию в случае ошибки
        print(f"Error deleting user: {e}")
        return "Ошибка при удалении пользователя"

@app.route('/admin/delete_test/<int:test_id>', methods=['GET'])
def delete_test(test_id):
    try:
        cur = conn.cursor()

        # Удаляем все записи из таблицы Answer, которые ссылаются на StudentTest, связанный с тестом
        cur.execute('DELETE FROM "Answer" WHERE StudentTestID IN (SELECT StudentTestID FROM "StudentTest" WHERE TestID = %s)', (test_id,))

        # Удаляем все записи из таблицы StudentTest, которые ссылаются на тест
        cur.execute('DELETE FROM "StudentTest" WHERE TestID = %s', (test_id,))

        # Удаляем все варианты ответов, связанные с вопросами в тесте
        cur.execute('DELETE FROM "Option" WHERE QuestionID IN (SELECT QuestionID FROM "Question" WHERE TestID = %s)', (test_id,))

        # Удаляем все вопросы, связанные с тестом
        cur.execute('DELETE FROM "Question" WHERE TestID = %s', (test_id,))

        # Удаляем сам тест
        cur.execute('DELETE FROM "Test" WHERE TestID = %s', (test_id,))

        # Сохраняем изменения в базе данных
        conn.commit()
        cur.close()

        # Перенаправляем на страницу управления тестами
        return redirect('/admin/tests')
    
    except Exception as e:
        conn.rollback()  # Откатываем транзакцию в случае ошибки
        print(f"Error deleting test: {e}")
        return f"Ошибка при удалении теста: {e}"


@app.route('/admin/manage_questions', methods=['GET', 'POST'])
def manage_questions():
    cur = conn.cursor()

    # Получаем список всех тестов
    cur.execute('SELECT TestID, Title FROM "Test"')
    tests = cur.fetchall()

    if request.method == 'POST':
        test_id = request.form.get('test_id')
        question_text = request.form.get('question_text')
        question_type = request.form.get('question_type')
        options = request.form.getlist('options')
        correct_answer = request.form.get('correct_answer')

        # Вставляем новый вопрос в базу данных
        cur.execute('''
            INSERT INTO "Question" (TestID, QuestionText, QuestionType) 
            VALUES (%s, %s, %s) RETURNING QuestionID
        ''', (test_id, question_text, question_type))

        question_id = cur.fetchone()[0]

        # Вставляем варианты ответа
        for i, option in enumerate(options):
            is_correct = True if option == correct_answer else False
            cur.execute('''
                INSERT INTO "Option" (QuestionID, OptionText, IsCorrect) 
                VALUES (%s, %s, %s)
            ''', (question_id, option, is_correct))

        conn.commit()

    # Получаем все вопросы из базы данных
    cur.execute('''
        SELECT q.QuestionID, q.QuestionText, t.Title, q.QuestionType
        FROM "Question" q
        JOIN "Test" t ON q.TestID = t.TestID
    ''')
    questions = cur.fetchall()

    cur.close()

    return render_template('manage_questions.html', tests=tests, questions=questions)

@app.route('/delete_question/<int:question_id>', methods=['GET'])
def delete_question(question_id):
    cur = conn.cursor()
    cur.execute('DELETE FROM "Option" WHERE QuestionID = %s', (question_id,))
    cur.execute('DELETE FROM "Question" WHERE QuestionID = %s', (question_id,))
    conn.commit()
    cur.close()
    return redirect('/admin/manage_questions')


@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user' not in session or session['user']['role'] != 'Teacher':
        return redirect('/login')  # Redirect to login if not teacher

    # Fetch the list of tests created by the teacher
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM "Test"')
    tests = cur.fetchall()

    # Fetch the number of students
    cur.execute('SELECT COUNT(*) FROM "User" WHERE Role = %s', ('Student',))
    student_count = cur.fetchone()[0]

    # Fetch the number of tests
    cur.execute('SELECT COUNT(*) FROM "Test"')
    test_count = cur.fetchone()[0]

    cur.close()

    return render_template('teacher_dashboard.html', tests=tests, student_count=student_count, test_count=test_count)


@app.route('/student_dashboard')
def student_dashboard():
    # Получаем тесты, доступные студенту
    cur = conn.cursor()
    cur.execute('SELECT TestID, Title, Description FROM "Test"')
    tests = cur.fetchall()

    # Получаем результаты студента
    student_id = session['user']['id']
    cur.execute('SELECT TestID, Score FROM "StudentTest" WHERE StudentID = %s', (student_id,))
    results = cur.fetchall()

    # Преобразуем результаты в словарь {test_id: score}
    test_results = {result[0]: result[1] for result in results}

    cur.close()

    # Отправляем данные в шаблон
    return render_template('student_dashboard.html', tests=tests, test_results=test_results)


@app.route('/create_test', methods=['GET', 'POST'])
def create_test():
    if request.method == 'POST':
        test_title = request.form.get('test_title')
        test_description = request.form.get('test_description')
        questions = request.form.getlist('question_text')  # Получаем все вопросы
        options = request.form.getlist('options_text')  # Получаем все варианты
        correct_answers = request.form.getlist('correct_answer')  # Получаем все правильные ответы

        # Проверка, что данные не пустые
        if not test_title or not test_description:
            return "❌ Test title and description are required!"

        # Проверка, что количество вопросов, вариантов и правильных ответов совпадает
        if len(questions) == 0 or len(options) == 0 or len(correct_answers) == 0:
            return "❌ Questions, options, and correct answers cannot be empty!"

        if len(questions) != len(options) or len(options) != len(correct_answers):
            return f"❌ The number of questions, options, and correct answers must match! Questions: {len(questions)}, Options: {len(options)}, Correct Answers: {len(correct_answers)}"

        cur = conn.cursor()
        cur.execute(
            'INSERT INTO "Test" (Title, Description) VALUES (%s, %s) RETURNING TestID',
            (test_title, test_description)
        )
        test_id = cur.fetchone()[0]  # Получаем ID созданного теста
        conn.commit()

        # Добавление вопросов и вариантов ответов
        for i in range(len(questions)):
            cur.execute(
                'INSERT INTO "Question" (TestID, QuestionText) VALUES (%s, %s) RETURNING QuestionID',
                (test_id, questions[i])
            )
            question_id = cur.fetchone()[0]  # Получаем ID вопроса
            conn.commit()

            # Варианты ответа
            option_list = options[i].split(';')  # Разделяем варианты через точку с запятой
            for option in option_list:
                cur.execute(
                    'INSERT INTO "Option" (QuestionID, OptionText, IsCorrect) VALUES (%s, %s, %s)',
                    (question_id, option, option == correct_answers[i])
                )
                conn.commit()

        cur.close()
        return redirect('/view_test')  # Перенаправляем на страницу просмотра теста

    return render_template('create_test.html')

@app.route('/take_test', methods=['GET', 'POST'])
def take_test():
    test_data = {
        'title': 'Math Test',
        'description': 'Test your basic math knowledge.',
        'questions': [
            {
                'question_text': 'What is 1 + 1?',
                'options': ['2', '1', '3', ],
                'correct_answer': '2'
            },
            {
                'question_text': 'What is 2 + 3?',
                'options': ['4', '5', '6', ],
                'correct_answer': '5'
            },
            {
                'question_text': 'What is 10 - 5?',
                'options': ['3', '4', '5', ],
                'correct_answer': '5'
            }
        ]
    }

    if request.method == 'POST':
        student_answers = request.form.to_dict()  # Получаем все ответы студента
        score = 0
        total_questions = len(test_data['questions'])

        # Проверка, что все вопросы выбраны
        for idx, question in enumerate(test_data['questions']):
            student_answer = student_answers.get(f'answer_{idx + 1}')
            if not student_answer:
                return "❌ Вы должны выбрать ответ для каждого вопроса."

            # Сравниваем выбранный ответ с правильным
            correct_answer = question['correct_answer']
            if student_answer == correct_answer:
                score += 1

        # Показываем результат
        return render_template('result.html', score=score, total=total_questions)

    return render_template('take_test.html', test=test_data)



if __name__ == '__main__':
    app.run(debug=True)