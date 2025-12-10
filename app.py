# app.py
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, TelField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import io
import pandas as pd

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'

# 使用相对路径，确保在云服务器上也能找到数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'address_book.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload config
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'xls'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


def allowed_file(filename, allowed=ALLOWED_EXTENSIONS):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(200), default='default.png')
    contacts = db.relationship('Contact', backref='owner', lazy=True)


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # keep compatibility fields (optional)
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    bookmarked = db.Column(db.Boolean, default=False)  # 新增收藏字段
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    methods = db.relationship('ContactMethod', backref='contact', lazy=True, cascade="all, delete-orphan")


class ContactMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # e.g., phone, email, social, address
    value = db.Column(db.String(200), nullable=False)


# Forms
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=50)])
    email = EmailField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(), EqualTo('password', message='两次密码不一致')
    ])
    submit = SubmitField('注册')


class LoginForm(FlaskForm):
    email = EmailField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')


class ContactForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired()])
    phone = TelField('电话')  # optional single field for compatibility
    email = EmailField('邮箱')
    address = StringField('地址')
    submit = SubmitField('保存')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
@login_required
def index():
    search_query = request.args.get('search', '')
    only_bookmarked = request.args.get('bookmarked', '') == '1'
    q = Contact.query.filter_by(user_id=current_user.id)
    if search_query:
        q = q.filter(Contact.name.contains(search_query))
    if only_bookmarked:
        q = q.filter_by(bookmarked=True)
    contacts = q.all()
    form = ContactForm()
    return render_template('index.html', contacts=contacts, form=form, edit_id=None)


@app.route('/add_contact', methods=['POST'])
@login_required
def add_contact():
    # 支持多联系方式：前端以 method_type[] / method_value[] 提交
    name = request.form.get('name', '').strip()
    if not name:
        flash('姓名不能为空', 'danger')
        return redirect(url_for('index'))

    new_contact = Contact(name=name, user_id=current_user.id)
    db.session.add(new_contact)
    db.session.flush()  # get id

    # process method lists
    types = request.form.getlist('method_type[]')
    values = request.form.getlist('method_value[]')
    for t, v in zip(types, values):
        v = (v or '').strip()
        t = (t or '').strip().lower()
        if v and t:
            cm = ContactMethod(contact_id=new_contact.id, type=t, value=v)
            db.session.add(cm)
    db.session.commit()
    flash('联系人添加成功！', 'success')
    return redirect(url_for('index'))


@app.route('/edit_contact/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if contact.owner != current_user:
        flash('无权限操作此联系人', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('姓名不能为空', 'danger')
            return redirect(url_for('index'))
        contact.name = name
        # 删除原有 methods 再添加（简单可靠）
        ContactMethod.query.filter_by(contact_id=contact.id).delete()
        types = request.form.getlist('method_type[]')
        values = request.form.getlist('method_value[]')
        for t, v in zip(types, values):
            v = (v or '').strip()
            t = (t or '').strip().lower()
            if v and t:
                cm = ContactMethod(contact_id=contact.id, type=t, value=v)
                db.session.add(cm)
        db.session.commit()
        flash('联系人更新成功！', 'success')
        return redirect(url_for('index'))

    # GET: render index with edit context
    contacts = Contact.query.filter_by(user_id=current_user.id).all()

    # --- 修复 Bug 的关键部分 ---
    # 实例化一个表单传递给模板，解决 CSRF 令牌报错问题
    form = ContactForm()

    return render_template('index.html',
                           contacts=contacts,
                           edit_contact=contact,
                           edit_id=contact_id,
                           edit_form=form)  # 必须传递 edit_form


@app.route('/delete_contact/<int:contact_id>')
@login_required
def delete_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if contact.owner != current_user:
        flash('无权限操作此联系人', 'danger')
        return redirect(url_for('index'))
    db.session.delete(contact)
    db.session.commit()
    flash('联系人已删除', 'success')
    return redirect(url_for('index'))


@app.route('/toggle_bookmark/<int:contact_id>')
@login_required
def toggle_bookmark(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if contact.owner != current_user:
        flash('无权限操作此联系人', 'danger')
        return redirect(url_for('index'))
    contact.bookmarked = not contact.bookmarked
    db.session.commit()
    flash('已更新收藏状态', 'success')
    return redirect(url_for('index'))


# Import / Export
@app.route('/export_contacts')
@login_required
def export_contacts():
    # Build a list of dicts for pandas
    contacts = Contact.query.filter_by(user_id=current_user.id).all()
    rows = []
    for c in contacts:
        phones = [m.value for m in c.methods if m.type == 'phone']
        emails = [m.value for m in c.methods if m.type == 'email']
        socials = [m.value for m in c.methods if m.type == 'social']
        adds = [m.value for m in c.methods if m.type == 'address']
        row = {
            'Name': c.name,
            'Phones': ';'.join(phones),
            'Emails': ';'.join(emails),
            'Socials': ';'.join(socials),
            'Addresses': ';'.join(adds),
            'Bookmarked': int(bool(c.bookmarked))
        }
        rows.append(row)
    df = pd.DataFrame(rows, columns=['Name', 'Phones', 'Emails', 'Socials', 'Addresses', 'Bookmarked'])
    # write to in-memory buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='contacts')
    output.seek(0)

    # 修复了 download_name 参数
    return send_file(output, download_name='contacts_export.xlsx', as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/import_contacts', methods=['POST'])
@login_required
def import_contacts():
    # Accept Excel file upload
    if 'file' not in request.files:
        flash('未上传文件', 'danger')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('未选择文件', 'danger')
        return redirect(url_for('index'))
    if not allowed_file(file.filename, allowed={'xlsx', 'xls'}):
        flash('请上传 Excel 文件 (.xlsx/.xls)', 'danger')
        return redirect(url_for('index'))

    try:
        df = pd.read_excel(file)
    except Exception as e:
        flash(f'读取 Excel 失败: {e}', 'danger')
        return redirect(url_for('index'))

    required_cols = {'Name'}
    if not required_cols.issubset(set(df.columns)):
        flash('Excel 必须包含至少 Name 列', 'danger')
        return redirect(url_for('index'))

    count = 0
    for _, row in df.iterrows():
        name = str(row.get('Name', '')).strip()
        if not name:
            continue
        c = Contact(name=name, user_id=current_user.id)
        db.session.add(c)
        db.session.flush()

        # parse semicolon-separated fields
        def parse_col(col):
            val = row.get(col, '')
            if pd.isna(val):
                return []
            if isinstance(val, (int, float)):
                val = str(val)
            return [s.strip() for s in str(val).split(';') if s.strip()]

        for phone in parse_col('Phones'):
            db.session.add(ContactMethod(contact_id=c.id, type='phone', value=phone))
        for email in parse_col('Emails'):
            db.session.add(ContactMethod(contact_id=c.id, type='email', value=email))
        for social in parse_col('Socials'):
            db.session.add(ContactMethod(contact_id=c.id, type='social', value=social))
        for addr in parse_col('Addresses'):
            db.session.add(ContactMethod(contact_id=c.id, type='address', value=addr))
        # bookmarked optional
        if 'Bookmarked' in df.columns and int(row.get('Bookmarked', 0)):
            c.bookmarked = True
        count += 1

    db.session.commit()
    flash(f'导入成功：{count} 条联系人', 'success')
    return redirect(url_for('index'))


# Avatar upload
@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('未选择文件', 'danger')
        return redirect(url_for('index'))
    file = request.files['avatar']
    if file.filename == '':
        flash('未选择文件', 'danger')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename, allowed={'png', 'jpg', 'jpeg', 'gif'}):
        filename = secure_filename(file.filename)
        filename = f"user_{current_user.id}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        if current_user.avatar and current_user.avatar != 'default.png':
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                pass
        current_user.avatar = filename
        db.session.commit()
        flash('头像上传成功！', 'success')
    else:
        flash('文件类型不支持，请上传图片', 'danger')
    return redirect(url_for('index'))


# Auth routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=form.email.data).first():
            flash('邮箱已被注册', 'danger')
            return redirect(url_for('register'))
        user = User(username=form.username.data, email=form.email.data)
        user.password_hash = generate_password_hash(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('邮箱或密码错误', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Initialize DB
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)