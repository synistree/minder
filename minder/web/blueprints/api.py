import logging

from flask import Blueprint, jsonify, current_app, request

from minder.models import Reminder

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/reminders', methods=['GET'])
def reminders():
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

    return jsonify(rems)
