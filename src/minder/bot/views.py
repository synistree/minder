import discord
import logging

from aiohttp import web
from pprint import pformat
from typing import Mapping, Any, Optional, List

from minder.cogs.backend import routes
from minder.models.reminders import Reminder
from minder.utils import Timezone, FuzzyTime

logger = logging.getLogger(__name__)


async def _validate_post_data(request: web.Request, required_attrs: List[str]) -> Mapping[str, Any]:
    post_data = await request.json()
    json_data = {}

    for attr in required_attrs:
        if attr not in post_data:
            logger.debug(f'POST Data:\n{pformat(post_data, intent=2)}')
            raise web.HTTPInternalServerError(text=f'Missing required POST data field "{attr}"')

        if not post_data[attr]:
            logger.debug(f'POST Data:\n{pformat(post_data, indent=2)}')
            raise web.HTTPInternalServerError(text='Required POST data field "{attr}" is empty')

        json_data[attr] = post_data[attr]

    return json_data


def _member_to_dict(member: discord.Member, use_tz: Optional[Timezone] = None) -> Mapping[str, Any]:
    joined_ts = member.joined_at.timestamp() if not use_tz else member.joined_at.astimezone(use_tz.timezone).ctime()
    return {'id': member.id, 'name': member.name, 'discriminator': member.discriminator, 'joined_ts': joined_ts, 'avatar': str(member.avatar_url)}


def _get_bot(request: web.Request, check_ready: bool = True):
    bot = request.app.get('bot', request.config_dict.get('bot', None))

    if not bot:
        raise web.HTTPInternalServerError(text='Cannot find reference to bot object in application')

    if not check_ready and not bot.init_done:
        logger.warning('Received JSONAPI request for guilds before bot was ready.')
        raise web.HTTPInternalServerError(text='Discord bot is not yet ready')

    return bot


@routes.get('/')
async def index(request: web.Request) -> web.Response:
    return web.json_response({'running': True})


@routes.get('/members')
async def get_members(request: web.Request) -> web.Response:
    bot = _get_bot(request)
    mems = {mem.id: {'name': mem.name, 'guild': {mem.guild.id: mem.guild.name}, 'id': mem.id} for mem in bot.get_all_members()}

    if not mems:
        logger.warning('No members found querying bot, returning empty response')
        status_code = 204
    else:
        logger.debug(f'Found #{len(mems)} entries:\n{pformat(mems, indent=2)}')
        status_code = 200

    return web.json_response(mems, status=status_code)


@routes.get('/guilds')
async def get_guilds(request: web.Request) -> web.Response:
    bot = _get_bot(request)
    use_tz = request.query.get('use_tz', None)

    if use_tz:
        if not Timezone.is_valid_timezone(use_tz):
            raise web.HTTPInternalServerError(text='Invalid timezone name provided: "{use_tz}"')

        use_tz = Timezone.build(use_tz)

    glds = {}

    for gld in bot.guilds:
        gld_members = {mem.id: _member_to_dict(mem, use_tz=use_tz) for mem in gld.members}
        glds[gld.id] = {'id': gld.id, 'name': gld.name, 'description': gld.description, 'owner_id': gld.owner_id, 'members': gld_members}

    if not glds:
        logger.warning('No guild details found, returning empty response')
        status_code = 204
    else:
        logger.debug(f'Found #{len(glds)} entries:\n{pformat(glds, indent=2)}')
        status_code = 200

    return web.json_response(glds, status=status_code)


@routes.get('/reminders')
async def get_reminders(request: web.Request) -> web.Response:
    bot = _get_bot(request)

    if not bot.redis_helper.keys(redis_id='reminders'):
        return web.json_response({'message': 'No reminders found', 'reminders': []})

    include_complete = request.query.get('include_complete', True)
    rem_ents = {}
    member_id = int(request.query['member_id']) if 'member_id' in request.query else None

    for r_id, r_ent in Reminder.fetch_all(bot.redis_helper, redis_id='reminders', check_exists=False).items():
        if not include_complete and r_ent.is_complete:
            continue

        if member_id and (r_ent.member_id != member_id):
            continue

        rem_ents[r_id] = r_ent.as_dict()

    msg = 'No reminders found in Redis' if not rem_ents else f'Found #{len(rem_ents)} reminders in Redis'
    json_resp = {'message': msg, 'reminders': rem_ents, 'include_complete': include_complete}

    if member_id:
        json_resp['member_id'] = member_id

    return web.json_response(json_resp)


@routes.post('/reminders')
async def new_reminder(request: web.Request) -> web.Response:
    bot = _get_bot(request)

    await _validate_post_data(request, ['when', 'content', 'member_id'])

    post_data = await request.json()
    when = post_data['when']
    content = post_data['content']
    member_id = int(post_data['member_id'])

    member = discord.utils.get(bot.get_all_members(), id=member_id)

    if not member:
        if 'member_name' in post_data:
            member_name = post_data['member_name']
            member = {'id': member_id, 'name': member_name}
            logger.warning(f'Unable to resolve Discord member ID {member_id}: No member found. Using provided name "{member_name}"')
        else:
            raise web.HTTPInternalServerError(text=f'Unable to resolve member ID #{member_id}: No such member found and no name provided')
    else:
        member_name = member.name
        logger.info(f'Resolved provided member ID #{member_id} to "{member_name}" on server "{member.guild.name}"')

    if 'use_tz' in post_data:
        use_tz = post_data['use_tz']
        if not Timezone.is_valid_timezone(use_tz):
            raise web.HTTPInternalServerError(text='Invalid timezone name provided: "{use_tz}"')

        use_tz = Timezone.build(use_tz)
    else:
        use_tz = None

    try:
        trigger_time = FuzzyTime.build(when, use_timezone=use_tz)
    except Exception as ex:
        raise web.HTTPInternalServerError(text=f'Error parsing fuzzy time string "{when}": {ex}')

    rem_ent = Reminder.build(trigger_time=trigger_time, member=member, content=content, use_timezone=use_tz)

    logger.info(f'Received bot web request to create new reminder:\n{pformat(rem_ent.as_dict(), indent=4)}')

    rem_ent.store(bot.redis_helper)

    msg = f'Successfully created new reminder for member #{member_id} at "{when}" ({trigger_time.resolved_time}) with content "{content}"'
    json_res = {'new_reminder': rem_ent.as_dict(), 'message': msg}

    return web.json_response(json_res)
