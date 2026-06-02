import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Optional, ValidationError
from wtforms.widgets import TextArea

app = Flask(__name__)
app.config['SECRET_KEY'] = 'project-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Новая')
    priority = db.Column(db.String(20), default='Средний')
    assignee = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

class ProjectForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание')
    start_date = DateField('Дата начала', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('Дата окончания', validators=[Optional()], format='%Y-%m-%d')

    def validate_end_date(self, field):
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('Дата окончания не может быть раньше даты начала')

class TaskForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание')
    status = SelectField('Статус', choices=[('Новая', 'Новая'), ('В работе', 'В работе'), ('На проверке', 'На проверке'), ('Завершена', 'Завершена')])
    priority = SelectField('Приоритет', choices=[('Низкий', 'Низкий'), ('Средний', 'Средний'), ('Высокий', 'Высокий')])
    assignee = StringField('Исполнитель', validators=[DataRequired()])

@app.route('/')
def projects():
    projects = Project.query.all()
    for p in projects:
        total = len(p.tasks)
        completed = sum(1 for t in p.tasks if t.status == 'Завершена')
        p.progress = (completed / total * 100) if total > 0 else 0
    return render_template('pm_projects.html', projects=projects)

@app.route('/project/<int:id>')
def view_project(id):
    project = Project.query.get_or_404(id)
    total = len(project.tasks)
    completed = sum(1 for t in project.tasks if t.status == 'Завершена')
    progress = (completed / total * 100) if total > 0 else 0
    return render_template('pm_view_project.html', project=project, progress=progress)

@app.route('/project/add', methods=['GET', 'POST'])
def add_project():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data
        )
        db.session.add(project)
        db.session.commit()
        flash('Проект создан', 'success')
        return redirect(url_for('projects'))
    return render_template('pm_project_form.html', form=form, title='Добавить проект')

@app.route('/project/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        project.name = form.name.data
        project.description = form.description.data
        project.start_date = form.start_date.data
        project.end_date = form.end_date.data
        db.session.commit()
        flash('Проект обновлён', 'success')
        return redirect(url_for('projects'))
    return render_template('pm_project_form.html', form=form, title='Редактировать проект')

@app.route('/project/<int:id>/delete', methods=['POST'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Проект удалён', 'success')
    return redirect(url_for('projects'))

@app.route('/project/<int:project_id>/task/add', methods=['GET', 'POST'])
def add_task(project_id):
    project = Project.query.get_or_404(project_id)
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            priority=form.priority.data,
            assignee=form.assignee.data,
            project_id=project.id
        )
        db.session.add(task)
        db.session.commit()
        flash('Задача добавлена', 'success')
        return redirect(url_for('view_project', id=project.id))
    return render_template('pm_task_form.html', form=form, title='Добавить задачу', project=project)

@app.route('/task/<int:id>/edit', methods=['GET', 'POST'])
def edit_task(id):
    task = Task.query.get_or_404(id)
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.status = form.status.data
        task.priority = form.priority.data
        task.assignee = form.assignee.data
        db.session.commit()
        flash('Задача обновлена', 'success')
        return redirect(url_for('view_project', id=task.project_id))
    return render_template('pm_task_form.html', form=form, title='Редактировать задачу', project=task.project)

@app.route('/task/<int:id>/delete', methods=['POST'])
def delete_task(id):
    task = Task.query.get_or_404(id)
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash('Задача удалена', 'success')
    return redirect(url_for('view_project', id=project_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5002)