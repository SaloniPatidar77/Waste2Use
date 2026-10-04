from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session,send_from_directory, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
from datetime import datetime ,timedelta
from collections import defaultdict
from difflib import get_close_matches
from flask import jsonify
import pytesseract
from PIL import Image
from ml_model import WasteIdeaModel
from difflib import get_close_matches
from flask import render_template, request
from ml_predictive_model import PredictiveAnalysis
import numpy as np
from sklearn.linear_model import LinearRegression
from flask import jsonify, request
from flask_login import login_required, current_user
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
import sqlite3, io, base64
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet 
from flask import make_response, render_template
from urllib.parse import unquote
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is not set")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production"

)

def add_notification(user_id, message):
    notif = Notification(user_id=user_id, message=message)
    db.session.add(notif)
    db.session.commit()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, "static/uploads")
app.config['PROFILE_PIC_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')

os.makedirs(app.config['PROFILE_PIC_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
UPLOAD_FOLDER = os.path.join('static', 'uploads')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['WASTE_IMAGE'] = os.path.join(BASE_DIR, "static/image")
os.makedirs(app.config['WASTE_IMAGE'], exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Search(db.Model):
    __tablename__ = "searches"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    query = db.Column(db.String(200), nullable=False)
    search_date = db.Column(db.DateTime, default=datetime.utcnow)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    points = db.Column(db.Integer, default=0)
    bio = db.Column(db.Text, default="")
    profile_pic = db.Column(db.String(150), default="default.png")
    role = db.Column(db.String(20), default="user")  # keep only this
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True)
    media = db.Column(db.String(200))  # image/video path
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    waste_type = db.Column(db.String(50))   # e.g. Plastic, Metal, Organic
    waste_amount = db.Column(db.Float)      # e.g. 2.5 (kg)
    likes = db.relationship('Like', backref='post', lazy=True)
    comments = db.relationship('Comment', backref='post', lazy=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    shares = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship(
    'User',
    backref=db.backref(
        'user_comments',
        overlaps="comments,author"
    ),
    overlaps="comments,author"
)
     
class CommunityMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    if not session.get('user_id'):
        return redirect('/login')

    posts = Post.query.options(
        db.joinedload(Post.likes),
        db.joinedload(Post.comments)
    ).order_by(Post.timestamp.desc()).all()

    return render_template("home.html", posts=posts)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        bio = request.form.get('bio')
        photo = request.files.get('photo')

        user = User.query.filter_by(username=username).first()
        if user:
            return render_template('signup.html', error="Username already exists")

        profile_pic = "default.png"
        if photo and photo.filename != "":
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            profile_pic = filename

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            bio=bio,
            profile_pic=profile_pic
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            session['user_id'] = user.id
            session['username'] = user.username

            return redirect(url_for('home'))

        return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile/<username>')
def profile(username):

    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = User.query.filter_by(username=username).first()

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for('home'))

    profile_pic_url = url_for(
        'static',
        filename=f'profile_pics/{user.profile_pic}'
        if user.profile_pic else 'profile_pics/default.png'
    )

    eco_score = 82
    rank = "Eco Guardian"
    achievements = ["Saved 15kg waste", "Planted 3 trees 🌱", "Top 10 Contributor"]

    return render_template(
        'profile.html',
        user=user,
        profile_pic=profile_pic_url,
        eco_score=eco_score,
        rank=rank,
        achievements=achievements
    )

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():

    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    if request.method == 'POST':

        bio = request.form.get('bio')
        file = request.files.get('profile_pic')

        if bio:
            user.bio = bio

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.root_path, 'static/profile_pics', filename)
            file.save(filepath)
            user.profile_pic = filename

        db.session.commit()

        return redirect(url_for('profile', username=user.username))

    return render_template('edit_profile.html', user=user)

@app.route("/post", methods=["GET", "POST"])
def post():

    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get("title")
        content = request.form.get("body")

        image_file = request.files.get("image")
        video_file = request.files.get("video")

        filename = None

        # IMAGE UPLOAD
        if image_file and image_file.filename != "":

            if not allowed_image(image_file.filename):
                flash("❌ Invalid image file type.", "danger")
                return redirect(url_for("post"))

            filename = secure_filename(image_file.filename)

            image_file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        # VIDEO UPLOAD
        if video_file and video_file.filename != "":

            if not allowed_video(video_file.filename):
                flash("❌ Invalid video file type.", "danger")
                return redirect(url_for("post"))

            filename = secure_filename(video_file.filename)

            video_file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        waste_type = request.form.get("waste_type")
        waste_amount = request.form.get("waste_amount", 0)

        new_post = Post(
            title=title,
            content=content,
            media=filename,
            user_id=session["user_id"],
            waste_type=waste_type,
            waste_amount=float(waste_amount)
        )

        db.session.add(new_post)
        db.session.commit()

        # Notify other users
        other_users = User.query.filter(
            User.id != session["user_id"]
        ).all()

        for user in other_users:
            add_notification(
                user.id,
                f"📢 {session['username']} added a new waste reuse post! ♻️"
            )

        flash("Post uploaded successfully!", "success")
        return redirect(url_for("home"))

    return render_template("post.html")
@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form['content']
    new_post = Post(user_id=current_user.id, content=content)
    db.session.add(new_post)
    db.session.commit()

    other_users = User.query.filter(User.id != current_user.id).all()

    for user in other_users:
        add_notification(
            user.id,
            f"📢 {current_user.username} added a new waste reuse post! ♻️"
        )

    flash("Post created successfully!")
    return redirect(url_for('index'))

@app.route('/delete_message/<int:msg_id>', methods=['POST'])
def delete_message(msg_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    msg = CommunityMessage.query.get_or_404(msg_id)

    if msg.user_id != session['user_id']:
        flash("You cannot delete this message!", "danger")
        return redirect(url_for('community'))

    if msg.image:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], msg.image)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(msg)
    db.session.commit()

    flash("Message deleted successfully!", "success")
    return redirect(url_for('community'))

@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):

    if not session.get("user_id"):
        return jsonify({"error": "login required"}), 401

    post = Post.query.get_or_404(post_id)

    existing_like = Like.query.filter_by(
        user_id=session["user_id"],
        post_id=post_id
    ).first()

    if existing_like:
        # Unlike
        db.session.delete(existing_like)

    else:
        # New like
        new_like = Like(
            user_id=session["user_id"],
            post_id=post_id
        )
        db.session.add(new_like)

        # Notify post owner
        if post.user_id != session["user_id"]:
            add_notification(
                post.user_id,
                f"❤️ {session['username']} liked your post!"
            )

    db.session.commit()

    total_likes = Like.query.filter_by(
        post_id=post_id
    ).count()

    return jsonify({"likes": total_likes})

@app.route("/comment/<int:post_id>", methods=["POST"])
def comment_post(post_id):

    if not session.get("user_id"):
        return redirect(url_for("login"))

    content = request.form.get("content")

    if not content:
        return jsonify({
            "status": "error",
            "message": "Empty comment"
        }), 400

    post = Post.query.get_or_404(post_id)

    comment = Comment(
        content=content,
        user_id=session["user_id"],
        post_id=post_id
    )

    db.session.add(comment)
    db.session.commit()

    # Notify post owner
    if post.user_id != session["user_id"]:
        add_notification(
            post.user_id,
            f"💬 {session['username']} commented on your post!"
        )

    return jsonify({"status": "ok"})

@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):

    comment = Comment.query.get_or_404(comment_id)

    if session.get("user_id") != comment.user_id:
        return jsonify({"status":"error"}),403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"status":"ok"})
@app.route("/share/<int:post_id>", methods=["POST"])
def share_post(post_id):

    if not session.get("user_id"):
        return jsonify({"error": "login required"}), 401

    post = Post.query.get_or_404(post_id)

    post.shares = (post.shares or 0) + 1

    # Notify post owner
    if post.user_id != session["user_id"]:
        add_notification(
            post.user_id,
            f"🔄 {session['username']} shared your post!"
        )

    db.session.commit()

    return jsonify({"shares": post.shares})
@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):

    if not session.get("user_id"):
        return jsonify({"status": "error"}), 401

    post = Post.query.get_or_404(post_id)

    # Only post owner can delete
    if post.user_id != session["user_id"]:
        return jsonify({"status": "error"}), 403

    # Get users who interacted with this post
    user_ids = set()

    for like in post.likes:
        if like.user_id != session["user_id"]:
            user_ids.add(like.user_id)

    for comment in post.comments:
        if comment.user_id != session["user_id"]:
            user_ids.add(comment.user_id)

    # Delete the post
    db.session.delete(post)
    db.session.commit()

    # Notify users who interacted with the deleted post
    for user_id in user_ids:
        add_notification(
            user_id,
            f"🗑️ {session['username']} deleted a post you interacted with."
        )

    return jsonify({"status": "ok"})

@app.route('/leaderboard')
def leaderboard():
    users = User.query.all()
    ranked_users = []

    for user in users:
        post_count = Post.query.filter_by(user_id=user.id).count()
        if post_count > 0:  # hide users with 0 posts
            ranked_users.append({
                'username': user.username,
                'posts_count': post_count,
                'points': user.points if hasattr(user, 'points') else 0
            })

    ranked_users.sort(key=lambda x: (x['points'], x['posts_count']), reverse=True)

    return render_template('leaderboard.html', users=ranked_users)

@app.route("/stats/<username>")
@login_required
def stats(username):
    user = User.query.filter_by(username=username).first_or_404()

    total_posts = len(user.posts)
    total_waste_saved = total_posts * 0.5  # each post = 0.5kg saved
    tree_equivalent = round(total_waste_saved / 20, 2)

    data = {
        "total_waste_saved": total_waste_saved,
        "total_posts": total_posts,
        "tree_equivalent": tree_equivalent
    }

    return render_template("stats.html", data=data)

@app.route("/admin/stats")
@login_required
def admin_stats():
    if current_user.role != "admin":
        flash("Access denied — Admins only!", "danger")
        return redirect(url_for("index"))
    conn = db.engine.raw_connection()
    
    posts_df = pd.read_sql_query("""
        SELECT DATE(date_posted) AS ds, COUNT(*) AS y 
        FROM post 
        GROUP BY ds ORDER BY ds
    """, conn)

    searches_df = pd.read_sql_query("""
        SELECT DATE(search_date) AS ds, COUNT(*) AS y 
        FROM searches 
        GROUP BY ds ORDER BY ds
    """, conn)
    posts_df["type"] = "Posts"
    searches_df["type"] = "Searches"
    combined_df = pd.concat([posts_df, searches_df])
 
    future_pred = None
    if len(posts_df) >= 2:
        model = Prophet()
        model.fit(posts_df)
        future = model.make_future_dataframe(periods=7)
        forecast = model.predict(future)
        future_pred = forecast[["ds", "yhat"]].tail(7).to_dict(orient="records")

    conn.close()
    return render_template(
    "admin/analytics.html",
    data=combined_df.to_dict(orient="records"),
    future_pred=future_pred
)

@app.route("/admin/delete-post/<int:post_id>", methods=["POST"])
@login_required
def admin_delete_post(post_id):
    if current_user.role != "admin":
        return jsonify({"status": "error"}), 403

    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"status": "ok"})

WASTE_DB = {
    "plastic bottle": {
        "text": "You can make a plant pot or a bird feeder from a plastic bottle.",
        "images": ["bottle1.jpg", "bottle2.jpg"]
    },
    "tyre": {
        "text": "Old tyres can be converted into swings or garden planters.",
        "images": ["tyre1.jpg", "tyre2.jpg"]
    },
    "paper": {
        "text": "Reuse paper to make notebooks, art, or origami.",
        "images": ["paper1.jpg", "paper2.jpg"]
    },
    "glass bottle": {
        "text": "Glass bottles can be turned into vases or decorative lamps.",
        "images": ["glass1.jpg", "glass2.jpg"]
    },
    "aluminium can": {
        "text": "Use aluminium cans to create pen holders or planters.",
        "images": ["can1.jpg", "can2.jpg"]
    },
    "plastic bag": {
        "text": "Weave plastic bags into reusable mats or baskets.",
        "images": ["bag1.jpg", "bag2.jpg"]
    },
    "cardboard": {
        "text": "Cardboard can be reused for storage boxes or crafts.",
        "images": ["cardboard1.jpg", "cardboard2.jpg"]
    },
    "electronic waste": {
        "text": "Old electronics can be recycled or used for DIY projects.",
        "images": ["ewaste1.jpg", "ewaste2.jpg"]
    },
    "food waste": {
        "text": "Food waste can be composted to make organic fertilizer.",
        "images": ["food1.jpg", "food2.jpg"]
    },
    "coconut shell": {
        "text": "Coconut shells can be used to make bowls or plant holders.",
        "images": ["coconut1.jpg", "coconut2.jpg"]
    },
    "cloth scraps": {
        "text": "Old cloth can be used for patchwork, cleaning, or crafts.",
        "images": ["cloth1.jpg", "cloth2.jpg"]
    },
    "tin": {
        "text": "Old tins can become candle holders or storage containers.",
        "images": ["tin1.jpg", "tin2.jpg"]
    },
    "rubber": {
        "text": "Old rubber items can be used for mats or DIY crafts.",
        "images": ["rubber1.jpg", "rubber2.jpg"]
    },
    "wood scraps": {
        "text": "Wood scraps can be used for small furniture or art pieces.",
        "images": ["wood1.jpg", "wood2.jpg"]
    },
    "metal scraps": {
        "text": "Metal scraps can be recycled or used in DIY tools.",
        "images": ["metal1.jpg", "metal2.jpg"]
    },
}

@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = []
    materials = []

    if query:
        new_search = Search(
            user_id=current_user.id if current_user.is_authenticated else None,
            query=query,
            search_date=datetime.utcnow()
        )

        db.session.add(new_search)
        db.session.commit()

        # Detect one or multiple waste materials
        materials = model.detect_materials(query)

        # Smart multi-material search
        results = model.search_multiple_materials(query)

    return render_template(
        'search.html',
        results=results,
        query=query,
        materials=materials
    )
@app.route('/post/<int:post_id>')
def post_detail(post_id):

    post = Post.query.get_or_404(post_id)

    return render_template(
        'post_detail.html',
        post=post
    )

@app.route('/idea/<int:idea_id>')
def idea_details(idea_id):

    idea = model.df[model.df["id"] == idea_id]

    if idea.empty:
        return "Idea not found", 404

    idea = idea.iloc[0].to_dict()

    return render_template(
        'idea_details.html',
        idea=idea
    )

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "webm"}


def allowed_image(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS
    )


def allowed_video(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in VIDEO_EXTENSIONS
    )

@app.route("/community", methods=["GET", "POST"])
def community():

    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":

        message_text = request.form.get("message", "").strip()
        media_file = request.files.get("image")

        if not message_text and (
            not media_file or media_file.filename == ""
        ):
            flash("⚠️ Message cannot be empty", "warning")
            return redirect(url_for("community"))

        media_path = None

        media_path = None

        if media_file:
            extension = media_file.filename.rsplit('.', 1)[1].lower() if '.' in media_file.filename else ''

            if extension not in IMAGE_EXTENSIONS and extension not in VIDEO_EXTENSIONS:
               flash("❌ Invalid file type.", "danger")
            return redirect(url_for("community"))

        filename = secure_filename(media_file.filename)
        media_path = filename

        media_file.save(
        os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )
    )

        msg = CommunityMessage(
            user_id=session["user_id"],
            username=session["username"],
            message=message_text,
            image=media_path
        )

        db.session.add(msg)
        db.session.commit()

        flash("✅ Message sent successfully!", "success")
        return redirect(url_for("community"))

    messages = CommunityMessage.query.order_by(
        CommunityMessage.timestamp.asc()
    ).all()

    for msg in messages:
        if msg.timestamp:
            msg.local_timestamp = (
                msg.timestamp + timedelta(hours=5, minutes=30)
            )

    return render_template(
        "community.html",
        messages=messages
    )




@app.route("/admin")
@login_required
def admin():

    if current_user.role != "admin":
        flash("Access denied")
        return redirect(url_for("home"))

    users = User.query.all()
    posts = Post.query.order_by(Post.date_posted.desc()).all()

    total_users = User.query.count()
    total_posts = Post.query.count()

    return render_template(
    "admin/dashboard.html",
    users=users,
    posts=posts,
    total_users=total_users,
    total_posts=total_posts
)

@app.route("/admin/users")
@login_required
def admin_users():
    if current_user.role != "admin":
        return "Access denied", 403

    users = User.query.order_by(User.id.desc()).all()
    return render_template("admin/users.html", users=users)

@app.route("/admin/posts")
@login_required
def admin_posts():
    if current_user.role != "admin":
        return "Access denied", 403

    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template("admin/posts.html", posts=posts)

@app.route("/admin/delete-user/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        return "Access denied", 403

    user = User.query.get_or_404(user_id)

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for("admin_users"))

@app.route("/admin/delete-post/<int:post_id>")
@login_required
def admin_delete_post_panel(post_id):
    if current_user.role != "admin":
        return "Access denied", 403

    post = Post.query.get_or_404(post_id)

    db.session.delete(post)
    db.session.commit()

    return redirect(url_for("admin_posts"))

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
    return dict(logged_user=user)

@app.route('/notification')
@login_required
def notifications():

    user_notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.timestamp.desc()).all()

    for n in user_notifications:
        if n.timestamp:
            n.local_timestamp = n.timestamp + timedelta(hours=5, minutes=30)

    return render_template(
        'notification.html',
        notifications=user_notifications
    )

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    receiver_id = request.form['receiver_id']
    message = request.form['message']
  
    add_notification(receiver_id, f"New message from {current_user.username}")
    return redirect(url_for('chat', user_id=receiver_id))

@app.context_processor
def inject_notification_model():
    return dict(Notification=Notification)

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js')

model = WasteIdeaModel()

@app.route("/feed")
def feed():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template("community_feed.html", posts=posts)



with app.app_context():
    db.create_all()


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)