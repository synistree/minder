from minder.cli import add_user, list_users, delete_user

USER_HASH = 'pbkdf2:sha256:150000$o7FE9zQM$218d079dcb46ac3dc808efd512f067acc1e4a9a21b790179e90baab439c3ae41'  # == "abcd1234"


def test_cli_users(session, app):
    cli_runner = app.test_cli_runner()
    res_add = cli_runner.invoke(add_user, ['--username', 'pytest', '--password-hash', USER_HASH])
    assert res_add.exit_code == 0, f'Bad return code when adding "pytest"\n{res_add.output}'
    print('Successfully added new user "pytest" to testing database')

    res_dup_user = cli_runner.invoke(add_user, ['--username', 'pytest', '--password-hash', USER_HASH])
    res_dup_user_out = res_dup_user.output
    assert 'Username "pytest" already exists in database' in res_dup_user_out, f'Expected notice that "pytest" user already exists. Got:\n{res_dup_user_out}'

    res_list = cli_runner.invoke(list_users)
    res_list_out = res_list.output
    assert res_list.exit_code == 0, 'Bad return code when listing users'
    assert '│    1 │ pytest     │ No          │ Yes        │' in res_list_out, 'Missing "pytest" entry in user list'
    print(f'User table:\n{res_list_out}')

    res_del = cli_runner.invoke(delete_user, ['-u', 'pytest'])
    res_del_out = res_del.output
    assert res_del.exit_code == 0, 'Bad return code when deleting "pytest" user'
    assert 'Sucessfully deleted user "pytest" from database' in res_del_out, 'Missing successfully deleted line in output for "pytest" user'
    print('Successfully deleted testing "pytest" user from database')
