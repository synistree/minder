import logging

from flask import Blueprint, jsonify, current_app, request

from minder.errors import MinderWebError
from minder.models import Reminder
from minder.utils import FuzzyTime

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/reminders', methods=['GET', 'POST'])
def reminders():
    if request.method == 'GET':
        exclude = [ex_attr.lower() for ex_attr in request.args.get('exclude', '').split(',')]
        member_id = request.args.get('member_id', None)
        channel_id = request.args.get('channel_id', None)

        rems = []

        for r_key in current_app.redis_helper.keys(redis_id='reminders', use_encoding='utf-8'):
            rem = Reminder.fetch(current_app.redis_helper, redis_id='reminders', redis_name=r_key)

            if 'complete' in exclude and rem.is_complete:
                continue

            if 'notified' in exclude and rem.user_notified:
                continue

            if member_id and int(member_id) != rem.member_id:
                continue

            if channel_id and int(channel_id) != rem.channel_id:
                continue

            rems.append(rem.as_dict())

        msg_out = 'No reminders found' if not rems else f'Found #{len(rems)} reminders'
        return jsonify({'message': msg_out, 'count': len(rems), 'is_error': False, 'data': rems})

    form_dict = request.form.to_dict()
    req_attrs = ['when', 'content', 'member_id', 'member_name']

    if 'channel_id' in request.form:
        req_attrs += ['channel_id', 'channel_name']

    for attr in req_attrs:
        if attr not in request.form:
            raise MinderWebError(f'No value for "{attr}" provided when attemptingn to create reminder', status_code=400, payload=form_dict)

    opts = {attr: request.form.get(attr) for attr in req_attrs}

    for o_name, o_val in opts.items():
        if not o_val:
            raise MinderWebError(f'No value provided for "{attr}" (value: "{o_val}")', status_code=400, payload=form_dict)

        if o_name.endswith('_id'):
            opts[o_name] = int(o_val)

    opts['timezone'] = request.form.get('timezone', None)
    when = opts['when']

    member_dict = {'id': opts['member_id'], 'name': opts['member_name']}

    channel_dict = {'id': opts['channel_id'], 'name': opts['channel_name']} if 'channel_id' in opts else None

    try:
        fuz_time = FuzzyTime.build(when, use_timezone=opts['timezone'])
    except Exception as ex:
        raise MinderWebError(f'Error parsing fuzzy timestamp for "{when}": {ex}', status_code=400, payload=form_dict, base_exception=ex) from ex

    try:
        rem = Reminder.build(fuz_time, member=member_dict, content=opts['content'], channel=channel_dict, use_timezone=opts['timezone'])
    except Exception as ex:
        raise MinderWebError(f'Error building new reminder for "{when}": {ex}', status_code=500, payload=form_dict, base_exception=ex) from ex

    try:
        rem.store(current_app.redis_helper)
    except Exception as ex:
        raise MinderWebError(f'Error storing new reminder for "{when}" in Redis: {ex}', status_code=500, payload=form_dict, base_exception=ex) from ex

    return jsonify({'message': f'Successfully built new reminder for "{when}" at "{rem.trigger_dt.ctime()}"', 'is_error': False, 'data': {'reminder': rem.as_dict()}})


@api_bp.route('/reminders/<id>', methods=['GET', 'DELETE'])
def reminder_by_id(id):
    try:
        rem = Reminder.fetch(current_app.redis_helper, redis_id='reminders', redis_name=id)
    except Exception as ex:
        raise MinderWebError(f'Error fetching reminder ID "{id}": {ex}', status_code=500, payload={'id': id}, base_exception=ex) from ex

    if not rem:
        raise MinderWebError(f'No reminder found with ID "{id}"', status_code=404, payload={'id': id})

    if request.method == 'GET':
        return jsonify(rem.as_dict())

    logger.info(f'Deleting reminder "{id}" as requested via API by "{request.remote_addr}"')

    rem.delete(current_app.redis_helper)

    return jsonify({'message': f'Deleted reminder "{id}" successfully', 'is_error': False})
