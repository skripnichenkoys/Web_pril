import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea

app = Flask(__name__)
app.config['SECRET_KEY'] = 'knowledge-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///knowledge_base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

article_category = db.Table('article_category',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author = db.Column(db.String(100), nullable=False)
    categories = db.relationship('Category', secondary=article_category, backref=db.backref('articles', lazy='dynamic'))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))

class ArticleForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired()])
    content = TextAreaField('Содержание', validators=[DataRequired()], widget=TextArea())
    author = StringField('Автор', validators=[DataRequired()])
    categories = StringField('Категории (через запятую)', validators=[DataRequired()])

class CategoryEditForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = StringField('Описание')

def process_categories(categories_str):
    names = [name.strip() for name in categories_str.split(',') if name.strip()]
    categories = []
    for name in names:
        cat = Category.query.filter_by(name=name).first()
        if not cat:
            cat = Category(name=name)
            db.session.add(cat)
            db.session.flush()
        categories.append(cat)
    return categories

@app.route('/')
def index():
    articles = Article.query.order_by(Article.updated_at.desc()).all()
    return render_template('kb_index.html', articles=articles)

@app.route('/article/<int:id>')
def view_article(id):
    article = Article.query.get_or_404(id)
    return render_template('kb_view_article.html', article=article)

@app.route('/article/add', methods=['GET', 'POST'])
def add_article():
    form = ArticleForm()
    if form.validate_on_submit():
        article = Article(
            title=form.title.data,
            content=form.content.data,
            author=form.author.data
        )
        db.session.add(article)
        db.session.flush()
        article.categories = process_categories(form.categories.data)
        db.session.commit()
        flash('Статья добавлена', 'success')
        return redirect(url_for('index'))
    return render_template('kb_article_form.html', form=form, title='Добавить статью')

@app.route('/article/<int:id>/edit', methods=['GET', 'POST'])
def edit_article(id):
    article = Article.query.get_or_404(id)
    form = ArticleForm(obj=article)
    if request.method == 'GET':
        form.categories.data = ', '.join([c.name for c in article.categories])
    if form.validate_on_submit():
        article.title = form.title.data
        article.content = form.content.data
        article.author = form.author.data
        article.updated_at = datetime.utcnow()
        article.categories = process_categories(form.categories.data)
        db.session.commit()
        flash('Статья обновлена', 'success')
        return redirect(url_for('index'))
    return render_template('kb_article_form.html', form=form, title='Редактировать статью')

@app.route('/article/<int:id>/delete', methods=['POST'])
def delete_article(id):
    article = Article.query.get_or_404(id)
    db.session.delete(article)
    db.session.commit()
    flash('Статья удалена', 'success')
    return redirect(url_for('index'))

@app.route('/categories')
def categories_list():
    cats = Category.query.all()
    return render_template('kb_categories.html', categories=cats)

@app.route('/category/<int:id>/edit', methods=['GET', 'POST'])
def edit_category(id):
    cat = Category.query.get_or_404(id)
    form = CategoryEditForm(obj=cat)
    if form.validate_on_submit():
        cat.name = form.name.data
        cat.description = form.description.data
        db.session.commit()
        flash('Категория обновлена', 'success')
        return redirect(url_for('categories_list'))
    return render_template('kb_category_form.html', form=form, category=cat)

@app.route('/category/<int:id>/delete', methods=['POST'])
def delete_category(id):
    cat = Category.query.get_or_404(id)
    for article in cat.articles:
        article.categories.remove(cat)
    db.session.delete(cat)
    db.session.commit()
    flash('Категория удалена', 'success')
    return redirect(url_for('categories_list'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)