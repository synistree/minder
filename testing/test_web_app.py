import re

from pprint import pformat

from minder.web.model import User


def test_get_index(client, session, fake_member, fake_text_channel):
    creds = {'username': 'pytest', 'password': 'pyt3s7'}
    logged_in_div = 'Successfully logged in as "pytest"'
    re_login_path = re.compile(r'/login(/?next=.*)?$')

    rv = client.get('/')
    assert rv.status_code == 302, f'Received non HTTP redirect status code {rv.status_code} (should be 302)'
    redirect = rv.location
    assert redirect.endswith('/login?next=%2F'), f'HTTP redirect does not appear to point to login page. Got: "{redirect}"'
    print(f'Received HTTP 302 when fetching "/" pointing to "{redirect}"')

    print('Testing login with no users')
    rv = client.post(redirect, data=creds)
    assert rv.status_code == 302, f'Received unexpected status code of "{rv.status_code}" (expected HTTP 302 redirect)'
    assert re_login_path.search(rv.location), f'HTTP redirect does not appear to point to login path. Got: "{rv.location}"'

    auth_rv = client.get('/')
    assert auth_rv.status_code == 302, f'Received unexpected status code of "{auth_rv.status_code}" (expected HTTP 302 redirect)'
    assert auth_rv.location.endswith('/login?next=%2F'), f'HTTP redirect does not appear to point to login path. Got: "{auth_rv.location}"'

    print('Adding dummy "pytest" user')
    usr = User(username='pytest', password_hash=User.generate_password('pyt3s7'), is_admin=True)
    session.add(usr)
    session.commit()

    rv = client.post('/login', data=creds, follow_redirects=True)
    assert rv.status_code == 200, f'Received unexpected status code of "{rv.status_code}" (expected HTTP 200 OK)'

    err_details = f'Expected: {logged_in_div}\nContent:\n{rv.data}'
    assert logged_in_div.encode() in rv.data, f'Cannot find div indicating successful login in response.\n{err_details}'

    print('Sucessfully fetched authenticated index path after logging in with dummy user')


def test_fetch_api(client):
    rv = client.get('/api/reminders')
    assert rv.status_code == 200, f'Unexpected HTTP status code returned from "/api/reminders": "{rv.status_code}" (expected HTTP 200 OK)'
    assert not rv.json, f'Received unexpected results from "/api/reminders" (should be empty). Found:\n{pformat(rv.json)}'

    print(f'Fetched successful, empty result from API')
