Minder Discord Bot
==================

Welcome to the ``minder`` [discord.py powered](https://discordpy.readthedocs.io/en/latest) reminder and basic management bot.

This bot leverages [Redis](https://redis.io/documentation) to persist short-term reminder entries that the bot will monitor and trigger based on the provided "fuzzy time" trigger requested. To accomplish this, the [redisent library](http://github.com/synistree/redisent) is used under the hood to easily marshal complex objects into and out of Redis.

This project primarily acts as a proof-of-concept of the features offered by this library but is growing into a full-fledged Discord administrative bot.

Features and Components
-----------------------

As the name implies, this bot was first authored to provide an easy-to-use means of scheduling arbitrary reminders via Discord. The design very much mimics the one Slack offers where a user can add a reminder using the [/reminder command](https://slack.com/help/articles/208423427-Set-a-reminder).

As for the implementation offered by ``minder``, the feature is offered via bot-prefixed commands as well as [Discord slash commands](https://blog.discord.com/slash-commands-are-here-8db0a385d9e6) via the [discord_slash library](https://discord-py-slash-command.readthedocs.io/en/latest):
