from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    documents = db.relationship('Document', backref='user', lazy=True)
    answers = db.relationship('UserAnswer', backref='user', lazy=True)

    def set_password(self, password):
        """Şifreyi hash'leyerek kaydeder (asla düz metin saklanmaz)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verilen şifre doğru mu kontrol eder."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    extracted_text = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    topics = db.relationship('Topic', backref='document', lazy=True)

    def __repr__(self):
        return f'<Document {self.filename}>'


class Topic(db.Model):
    __tablename__ = 'topics'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    topic_name = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text)

    subtopics = db.Column(db.Text)
    prerequisites = db.Column(db.Text)
    common_mistakes = db.Column(db.Text)
    difficulty_level = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('Question', backref='topic', lazy=True)

    def __repr__(self):
        return f'<Topic {self.topic_name}>'


class Question(db.Model):
    """Üretilen sınav sorusu."""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    
    # Soru içeriği
    question_text = db.Column(db.Text, nullable=False)
    solution_steps = db.Column(db.Text)
    correct_answer = db.Column(db.Text)
    
    # Soru metadata
    difficulty = db.Column(db.String(20))  # kolay, orta, zor
    question_type = db.Column(db.String(50))  # hesaplama, ispat, vs.
    measured_concept = db.Column(db.Text)
    options = db.Column(db.Text)  # JSON string
    hint = db.Column(db.Text)
    
    # Kaynak bilgisi (PDF'ten)
    source_page = db.Column(db.Integer)
    source_image_path = db.Column(db.Text)
    source_description = db.Column(db.Text)
    
    # ═══ Grafik alanları ═══
    has_graph = db.Column(db.Boolean, default=False)
    graph_svg = db.Column(db.Text)
    graph_data = db.Column(db.Text)  # JSON string — Matplotlib için
    graph_description = db.Column(db.Text)
    
    # ═══ AI Doğrulama ═══
    is_verified = db.Column(db.Boolean, default=False)
    verification_method = db.Column(db.String(50))  # 'sympy', 'ai', 'both'
    verification_confidence = db.Column(db.String(20))  # 'yuksek', 'orta', 'dusuk'
    verification_message = db.Column(db.Text)
    verification_errors = db.Column(db.Text)  # JSON string
    
    # ═══ Bloom Taksonomisi ═══
    bloom_level = db.Column(db.String(30))  # 'hatirlama', 'anlama', vs.

    
    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:50]}...>'


class UserAnswer(db.Model):
    __tablename__ = 'user_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    time_spent = db.Column(db.Integer)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserAnswer user={self.user_id} q={self.question_id}>'


class ProcessingJob(db.Model):
    """Bir dosya işleme görevinin durumunu takip eder."""
    __tablename__ = 'processing_jobs'

    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)

    status = db.Column(db.String(30), default='pending')

    current_step = db.Column(db.String(100))
    progress = db.Column(db.Integer, default=0)

    detected_topic = db.Column(db.String(300))
    detected_subtopics = db.Column(db.Text)
    detected_level = db.Column(db.String(50))
    content_type = db.Column(db.String(50))

    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    error_message = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Feedback(db.Model):
    """Soru geri bildirimleri — kullanıcılar soruları değerlendirir."""
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)

    rating = db.Column(db.String(20), nullable=False)

    reason = db.Column(db.String(50))
    comment = db.Column(db.Text)

    topic_category = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref='feedbacks')
    question = db.relationship('Question', backref='feedbacks')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id', name='unique_user_question_feedback'),
    )

    def __repr__(self):
        return f'<Feedback {self.id}: {self.rating}>'


class Favorite(db.Model):
    """Kullanıcı favori soruları."""
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    note = db.Column(db.Text)

    user = db.relationship('User', backref='favorites')
    question = db.relationship('Question', backref='favorited_by')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id', name='unique_user_question_favorite'),
    )

    def __repr__(self):
        return f'<Favorite {self.id}: user={self.user_id} q={self.question_id}>'

class FlashcardReview(db.Model):
    """Kullanıcının flashcard çalışma performansı."""
    __tablename__ = 'flashcard_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    
    # Aralıklı tekrar (SM-2 algoritması)
    interval = db.Column(db.Integer, default=1)      # Sonraki gösterilme aralığı (gün)
    ease_factor = db.Column(db.Float, default=2.5)   # Zorluk çarpanı
    repetitions = db.Column(db.Integer, default=0)   # Kaç kez tekrar edildi
    
    # Tarihler
    next_review = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_reviewed = db.Column(db.DateTime)
    
    # Performans
    total_correct = db.Column(db.Integer, default=0)
    total_wrong = db.Column(db.Integer, default=0)
    last_rating = db.Column(db.String(20))  # 'easy', 'good', 'hard', 'again'
    
    # İlişkiler
    user = db.relationship('User', backref='flashcard_reviews')
    question = db.relationship('Question', backref='flashcard_reviews')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id', name='unique_user_question_review'),
    )
    
    def __repr__(self):
        return f'<FlashcardReview {self.id}: user={self.user_id} q={self.question_id}>'