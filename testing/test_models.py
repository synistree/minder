import humanize

from datetime import datetime


def test_build_reminder(fake_channel_reminder, fake_dm_reminder):
    chan_rem = fake_channel_reminder
    print(f'Build test channel reminder:\n{chan_rem.dump()}')
    dt_now = datetime.now()
    assert not chan_rem.is_complete, f'Reminder is somehow considered complete? Now: {dt_now.ctime()} - Trigger: {chan_rem.trigger_dt.ctime()}'
    trigger_time = chan_rem.trigger_time.num_seconds_left
    nice_trigger = humanize.naturaldelta(trigger_time)
    print(f'Channel reminder is *NOT* marked complete. Has {trigger_time} seconds left (~ {nice_trigger})')

    dm_rem = fake_dm_reminder
    print(f'Build test DM reminder:\n{dm_rem.dump()}')
