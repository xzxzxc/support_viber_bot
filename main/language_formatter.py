# coding: utf-8
from .models import Message
from string import Template
import collections, types


def format_lang(message_text: str or types.NoneType, keys: str or collections.Iterable, lang: str):
    if isinstance(keys, str):
        keys = (keys,)
        if message_text is None:
            message_text = '$' + keys[0]
    keys_dict = dict(((x, None) for x in keys))
    for key in keys_dict.keys():
        message = Message.objects.get(pk=key)
        keys_dict[key] = (message.text_ru if is_ru(lang) else message.text_en).replace('\r', '\\r').replace('\n', '\\n')
    return Template(message_text).substitute(keys_dict)


def format_lang_not_for_json(message_text: str or types.NoneType, keys: str or collections.Iterable, lang: str):
    if isinstance(keys, str):
        keys = (keys,)
        if message_text is None:
            message_text = '$' + keys[0]
    keys_dict = dict(((x, None) for x in keys))
    for key in keys_dict.keys():
        message = Message.objects.get(pk=key)
        keys_dict[key] = (message.text_ru if is_ru(lang) else message.text_en)
    return Template(message_text).substitute(keys_dict)

def is_ru(lang: str):
    return lang in ('uk', 'ru')
