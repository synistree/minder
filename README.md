# minder - Python Discord Bot

Minder is a [discord.py](https://discordpy.readthedocs.io/en/stable/) powered Python Discord Bot with a growing number of helpful administrative features as well as a comprehensive built in reminder system.

Under the hood, the application leverages [redis-py](https://github.com/andymccurdy/redis-py) for storing data asyncronously as well as a [Flask](https://flask.palletsprojects.com/en/1.1.x/) web backend that provides a UI for monitoring and managing the bot.

See the [redisent](http://github.com/synistree/redisent) GitHub repository for more details on the library reponsible for working with Redis which was authored for this project.

## Build Status

| Branch | Documentation | Build |
|--------|---------------|-------|
| [devel](https://github.com/synistree/minder/tree/devel) | [![devel Documentation](https://readthedocs.org/projects/minder/badge/?version=latest)](https://minder.readthedocs.io/en/latest/?badge=latest) | [![devel](https://travis-ci.com/synistree/minder.svg?branch=devel)](https://travis-ci.com/synistree/minder) |
| [master](https://github.com/synistree/minder/tree/master) | [![stable](https://readthedocs.org/projects/minder/badge/?version=stable)](https://minder.readthedocs.io/en/latest/?badge=stable) | [![master](https://travis-ci.com/synistree/minder.svg?branch=master)](https://travis-ci.com/synistree/minder)

## Quick Start
To start with, check out the project and create a new Python 3.8 or 3.9 virtual environment for running ``minder``:

```bash
# Use "-b master" for the stable verson
$ git clone https://github.com/synistree/minder -o gh -b devel
Cloning into 'minder'...
remote: Enumerating objects: 478, done.
remote: Counting objects: 100% (478/478), done.
remote: Compressing objects: 100% (254/254), done.
remote: Total 478 (delta 247), reused 421 (delta 203), pack-reused 0
Receiving objects: 100% (478/478), 1.34 MiB | 3.95 MiB/s, done.
Resolving deltas: 100% (247/247), done.

$ cd minder

# Create virtualenv and symlink activate script into root path
$ python3.9 -m venv --prompt 'minder' .venv &&ln -s .venv/bin/activate ./activate

# Activate the script
$ source ./activate

# Finally, install dependencies and the minder project in the virtualenv
(minder) $ python -m pip install -U pip build wheel
Collecting pip
  Downloading pip-21.1-py3-none-any.whl (1.5 MB)
     |████████████████████████████████| 1.5 MB 2.1 MB/s
Collecting build
  Using cached build-0.3.1.post1-py2.py3-none-any.whl (13 kB)
Collecting wheel
  Using cached wheel-0.36.2-py2.py3-none-any.whl (35 kB)
Collecting toml
  Using cached toml-0.10.2-py2.py3-none-any.whl (16 kB)
  
  .........

      Successfully uninstalled pip-20.1.1
Successfully installed build-0.3.1.post1 packaging-20.9 pep517-0.10.0 pip-21.1 pyparsing-2.4.7 toml-0.10.2 wheel-0.36.2
(minder) $ pip install -r ./requirements.txt
Collecting redisent
  Cloning git://github.com/synistree/redisent.git (to revision devel) to /tmp/pip-install-1xjvcsi1/redisent_f962aa7ed51a43d692f2174d38b0ac9e
  Running command git clone -q git://github.com/synistree/redisent.git /tmp/pip-install-1xjvcsi1/redisent_f962aa7ed51a43d692f2174d38b0ac9e
  Running command git checkout -b devel --track origin/devel
  Switched to a new branch 'devel'
  Branch 'devel' set up to track remote branch 'devel' from 'origin'.
  Installing build dependencies ... done

  ..........


Successfully installed APScheduler-3.7.0 IPython-7.22.0 Jinja2-2.11.3 MarkupSafe-1.1.1 SQLAlchemy-1.4.11 SQLAlchemy-Utils-0.37.0 WTForms-2.3.3 WTForms-Alchemy-0.17.0 WTForms-Components-0.10.5 Werkzeug-1.0.1 aiohttp-3.7.4.post0 async-timeout-3.0.1 attrs-20.3.0 backcall-0.2.0 beautifulsoup4-4.9.3 chardet-4.0.0 click-7.1.2 cogwatch-2.1.0 colorama-0.4.4 colorlog-5.0.1 dataclassy-0.8.2 dateparser-1.0.0 decorator-5.0.7 discord-ext-menus-1.0 discord-py-slash-command-1.1.2 discord.py-1.7.1 dnspython-2.1.0 dominate-2.6.0 email-validator-1.1.2 emoji-1.2.0 flask-1.1.2 flask-Bootstrap-3.3.7.1 flask-Login-0.5.0 flask-Moment-0.11.0 flask-Pretty-0.2.0 flask-SQLAlchemy-2.5.1 flask-WTF-0.14.3 greenlet-1.0.0 humanize-3.4.1 idna-3.1 infinity-1.5 intervals-0.9.1 ipython-genutils-0.2.0 itsdangerous-1.1.0 jedi-0.18.0 multidict-5.1.0 parso-0.8.2 pexpect-4.8.0 pickleshare-0.7.5 prompt-toolkit-3.0.18 ptyprocess-0.7.0 pyYAML-5.4.1 pygments-2.8.1 python-dateutil-2.8.1 python-dotenv-0.17.0 pytz-2021.1 redis-3.5.3 redisent-1.1.1 regex-2021.4.4 six-1.15.0 soupsieve-2.2.1 tabulate-0.8.9 traitlets-5.0.5 typing-extensions-3.7.4.3 tzlocal-2.1 validators-0.18.2 visitor-0.1.3 watchgod-0.7 wcwidth-0.2.5 yarl-1.6.3
(minder) $ pip install -U .
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
    Preparing wheel metadata ... done
Requirement already satisfied: Werkzeug in ./.venv/lib/python3.9/site-packages (from minder-synistree==0.11.1) (1.0.1)
Building wheels for collected packages: minder-synistree
  Building wheel for minder-synistree (PEP 517) ... done
  Created wheel for minder-synistree: filename=minder_synistree-0.11.1-py3-none-any.whl size=1667701 sha256=19901555e03c3c2f2efcf89a43acae266ae8cae09fa452f1daad4e4c50472d3c
  Stored in directory: /tmp/pip-ephem-wheel-cache-3f3ult_d/wheels/f1/71/31/7d981c36f3719cc5066adeba9116a52d9d0a0294ac7a854bf9
Successfully built minder-synistree
Installing collected packages: minder-synistree
Successfully installed minder-synistree-0.11.1
```

At this point the application and dependencies are all ready to go and the next step will be creating the [Discord developer account](http://discordapp.com/developers/applications) and finally creating the ``.env`` configuration for the bot.

### Creating a Bot account in the Developer Portal
Go ahead and login to your [Discord developer account](http://discordapp.com/developers/applications) and select the "New Application" button to get started creating your bot.

The first page will let the user set the bot's username and avatar as well as provide a basic description and associated URLs for the project. Once done here, click on the "Bot" Settings page and convert this application into a bot (this cannot be undone so make sure all other settings are correct prior to doing this).

Once created, there will be an option to reveal or copy the "Token" for the new bot. This value will be used as the ``BOT_TOKEN`` vaule in the ``.env`` file which will be created next. This token can be regenerated but it effectively gives anyone having the token full control over the bot so be very careful with this key.
