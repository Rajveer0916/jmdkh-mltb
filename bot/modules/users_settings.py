from functools import partial
from html import escape
from os import mkdir, path, remove
from time import sleep, time

from PIL import Image
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler)

from bot import DATABASE_URL, config_dict, dispatcher, user_data
from bot.helper.ext_utils.bot_utils import update_user_ldata
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage

handler_dict = {}

def get_user_settings(from_user):
    user_id = from_user.id
    name = from_user.full_name
    buttons = ButtonMaker()
    thumbpath = f"Thumbnails/{user_id}.jpg"
    user_dict = user_data.get(user_id, False)
    if not user_dict and config_dict['AS_DOCUMENT'] or user_dict and user_dict.get('as_doc'):
        ltype = "DOCUMENT"
        buttons.sbutton("Send As Media", f"userset {user_id} med")
    else:
        ltype = "MEDIA"
        buttons.sbutton("Send As Document", f"userset {user_id} doc")

    if user_dict and user_dict.get('lprefix'):
        lprefix = user_dict['lprefix']
        buttons.sbutton("Change Leech Prefix", f"userset {user_id} lprefix")
        buttons.sbutton("Remove Leech Prefix", f"userset {user_id} rlpre")
    else:
        buttons.sbutton("Add Leech Prefix", f"userset {user_id} lprefix")
        lprefix = 'None'

    if user_dict and user_dict.get('yt_ql'):
        ytq = user_dict['yt_ql']
        buttons.sbutton("Change YT-DLP Quality", f"userset {user_id} yt_ql")
        buttons.sbutton("Remove YT-DLP Quality", f"userset {user_id} rytq")
    elif config_dict['YT_DLP_QUALITY']:
        ytq = config_dict['YT_DLP_QUALITY']
        buttons.sbutton("Set YT-DLP Quality", f"userset {user_id} yt_ql")
    else:
        buttons.sbutton("Set YT-DLP Quality", f"userset {user_id} yt_ql")
        ytq = 'None'

    if path.exists(thumbpath):
        thumbmsg = "Exists"
        buttons.sbutton("Change Thumbnail", f"userset {user_id} sthumb")
        buttons.sbutton("Delete Thumbnail", f"userset {user_id} dthumb")
    else:
        thumbmsg = "Not Exists"
        buttons.sbutton("Set Thumbnail", f"userset {user_id} sthumb")

    buttons.sbutton("Close", f"userset {user_id} close")
    text = f"<u>Settings for <a href='tg://user?id={user_id}'>{name}</a></u>\n"\
            f"Leech Type <b>{ltype}</b>\n" \
            f"Custom Thumbnail <b>{thumbmsg}</b>\n" \
            f"YT-DLP Quality is <code>{escape(ytq)}</code>\n" \
            f"Leech Prefix <code>{escape(lprefix)}</code>"
    return text, buttons.build_menu(1)

def update_user_settings(message, from_user):
    msg, button = get_user_settings(from_user)
    editMessage(msg, message, button)

def user_settings(update, context):
    msg, button = get_user_settings(update.message.from_user)
    sendMessage(msg, context.bot, update.message, button)

def get_message(key):
    if key == 'yt_ql':
        rmsg = f'''
Send YT-DLP Qaulity. Timeout: 60 sec
Examples:
1. <code>{escape('bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]')}</code> this will give 1080p-mp4.

2. <code>{escape('bv*[height<=720][ext=webm]+ba/b[height<=720]')}</code> this will give 720p-webm.

Check all available qualities options <a href="https://github.com/yt-dlp/yt-dlp#filtering-formats">HERE</a>.
        '''
    elif key == 'lprefix':
        rmsg = f'''
Send Leech Prefix. Timeout: 60 sec
Examples:
1. <code>{escape('<b>@JMDKH_Team</b>')}</code> 
This will give output of:
<b>@JMDKH_Team</b>  <code>50MB.bin</code>.

2. <code>{escape('<code>@JMDKH_Team</code>')}</code> 
This will give output of:
<code>@JMDKH_Team</code> <code>50MB.bin</code>.

Check all available formatting options <a href="https://core.telegram.org/bots/api#formatting-options">HERE</a>.
        '''
    return rmsg

def set_values(update, context, omsg, key):
    message = update.message
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    update_user_ldata(user_id, key, value)
    update.message.delete()
    update_user_settings(omsg, message.from_user)
    if DATABASE_URL:
        DbManger().update_user_data(user_id)

def set_thumb(update, context, omsg):
    message = update.message
    user_id = message.from_user.id
    handler_dict[user_id] = False
    path_ = "Thumbnails/"
    if not path.isdir(path_):
        mkdir(path_)
    photo_dir = message.photo[-1].get_file().download()
    user_id = message.from_user.id
    des_dir = path.join(path_, f'{user_id}.jpg')
    Image.open(photo_dir).convert("RGB").save(des_dir, "JPEG")
    remove(photo_dir)
    update_user_ldata(user_id, 'thumb', des_dir)
    update.message.delete()
    update_user_settings(omsg, message.from_user)
    if DATABASE_URL:
        DbManger().update_thumb(user_id, des_dir)

def edit_user_settings(update, context):
    query = update.callback_query
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "doc":
        update_user_ldata(user_id, 'as_doc', True)
        query.answer(text="Your File Will Deliver As Document!", show_alert=True)
        update_user_settings(message, query.from_user)
        if DATABASE_URL:
            DbManger().update_user_data(user_id)
    elif data[2] == "med":
        update_user_ldata(user_id, 'as_doc', False)
        query.answer(text="Your File Will Deliver As Media!", show_alert=True)
        update_user_settings(message, query.from_user)
        if DATABASE_URL:
            DbManger().update_user_data(user_id)
    elif data[2] == "dthumb":
        path_ = f"Thumbnails/{user_id}.jpg"
        if path.lexists(path_):
            query.answer(text="Thumbnail Removed!", show_alert=True)
            remove(path_)
            update_user_ldata(user_id, 'thumb', '')
            update_user_settings(message, query.from_user)
            if DATABASE_URL:
                DbManger().update_thumb(user_id)
        else:
            query.answer(text="Old Settings", show_alert=True)
            update_user_settings(message, query.from_user)
    elif data[2] == "sthumb":
        query.answer()
        if handler_dict.get(user_id):
            handler_dict[user_id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[user_id] = True
        buttons = ButtonMaker()
        buttons.sbutton("Back", f"userset {user_id} back")
        buttons.sbutton("Close", f"userset {user_id} close")
        editMessage('Send a photo to save it as custom thumbnail. Timeout: 60 sec', message, buttons.build_menu(1))
        partial_fnc = partial(set_thumb, omsg=message)
        photo_handler = MessageHandler(filters=Filters.photo & Filters.chat(message.chat.id) & Filters.user(user_id),
                                       callback=partial_fnc)
        dispatcher.add_handler(photo_handler)
        while handler_dict[user_id]:
            if time() - start_time > 60:
                handler_dict[user_id] = False
                update_user_settings(message, query.from_user)
        dispatcher.remove_handler(photo_handler)
    elif data[2] in ['yt_ql', 'lprefix']:
        query.answer()
        if handler_dict.get(user_id):
            handler_dict[user_id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[user_id] = True
        buttons = ButtonMaker()
        buttons.sbutton("Back", f"userset {user_id} back")
        buttons.sbutton("Close", f"userset {user_id} close")
        rmsg = get_message(data[2])
        editMessage(rmsg, message, buttons.build_menu(1))
        partial_fnc = partial(set_values, omsg=message, key=data[2])
        value_handler = MessageHandler(filters=Filters.text & Filters.chat(message.chat.id) & Filters.user(user_id),
                                       callback=partial_fnc)
        dispatcher.add_handler(value_handler)
        while handler_dict[user_id]:
            if time() - start_time > 60:
                handler_dict[user_id] = False
                update_user_settings(message, query.from_user)
        dispatcher.remove_handler(value_handler)
    elif data[2] == 'rytq':
        query.answer(text="YT-DLP Quality Removed!", show_alert=True)
        update_user_ldata(user_id, 'yt_ql', '')
        update_user_settings(message, query.from_user)
        if DATABASE_URL:
            DbManger().update_user_data(user_id)
    elif data[2] == 'rlpre':
        query.answer(text="Leech Prefix Removed!", show_alert=True)
        update_user_ldata(user_id, 'lprefix', '')
        update_user_settings(message, query.from_user)
        if DATABASE_URL:
            DbManger().update_user_data(user_id)
    elif data[2] == 'back':
        query.answer()
        handler_dict[user_id] = False
        update_user_settings(message, query.from_user)
    else:
        query.answer()
        handler_dict[user_id] = False
        query.message.delete()
        query.message.reply_to_message.delete()

def send_users_settings(update, context):
    msg = ''.join(f'<code>{u}</code>: {escape(str(d))}\n\n' for u, d in user_data.items())
    if msg:
        sendMessage(msg, context.bot, update.message)
    else:
        sendMessage('No users data!', context.bot, update.message)

users_settings_handler = CommandHandler(BotCommands.UsersCommand, send_users_settings,
                                            filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
user_set_handler = CommandHandler(BotCommands.UserSetCommand, user_settings,
                                   filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
but_set_handler = CallbackQueryHandler(edit_user_settings, pattern="userset")

dispatcher.add_handler(user_set_handler)
dispatcher.add_handler(but_set_handler)
dispatcher.add_handler(users_settings_handler)
