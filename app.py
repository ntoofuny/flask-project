from flask import (Flask, g, render_template, flash, redirect, url_for, session, request)
from flask_login import (LoginManager, login_user, logout_user, login_required, current_user)
from flask_bcrypt import check_password_hash
from flask_socketio import emit, join_room, leave_room, SocketIO
from werkzeug.utils import secure_filename
import os
import models
import forms
from PIL import Image
#import flask_resize

DEBUG = True
PORT = 8000
HOST = '0.0.0.0'

app = Flask(__name__)
app.secret_key = 'hjgsjglsjgesgwesgs'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

socketio = SocketIO(app)

UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024



@login_manager.user_loader
def load_user(userid):
    try:
        return models.User.get(models.User.id == userid)
    except models.DoesNotExist:
        return None


@app.before_request
def before_request():
    g.db = models.DATABASE
    g.db.connect()


@app.after_request
def after_request(response):
    g.db.close()
    return response


@app.route('/register', methods=('GET', 'POST'))
def register():
    form = forms.RegisterForm()
    if form.validate_on_submit():
        flash("Yay, you registered!", "success")
        models.User.create_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/login', methods=('GET', 'POST'))
def login():
    form = forms.LoginForm()
    if form.validate_on_submit():
        try:
            user = models.User.get(models.User.email == form.email.data)
        except models.DoesNotExist:
            flash("Your email or password doesn't match!", "error")
        else:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                flash("You've been logged in!", "success")
                return redirect(url_for('index'))
            else:
                flash("Your email or password doesn't match!", "error")
    return render_template('login.html', form=form)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = forms.SearchForm()
    users = models.User.select();
    return render_template("search.html", form = form, users = users)

@app.route('/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    user = models.User.get(models.User.username == username)
    form = forms.ChatForm()

    if form.validate_on_submit():
        session['name'] = current_user.username
        session['room'] = user.username + "'s chatroom"
        return redirect(url_for('.chat'))
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        filename = user.username+".jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        im = Image.open(filepath)
        size = (150, 100)
        out = im.resize(size)
        out.save(filepath)

    return render_template('user.html', user=user, form =form)

@app.route('/chat')
@login_required
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    name = session.get('name', '')
    room = session.get('room', '')
    if name == '' or room == '':
        return redirect(url_for('index'))
    return render_template('chat.html', name=name, room=room)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You've been logged out", "success")
    return redirect(url_for('index'))


@app.route('/')
def index():
    return render_template("index.html")

@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    join_room(room)
    emit('status', {'msg': session.get('name') + ' has entered the room.'}, room=room)


@socketio.on('text', namespace='/chat')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = session.get('room')
    emit('message', {'msg': session.get('name') + ':' + message['msg']}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    leave_room(room)
    emit('status', {'msg': session.get('name') + ' has left the room.'}, room=room)

if __name__ == '__main__':
    models.initialize()
    try:
        models.User.create_user(
            username='amadeusz',
            email='amadeusz@gmail.com',
            password='password',
            admin=False)
    except ValueError:
        print("didn't work")
        pass

    socketio.run(app,debug= True)