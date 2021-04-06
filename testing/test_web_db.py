from minder.web.model import User


def test_fetch_user(session):
    users = session.query(User).all()

    assert not users, f'Unexpected Users returned from test database:\n{users}'

    usr = User(username='pytest', password_hash=User.generate_password('pyt3s7'), is_admin=False)

    session.add(usr)
    session.commit()

    print(f'Added new user:\n{usr}')

    fetch_usr = session.query(User).filter_by(username='pytest').one()

    assert fetch_usr, 'Unable to find newly created "pytest" user'

    print(f'Retrieved newly created user:\n{usr}')

    assert not fetch_usr.is_admin, f'Newly created user was incorrectly created as an admin: {usr}'
