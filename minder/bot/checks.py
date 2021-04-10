from discord.ext import commands


def is_admin():
    def predicate(ctx: commands.Context) -> bool:
        usr_cfg = ctx.bot.bot_config.get_user(user_id=ctx.author.id)

        if not usr_cfg:
            return False

        return usr_cfg.get('is_admin', False)

    return commands.check(predicate)
