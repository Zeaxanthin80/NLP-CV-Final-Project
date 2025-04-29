from flask import Flask
from flask import render_template
from dotenv import load_dotenv
import os
from celery import Celery

load_dotenv()  # Load environment variables from .env file

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        broker=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    )
    celery.conf.update(app.config)
    print("CELERY_BROKER_URL:", app.config.get("CELERY_BROKER_URL"))
    print("CELERY_RESULT_BACKEND:", app.config.get("CELERY_RESULT_BACKEND"))
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    from . import routes
    app.register_blueprint(routes.bp)
    app.celery = make_celery(app)
    return app

def create_celery_app():
    # Used by celery_worker.py
    from . import create_app
    flask_app = create_app()
    return flask_app.celery
