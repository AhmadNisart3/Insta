from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
print("hello")
# App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1340841002453968837b6053f9dc3fdc7fd3b7d86b87dca'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://asadmehmood10:Admin123@com769project.database.windows.net/ScalableProject1?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Azure Blob Storage Config
AZURE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=asadmehmood;AccountKey=kFYwacIC/6zs+oaZ0M/v7kP/tAfAoDpwK0pQjUsv1158l5KBmPjE5aqb9p5BcZdLtUKpT3Z+IqQn+AStkLCIVw==;EndpointSuffix=core.windows.net"
AZURE_CONTAINER_NAME = "videos"

# Initialize DB & Azure Blob
db = SQLAlchemy(app)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
try:
    blob_service_client.create_container(AZURE_CONTAINER_NAME)
except Exception:
    pass

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(512), nullable=False)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    people_present = db.Column(db.String(256), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='media')
    ratings = db.relationship('Rating', backref='media')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'media_id', name='unique_user_media_rating'),)

with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template_string('''
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            a { color: #007BFF; text-decoration: none; margin: 0 10px; }
            a:hover { text-decoration: underline; }
        </style>
        <h1>Welcome to the Video Distribution Website</h1>
        <a href="{{ url_for('login') }}">Login</a> |
        <a href="{{ url_for('register') }}">Register</a>
    ''')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, role=role, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created!', 'success')
        return redirect(url_for('login'))
    return render_template_string('''
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            form { margin-top: 20px; }
            input, select, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; }
            button { background-color: #007BFF; color: white; border: none; cursor: pointer; }
            button:hover { background-color: #0056b3; }
        </style>
        <h1>Register</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required><br>
            <input type="email" name="email" placeholder="Email" required><br>
            <input type="password" name="password" placeholder="Password" required><br>
            <select name="role" required>
                <option value="creator">Creator</option>
                <option value="consumer">Consumer</option>
            </select><br>
            <button type="submit">Register</button>
        </form>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed.', 'danger')
    return render_template_string('''
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            form { margin-top: 20px; }
            input, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; }
            button { background-color: #007BFF; color: white; border: none; cursor: pointer; }
            button:hover { background-color: #0056b3; }
        </style>
        <h1>Login</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required><br>
            <input type="password" name="password" placeholder="Password" required><br>
            <button type="submit">Login</button>
        </form>
    ''')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['role'] == 'creator':
        return render_template_string('''
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                form { margin-top: 20px; }
                input, select, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; }
                button { background-color: #007BFF; color: white; border: none; cursor: pointer; }
                button:hover { background-color: #0056b3; }
            </style>
            <h1>Creator Dashboard</h1>
            <form method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data">
                <input type="text" name="title" placeholder="Title" required><br>
                <input type="text" name="caption" placeholder="Caption"><br>
                <input type="text" name="location" placeholder="Location"><br>
                <input type="text" name="people_present" placeholder="People Present"><br>
                <input type="file" name="file" required><br>
                <select name="media_type" required>
                    <option value="video">Video</option>
                    <option value="picture">Picture</option>
                </select><br>
                <button type="submit">Upload Media</button>
            </form>
            <a href="{{ url_for('logout') }}">Logout</a>
        ''')
    else:
        media = Media.query.options(
            joinedload(Media.comments),
            joinedload(Media.ratings)
        ).all()
        return render_template_string('''
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1, h2, h4 { color: #333; }
                video, img { max-width: 100%; height: auto; }
                form { margin-top: 20px; }
                input, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; }
                button { background-color: #007BFF; color: white; border: none; cursor: pointer; }
                button:hover { background-color: #0056b3; }
                ul { list-style-type: none; padding: 0; }
                li { margin-bottom: 10px; }
            </style>
            <h1>Consumer Dashboard</h1>
            {% for item in media %}
                <h2>{{ item.title | e }}</h2>
                <p>{{ item.caption | e }}</p>
                {% if item.media_type == 'video' %}
                    <video width="500" controls>
                        <source src="{{ item.file_path | e }}" type="video/mp4">
                        Your browser does not support video playback.
                    </video>
                {% else %}
                    <img src="{{ item.file_path | e }}" alt="Picture" width="500">
                {% endif %}
                <h4>Comments:</h4>
                <ul>
                    {% for comment in item.comments %}
                        <li>{{ comment.text | e }}</li>
                    {% endfor %}
                    {% if not item.comments %}
                        <li>No comments yet.</li>
                    {% endif %}
                </ul>
                <form method="POST" action="{{ url_for('comment') }}">
                    <input type="hidden" name="media_id" value="{{ item.id }}">
                    <input type="text" name="text" placeholder="Comment" required>
                    <button type="submit">Comment</button>
                </form>
                <h4>Ratings:</h4>
                <ul>
                    {% for rating in item.ratings %}
                        <li>{{ rating.value | e }}/5</li>
                    {% endfor %}
                    {% if not item.ratings %}
                        <li>No ratings yet.</li>
                    {% endif %}
                </ul>
                <form method="POST" action="{{ url_for('rate') }}">
                    <input type="hidden" name="media_id" value="{{ item.id }}">
                    <input type="number" name="value" min="1" max="5" required>
                    <button type="submit">Rate</button>
                </form>
                <hr>
            {% endfor %}
            <a href="{{ url_for('logout') }}">Logout</a>
        ''', media=media)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session or session['role'] != 'creator':
        return redirect(url_for('login'))
    title = request.form['title']
    caption = request.form['caption']
    location = request.form['location']
    people_present = request.form['people_present']
    file = request.files['file']
    media_type = request.form['media_type']
    if file:
        filename = file.filename
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=filename)
        blob_client.upload_blob(file, overwrite=True, content_settings=ContentSettings(
            content_type='video/mp4' if media_type == 'video' else 'image/jpeg'))
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"
        media = Media(
            title=title,
            caption=caption,
            location=location,
            people_present=people_present,
            file_path=blob_url,
            media_type=media_type if media_type in ['video', 'picture'] else 'picture',
            creator_id=session['user_id']
        )
        db.session.add(media)
        db.session.commit()
        flash('Media uploaded successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comment = Comment(
        text=request.form['text'],
        user_id=session['user_id'],
        media_id=request.form['media_id']
    )
    db.session.add(comment)
    db.session.commit()
    flash('Comment added!', 'success')
    return redirect(url_for('dashboard'))




@app.route('/rate', methods=['POST'])
def rate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    media_id = request.form.get('media_id')
    if not media_id:
        flash('Media ID is required to rate!', 'danger')
        return redirect(url_for('dashboard'))
    try:
        media_id = int(media_id)
    except ValueError:
        flash('Invalid Media ID!', 'danger')
        return redirect(url_for('dashboard'))
    media = Media.query.get(media_id)
    if not media:
        flash('Invalid media item!', 'danger')
        return redirect(url_for('dashboard'))
    existing_rating = Rating.query.filter_by(user_id=session['user_id'], media_id=media_id).first()
    if existing_rating:
        flash('You have already rated this media!', 'warning')
        return redirect(url_for('dashboard'))
    rating = Rating(
        value=int(request.form['value']),
        user_id=session['user_id'],
        media_id=media_id
    )
    db.session.add(rating)
    try:
        db.session.commit()
        flash('Media rated!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Failed to rate media. Please check your input and try again.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
