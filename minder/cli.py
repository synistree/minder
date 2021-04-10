import IPython


def register_app_cli(app):
    @app.cli.command('ipy-shell', help='IPython shell for working within the Flask context')
    def ipy_shell():
        context = {}
        context.update(app.make_shell_context())
        IPython.embed(header='Welcome to the minder IPython shell', colors='linux', using='asyncio', local=context)


__all__ = ['register_app_cli']
