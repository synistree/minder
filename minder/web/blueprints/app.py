import logging

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user, login_required, login_user, logout_user

from minder.web.forms import LoginForm

app_bp = Blueprint('app', __name__)
logger = logging.getLogger(__name__)


@app_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash(f'Already logged in as "{current_user}"')
        return redirect(url_for('app.overview'))

    from minder.web.model import User

    form = LoginForm(request.form)

    if request.method == 'POST' and form.validate_on_submit():
        logger.debug(f'Looking up user information for "{form.username.data}"')
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            logger.warning(f'Received invalid login for "{form.username.data}".')
            return redirect(url_for('app.login'))

        if not user.enabled:
            flash('User is disabled :(', 'error')
            logger.warning(f'Received login from disabled user "{form.username.data}"')
            return redirect(url_for('app.login'))

        logger.info(f'Logging in user "{user.username}" after successful authentication')
        login_user(user, remember=True)

        flash(f'Successfully logged in as "{user.username}"')
        return redirect(url_for('app.overview'))

    return render_template('login.j2', title='Sign In', form=form)


@app_bp.route('/')
@login_required
def overview():
    return render_template('overview.j2')



@app_bp.route('/manage', methods=['GET'])
@login_required
def manage():
    return render_template('manage.j2', title='Manage Minder')


@app_bp.route('/success', methods=['GET'])
@login_required
def success():
    return render_template('success.j2', title='Successful Login')


@app_bp.route('/logout', methods=['GET'])
def logout():
    if not current_user.is_authenticated:
        flash('Not logged in.', 'error')
        return redirect(url_for('app.overview'))

    logout_user()
    return redirect(url_for('app.login'))
