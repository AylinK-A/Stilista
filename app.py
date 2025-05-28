from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from forms import RegistrationForm, LoginForm, AvatarUploadForm
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 's3cr3t_k3y_123498'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'market.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images/uploads/'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

migrate = Migrate(app, db)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='images/uploads/default.jpg')
    favorites = db.relationship('Favorite', backref='user', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.String(50))
    image = db.Column(db.String(200))

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user:
        print(f'Загружен пользователь: {user.username}')
    else:
        print(f'Не найден пользователь с ID {user_id}')
    return user

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/home')
@login_required
def home():
    items = Item.query.all()
    print(f"Items: {items}")
    return render_template('home.html', items=items)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Создаем хеш пароля
        hashed_password = generate_password_hash(form.password.data)
        print(f"Хеш пароля: {hashed_password}")  # Логируем хеш пароля

        # Создаем объект пользователя
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        print(f"Пользователь {user.username} создается.")  # Логируем создание пользователя
        
        # Добавляем пользователя в сессию
        db.session.add(user)
        print("Пользователь добавлен в сессию.")  # Логируем добавление в сессию
        
        # Сохраняем в базе данных
        db.session.commit()
        print(f"Пользователь {user.username} сохранен в базе данных.")  # Логируем коммит

        # Сообщение об успешной регистрации
        flash('Регистрация успешна. Теперь войдите в аккаунт.')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            # Логируем хеш пароля для проверки
            print("Введённый пароль:", form.password.data)
            print("Пароль из базы данных:", user.password)
            
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('account'))
            else:
                flash('Неверные имя пользователя или пароль')
        else:
            flash('Неверные имя пользователя или пароль')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = AvatarUploadForm()
    fav_items = [Item.query.get(fav.item_id) for fav in current_user.favorites]
    return render_template('account.html', favorites=fav_items, form=form)

@app.route('/logout', methods=['POST'])
@login_required
def upload_avatar():
    form = AvatarUploadForm()
    if form.validate_on_submit():
        file = form.avatar.data
        if file:
            print(f"Загружен файл: {file.filename}")
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                print(f"Путь для сохранения: {filepath}")
                try:
                    file.save(filepath)
                    current_user.avatar = f'images/uploads/{filename}'
                    db.session.commit()
                    print(f"Аватар обновлен: {current_user.avatar}")
                except Exception as e:
                    print(f"Ошибка при сохранении файла: {e}")
            else:
                print('Неверный формат файла')
        else:
            print("Файл не был выбран.")
    else:
        print("Форма не прошла валидацию.")
        for field, errors in form.errors.items():
            for error in errors:
                print(f"Ошибка в поле {field}: {error}")  # Вывод ошибок валидации
    return redirect(url_for('account'))


@app.route('/favorite/<int:item_id>', methods=['POST'])
@login_required
def favorite(item_id):
    exists = Favorite.query.filter_by(user_id=current_user.id, item_id=item_id).first()
    if not exists:
        fav = Favorite(user_id=current_user.id, item_id=item_id)
        db.session.add(fav)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/reset_items')
def reset_items():
    Item.query.delete()
    db.session.commit()
    items = [
        Item(name='Платье', price='2900', image='dress.jpg'),
        Item(name='Футболка-поло', price='2990', image='T-shirt.jpg'),
        Item(name='Футболка', price='2090', image='T-shirt1.jpg'),
        Item(name='Юбка', price='2590', image='dress1.jpg')
    ]
    db.session.add_all(items)
    db.session.commit()
    return "Товары обновлены!"

#if __name__ == '__main__':
    #with app.app_context():
        #db.create_all()
    #app.run(debug=True)
