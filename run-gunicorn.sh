pip install gunicorn
gunicorn --bind '0.0.0.0:80' 'minder.web.app:create_app()'
