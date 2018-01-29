from django.http import HttpResponse
from channels.handler import AsgiHandler
from channels import Group, Channel
from channels.auth import channel_session_user, channel_session_user_from_http
import json

from ..models import User
from ...services import moves_service


@channel_session_user_from_http
def ws_connect(message):

    Group('users').add(message.reply_channel)
    Group('user_{}'.format(message.user.id)).add(message.reply_channel)
    Channel(message.reply_channel.name).send({
        'text': json.dumps({
            'username': message.user.username,
            'message': 'New User connected {}'.format(message.user.id)
        })
    })


@channel_session_user
def ws_disconnect(message):
    user = message.user
    user.websocket.remove(message.reply_channel.name)
    user.save()


def hello(message):
    print("Background Hello!")  # long running task or printing
    # Group('user_{}'.format(message.user_id)).send({
    #     'text': json.dumps({
    #         'message': 'Import progress '
    #     })
    # })


def import_data(action):
    print("Background Import!")  # long running task or printing
    user = User.objects.get(id=action['user_id'])
    moves_service.import_storyline(user)
