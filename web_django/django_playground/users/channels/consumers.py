from django.http import HttpResponse
from channels.handler import AsgiHandler
from channels import Group
from channels.auth import channel_session_user, channel_session_user_from_http
import json

from ..models import User
from ...services import moves_service

@channel_session_user_from_http
def ws_connect(message):
    Group('users').add(message.reply_channel)
    Group('users').send({
        'text': json.dumps({
            'username': message.user.username,
            'is_logged_in': True
        })
    })


@channel_session_user
def ws_disconnect(message):
    Group('users').send({
        'text': json.dumps({
            'username': message.user.username,
            'is_logged_in': False
        })
    })
    Group('users').discard(message.reply_channel)

def hello(message):
    print("Called Background task!")  # long running task or printing


def import_data(action):
    print("Background Import!")  # long running task or printing
    user = User.objects.get(id=action['user_id'])
    moves_service.import_storyline(user)
