# coding: utf-8
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from .models import ViberUser, WhitePhone, Category, Question
from django.conf import settings
from django.core.mail import EmailMessage

from viberbot import Api
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.rich_media_message import RichMediaMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage
from viberbot.api.messages.contact_message import ContactMessage, Contact
from viberbot.api.viber_requests import ViberConversationStartedRequest, ViberFailedRequest, ViberMessageRequest

import sched
import shutil
import threading
import time
import logging
import json
import requests
import random
import os
from string import Template
from .jsons_storage import *
from .language_formatter import *


viber = Api(settings.BOT_CONFIGURATION)

scheduler = sched.scheduler(time.time, time.sleep)
scheduler.enter(5, 1, lambda: viber.set_webhook('https://' + settings.ALLOWED_HOSTS[0]))
t = threading.Thread(target=scheduler.run)
t.start()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.ERROR)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(name)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

menu_button_messages = ('ask', 'ask_custom', 'call_support', 'check_status', 'switch_lang')

def check_id(id_int: list, id_str: str):
    try:
        id_int.append(int(id_str))
    except ValueError:
        return False
    return id_int[0] >= 0


def send_main_menu(user_id: int, language: str):
    viber.send_messages(user_id, [
        KeyboardMessage(keyboard=json.loads(format_lang(menu_keyboard, menu_button_messages, language)),
                       min_api_version=3)])


def send_disclaimer(user_id: int, language: str):
    viber.send_messages(user_id, [RichMediaMessage(
        rich_media=json.loads(format_lang(disclaimer_rich_text, 'disclaimer', language)),
        min_api_version=4, keyboard=json.loads(format_lang(menu_keyboard, menu_button_messages, language)))])


def link(request):
    return HttpResponse('<a href="viber://pa?chatURI=' + settings.CHAT_URI + '">Link to chat</a>')

def send_email(subject, mail_text, mail, phone, viber_request):
    try:
        message = EmailMessage(subject, mail_text, settings.EMAIL_HOST_USER, [mail])
        fname = None
        if hasattr(viber_request.message, 'media'):
            r = requests.get(viber_request.message.media, verify=False, stream=True)
            r.raw.decode_content = True
            if hasattr(viber_request.message, 'file_name'):
                fname = viber_request.message.file_name
            else:
                fname = viber_request.message.media.split('?')[0].split('/')[-1]
            fname = os.path.join(settings.MEDIA_ROOT, fname)
            with open(fname, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            message.attach_file(fname)
        try:
            message.send(False)
        finally:
            if fname:
                os.remove(fname)
    except Exception as e:
        logger.error(e)
        logger.error("Mail wasn't delivered. Subject:%s, Text:%s, Phone:%s" % (subject, mail_text, phone))


@csrf_exempt
def index(request):
    try:
        # every viber message is signed, you can verify the signature using this method
        if not viber.verify_signature(request.body, request.META.get('HTTP_X_VIBER_CONTENT_SIGNATURE')):
            return HttpResponseForbidden()
        # this library supplies a simple way to receive a request object
        viber_request = viber.parse_request(str(request.body, 'utf-8', 'ignore'))
        #logger.error(viber_request)

        if isinstance(viber_request, ViberFailedRequest):
            logger.warning("client failed receiving message. failure: {0}".format(viber_request))
            return HttpResponse()

        viber_user = None
        if hasattr(viber_request, 'user'):
            try:
                viber_user = ViberUser.objects.get(pk=viber_request.user.id)
            except ObjectDoesNotExist:
                pass
        elif hasattr(viber_request, 'sender'):
            try:
                viber_user = ViberUser.objects.get(pk=viber_request.sender.id)
            except ObjectDoesNotExist:
                pass

        if viber_user:
            if isinstance(viber_request, ViberConversationStartedRequest):
                send_disclaimer(viber_user.user_id, viber_user.user_language)
            elif isinstance(viber_request, ViberMessageRequest):
                if viber_request.silent:
                    id_int = []
                    if viber_request.message.text == 'm':
                        send_main_menu(viber_user.user_id, viber_user.user_language)
                    elif viber_request.message.text[0] == 'c' and check_id(id_int, viber_request.message.text[1:]):
                        id_int = id_int[0]
                        if viber_request.message.tracking_data == 'cust':
                            viber.send_messages(viber_user.user_id, [
                                TextMessage(tracking_data = id_int, text=format_lang(None, 'enter_question', viber_user.user_language), 
                                            keyboard=json.loads(get_main_menu_keyboard(viber_user.user_language)), min_api_version=3)
                            ])
                        else:
                            viber.send_messages(viber_user.user_id, [
                                RichMediaMessage(rich_media=json.loads(get_unified_button_keyboard(
                                        ['q' + str(quest.id) for quest in Question.objects.filter(category_id=id_int).order_by('id')],
                                        [quest.question_text_ru if is_ru(viber_user.user_language) else quest.question_text_en
                                            for quest in Question.objects.filter(category_id=id_int).order_by('id')],
                                        viber_user.user_language, rich=True)
                                    ), keyboard=json.loads(format_lang(menu_keyboard, menu_button_messages, viber_user.user_language)), min_api_version=3)
                            ])
                    elif viber_request.message.text[0] == 'q' and check_id(id_int, viber_request.message.text[1:]):
                        quest = Question.objects.get(pk=int(id_int[0]))
                        viber.send_messages(viber_user.user_id, [
                                RichMediaMessage(rich_media=json.loads(Template(question_rich_text).substitute({'answer_url': quest.answer_url or '', 
                                                 'action_type': 'open-url' if quest.answer_url else 'none', 'bg_color': '#A9CCE3' if quest.answer_url else '#D5DBDB',
                                                 'answer_text': quest.answer_text_ru if is_ru(viber_user.user_language) else quest.answer_text_en})), 
                                                 keyboard=json.loads(format_lang(menu_keyboard, menu_button_messages, viber_user.user_language)), min_api_version=3)
                            ])
                    elif viber_request.message.text == 'ask':
                        viber.send_messages(viber_user.user_id, [
                            KeyboardMessage(keyboard=json.loads(get_unified_button_keyboard(
                                ['c' + str(cat.id) for cat in Category.objects.all().order_by('id')],
                                [cat.category_name_ru if is_ru(viber_user.user_language) else cat.category_name_en
                                    for cat in Category.objects.all().order_by('id')], viber_user.user_language)), 
                                min_api_version=3)
                        ])
                    elif viber_request.message.text == 'cust':
                        viber.send_messages(viber_user.user_id, [
                            KeyboardMessage(tracking_data='cust', keyboard=json.loads(get_unified_button_keyboard(
                                ['c' + str(cat.id) for cat in Category.objects.all().order_by('id')],
                                [cat.category_name_ru if is_ru(viber_user.user_language) else cat.category_name_en

                                    for cat in Category.objects.all().order_by('id')], viber_user.user_language)), 
                                min_api_version=3)
                        ])
                    elif viber_request.message.text == 'call':
                        viber.send_messages(viber_user.user_id, [
                            ContactMessage(contact = Contact(name=format_lang(None, 'contact_name', viber_request.sender.language),
                                                     phone_number=format_lang(None, 'contact_phone', viber_request.sender.language)), 
                                           keyboard = json.loads(format_lang(menu_keyboard, menu_button_messages, 
                                                                        viber_user.user_language)), min_api_version = 3)
                            ])
                    elif viber_request.message.text == 'check':
                        mail = format_lang(None, 'email', viber_user.user_language)
                        subject = format_lang(None, 'email_subject_check', viber_user.user_language)
                        phone = viber_user.phone.phone_number_text
                        mail_text = Template(format_lang_not_for_json(None, 'email_template_check', viber_user.user_language)).substitute(
                            {'phone': phone})
                        viber.send_messages(viber_user.user_id, [
                            TextMessage(text=format_lang(None, 'check_accepted', viber_user.user_language), 
                                        keyboard=json.loads(format_lang(menu_keyboard, menu_button_messages, 
                                                                        viber_user.user_language)), min_api_version=3)
                            ])
                        if EmailMessage(subject, mail_text, settings.EMAIL_HOST_USER, [mail]).send(True) != 1:
                            raise Exception("Mail wasn't delivered. Subject:%s, Text:%s, Phone:%s"%(subject, mail_text, phone))
                    elif viber_request.message.text == 'att_n':
                        track_data = viber_request.message.tracking_data.split('|', 1)
                        mail = format_lang(None, 'email', viber_user.user_language)
                        subject = format_lang(None, 'email_subject', viber_user.user_language)
                        phone = viber_user.phone.phone_number_text
                        category = Category.objects.get(pk=int(track_data[0]))
                        mail_text = Template(format_lang_not_for_json(None, 'email_template', viber_user.user_language)).substitute(
                            {'question_text': track_data[1], 'phone': phone, 
                             'category': category.category_name_ru if is_ru(viber_user.user_language) else category.category_name_en})
                        viber.send_messages(viber_user.user_id, [
                                TextMessage(text=format_lang(None, 'question_accepted', viber_user.user_language), 
                                            keyboard=json.loads(format_lang(menu_keyboard, menu_button_messages, 
                                                                            viber_user.user_language)), min_api_version=3)
                                ])
                        if EmailMessage(subject, mail_text, settings.EMAIL_HOST_USER, [mail]).send(True) != 1:
                            raise Exception("Mail wasn't delivered. Subject:%s, Text:%s, Phone:%s"%(subject, mail_text, phone))
                    elif viber_request.message.text == 'sl':
                        viber_user.user_language = 'en' if is_ru(viber_user.user_language) else 'ru'
                        viber_user.save()
                        viber_user.refresh_from_db()
                        send_main_menu(viber_user.user_id, viber_user.user_language)
                else:
                    track_data = viber_request.message.tracking_data.split('|', 1)
                    if len(track_data) == 1:
                        viber.send_messages(viber_user.user_id, [
                            TextMessage(tracking_data = viber_request.message.tracking_data + '|' + viber_request.message.text,
                                text=format_lang(None, 'attach_file', viber_user.user_language), 
                                keyboard=json.loads(format_lang(attach_file_keyboard, ['att_n'], 
                                                                        viber_user.user_language)), min_api_version=3)
                            ])
                    else:
                        mail = format_lang(None, 'email', viber_user.user_language)
                        subject = format_lang(None, 'email_subject', viber_user.user_language)
                        phone = viber_user.phone.phone_number_text
                        category = Category.objects.get(pk=int(track_data[0]))
                        mail_text = Template(format_lang_not_for_json(None, 'email_template', viber_user.user_language)).substitute(
                            {'question_text': track_data[1], 'phone': phone, 
                             'category': category.category_name_ru if is_ru(viber_user.user_language) else category.category_name_en})
                        viber.send_messages(viber_user.user_id, [
                                TextMessage(text=format_lang(None, 'question_accepted', viber_user.user_language), 
                                            keyboard=json.loads(format_lang(menu_keyboard, menu_button_messages, 
                                                                            viber_user.user_language)), min_api_version=3)
                                ])
                        thr = threading.Thread(target=send_email, args=(subject, mail_text, mail, phone, viber_request))
                        thr.start()
        else:
            if isinstance(viber_request, ViberConversationStartedRequest):# or (isinstance(viber_request, ViberMessageRequest) and viber_request.silent):
                viber.send_messages(viber_request.user.id, [
                    KeyboardMessage(keyboard=json.loads(authorize_keyboard), min_api_version=4)])
            elif isinstance(viber_request, ViberMessageRequest):
                phone = None
                if hasattr(viber_request.message, 'text'):
                    m_phone = str(viber_request.message.text)
                elif hasattr(viber_request.message, 'contact'):
                    m_phone = viber_request.message.contact.phone_number
                try:
                    if m_phone.isalnum():
                        phone = WhitePhone.objects.get(pk=m_phone)
                except ObjectDoesNotExist:
                    pass
                if phone:
                    ViberUser.objects.create(user_id=viber_request.sender.id, phone=phone,
                                             user_language=viber_request.sender.language)
                    send_disclaimer(viber_request.sender.id, viber_request.sender.language)
                else:
                    viber.send_messages(viber_request.sender.id, [
                                        KeyboardMessage(keyboard=json.loads(format_lang(not_authorized_keyboard, 'not_authorized',
                                        viber_request.sender.language)), min_api_version=4)
                                        ])
    except Exception as e:
        logger.error(e)
    finally:
        return HttpResponse()
