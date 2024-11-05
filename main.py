import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import nest_asyncio
import re  # Импортируем регулярные выражения для валидации email

# Разрешаем вложенные асинхронные циклы
nest_asyncio.apply()

# Настройки Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Укажите ссылку на вашу Google Таблицу
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1c6BT-To7vZ9rSZ3ucdD66pIUFWIOxd73NThNF5AAVKc/edit?hl=ru&gid=0'
spreadsheet_id = spreadsheet_url.split('/d/')[1].split('/')[0]
spreadsheet = client.open_by_key(spreadsheet_id)

# Определение состояний
CHOOSING_DAY, CHOOSING_TIME, TYPING_NAME_SURNAME, TYPING_PHONE, TYPING_EMAIL, CHOOSING_ACTION = range(6)

async def delete_if_exists_on_all_sheets(user_id):
    days = ['Вторник', 'Среда', 'Четверг']
    rows_to_delete = []

    for day in days:
        try:
            sheet = spreadsheet.worksheet(day)
            cells = sheet.findall(str(user_id))  # Ищем все ячейки с user_id
            for cell in cells:
                rows_to_delete.append((sheet, cell.row))  # Сохраняем ссылку на лист и строку для удаления
                print(f"Найден ID {user_id} на листе {day} в строке {cell.row}")
        except gspread.exceptions.WorksheetNotFound:
            print(f"Лист {day} не найден.")
        except Exception as e:
            print(f"Произошла ошибка: {e}")

    # Удаление строк с найденным user_id
    for sheet, row in rows_to_delete:
        sheet.delete_rows(row)  # Исправлено на delete_rows
        print(f"Удалена строка {row} с ID {user_id} на листе {sheet.title}")

    if not rows_to_delete:
        print(f"ID {user_id} не найден на всех листах.")

# Функция для валидации email
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Обработчик команды /stop
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"Запуск /stop для пользователя ID: {user_id}")

    # Проверяем, есть ли данные пользователя
    if not context.user_data:
        await update.message.reply_text("Вы не запускали бота. Пожалуйста, сначала напишите /start.")
        return

    # Очищаем данные пользователя
    context.user_data.clear()
    await update.message.reply_text("Вы остановили бота. Чтобы начать заново, напишите /start.")
    return ConversationHandler.END  # Завершаем текущую беседу

# Обработчик команды /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"Запуск /start для пользователя ID: {user_id}")

    await delete_if_exists_on_all_sheets(user_id)  # Вызов функции удаления для текущего user_id

    keyboard = [
        [InlineKeyboardButton("Среда", callback_data='Wednesday')],
        [InlineKeyboardButton("Четверг", callback_data='Thursday')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Здравствуйте! Вы попали на запись на Interview в Moldcell Academy 😎. Пожалуйста, выберите день:", reply_markup=reply_markup)

    return CHOOSING_DAY

# Обработчик выбора дня
async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки
    day_response = query.data

    # Переводим день на русский
    day_mapping = {'Tuesday': 'Вторник', 'Wednesday': 'Среда', 'Thursday': 'Четверг'}
    russian_day = day_mapping.get(day_response, day_response)

    context.user_data['day'] = day_response  # Сохраняем выбранный день

    # Отправляем пользователю сообщение с подтверждением выбора дня на русском
    await query.message.reply_text(f"Вы выбрали день: *{russian_day}* 📅.", parse_mode='Markdown')

    # Создаём инлайн-кнопки для выбора времени в зависимости от выбранного дня
    if day_response == 'Wednesday':
        keyboard = [
            [InlineKeyboardButton("13:30", callback_data='13:30'),
             InlineKeyboardButton("13:45", callback_data='13:45')],
            [InlineKeyboardButton("14:00", callback_data='14:00'),
             InlineKeyboardButton("14:15", callback_data='14:15')],
            [InlineKeyboardButton("17:00", callback_data='17:00'),
             InlineKeyboardButton("17:15", callback_data='17:15')],
            [InlineKeyboardButton("17:30", callback_data='17:30'),
             InlineKeyboardButton("17:45", callback_data='17:45')],
            [InlineKeyboardButton("18:00", callback_data='18:00')],
            [InlineKeyboardButton("Отмена выбора", callback_data='cancel')]
        ]
    elif day_response == 'Thursday':
        keyboard = [
            [InlineKeyboardButton("14:00", callback_data='14:00'),
             InlineKeyboardButton("14:15", callback_data='14:15')],
            [InlineKeyboardButton("14:30", callback_data='14:30'),
             InlineKeyboardButton("14:45", callback_data='14:45')],
            [InlineKeyboardButton("15:00", callback_data='15:00')],
            [InlineKeyboardButton("15:15", callback_data='15:15')],
            [InlineKeyboardButton("15:30", callback_data='15:30')],
            [InlineKeyboardButton("15:45", callback_data='15:45')],
            [InlineKeyboardButton("16:00", callback_data='16:00')],
            [InlineKeyboardButton("16:15", callback_data='16:15')],
            [InlineKeyboardButton("Отмена выбора", callback_data='cancel')]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Теперь выберите время:", reply_markup=reply_markup)

    return CHOOSING_TIME

# Обработчик выбора времени
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки
    user_response = query.data

    if user_response == 'cancel':
        await query.message.reply_text("Вы отменили выбор времени. Когда будете готовы записаться, напишите /start.")
        return ConversationHandler.END

    day = context.user_data['day']
    day_mapping = {'Tuesday': 'Вторник', 'Wednesday': 'Среда', 'Thursday': 'Четверг'}
    russian_day = day_mapping.get(day, day)

    # Проверка, существует ли соответствующий лист
    try:
        sheet = spreadsheet.worksheet(russian_day)
    except gspread.exceptions.WorksheetNotFound:
        # Создаём лист, если он не существует
        print(f"Создание нового листа: {russian_day}")
        sheet = spreadsheet.add_worksheet(title=russian_day, rows="100", cols="4")

    # Получаем все значения первого столбца (времени)
    occupied_times = sheet.col_values(1)  # Получаем все значения первого столбца

    # Проверяем, сколько раз время уже занято
    count = occupied_times.count(user_response)

    if count >= 3:  # Проверяем, если 3 или больше записей
        await query.message.reply_text(f"Время {user_response} уже занято. Пожалуйста, выберите другое время.", parse_mode='Markdown')
        return CHOOSING_TIME

    context.user_data['time'] = user_response
    await query.message.reply_text(f"⌚ Вы выбрали время: *{user_response}*.\n\nПожалуйста, введите ваше имя и фамилию через *пробел* по типу: Имя Фамилия", parse_mode='Markdown')

    return TYPING_NAME_SURNAME

# Обработчик ввода имени и фамилии
async def receive_name_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name_surname_response = update.message.text.split(maxsplit=2)
    
    if len(name_surname_response) < 2:
        await update.message.reply_text("Пожалуйста, введите ваше имя и фамилию через *пробел* по типу: Имя Фамилия", parse_mode='Markdown')
        return TYPING_NAME_SURNAME

    # Берем только первые два слова
    name_response = name_surname_response[0]
    surname_response = name_surname_response[1]
    
    context.user_data['name'] = name_response
    context.user_data['surname'] = surname_response
    await update.message.reply_text(f"Ваше имя: *📝 {name_response}*.\nВаша фамилия: *📝{surname_response}*.\n\nПожалуйста, введите ваш номер телефона по типу: 060123467", parse_mode='Markdown')

    return TYPING_PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_response = update.message.text

    # Проверка на наличие только цифр
    if not phone_response.isdigit():
        await update.message.reply_text("Пожалуйста, введите номер телефона только цифрами.")
        return TYPING_PHONE

    # Если необходимо, вы можете дополнительно проверить длину номера
    if len(phone_response) < 7:  # Например, минимальная длина для номера
        await update.message.reply_text("Номер телефона слишком короткий. Пожалуйста, введите корректный номер.")
        return TYPING_PHONE

    context.user_data['phone'] = phone_response

    day = context.user_data['day']  # Получаем день из пользовательских данных
    russian_day = {'Tuesday': 'Вторник', 'Wednesday': 'Среда', 'Thursday': 'Четверг'}.get(day)

    if not russian_day:
        await update.message.reply_text("Ошибка: день не распознан.")
        return ConversationHandler.END

    try:
        sheet = spreadsheet.worksheet(russian_day)  # Получаем соответствующий лист
    except gspread.exceptions.WorksheetNotFound:
        await update.message.reply_text(f"Ошибка: лист {russian_day} не найден.")
        return ConversationHandler.END

    # Отправляем пользователю сообщение с номером телефона
    await update.message.reply_text(f"📱 Ваш номер телефона: *{phone_response}*.\n\nПожалуйста, введите ваш E-mail по типу: example@gmail.com", parse_mode='Markdown')

    return TYPING_EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_response = update.message.text

    if not is_valid_email(email_response):
        await update.message.reply_text("Введите корректный email адрес.")
        return TYPING_EMAIL

    context.user_data['email'] = email_response
    day = context.user_data['day']
    russian_day = {'Tuesday': 'Вторник', 'Wednesday': 'Среда', 'Thursday': 'Четверг'}.get(day)

    if not russian_day:
        await update.message.reply_text("Ошибка: день не распознан.")
        return ConversationHandler.END

    try:
        sheet = spreadsheet.worksheet(russian_day)
    except gspread.exceptions.WorksheetNotFound:
        await update.message.reply_text(f"Ошибка: лист {russian_day} не найден.")
        return ConversationHandler.END

    # Подтверждение с введённым email
    await update.message.reply_text(f"📬 Ваш email: *{email_response}*.", parse_mode='Markdown')

    # Отладочный вывод
    print(f"Сохраняем данные: Время: {context.user_data['time']}, Имя: {context.user_data['name']}, Фамилия: {context.user_data['surname']}, Телефон: {context.user_data['phone']}, Email: {context.user_data['email']}, ID: {update.effective_user.id}")

    # Выводим все собранные данные и даем выбор
    data_summary = (
        f"Пожалуйста, подтвердите ваши данные:\n\n"
        f"📅 День: *{russian_day}*\n" 
        f"⌚ Время: *{context.user_data['time']}*\n"
        f"📝 Имя: *{context.user_data['name']}*\n"
        f"📝 Фамилия: *{context.user_data['surname']}*\n"
        f"📱 Телефон: *{context.user_data['phone']}*\n"
        f"📬 Email: *{context.user_data['email']}*\n"
    )

    await update.message.reply_text(data_summary, parse_mode='Markdown')

    # Создаем инлайн-кнопки для выбора
    keyboard = [
        [InlineKeyboardButton("Отправить данные", callback_data='send_data')],
        [InlineKeyboardButton("Перезаписать данные", callback_data='rewrite_data')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

    return CHOOSING_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Получаем день на русском языке
    russian_day = {'Tuesday': 'Вторник', 'Wednesday': 'Среда', 'Thursday': 'Четверг'}.get(context.user_data['day'])

    if query.data == 'send_data':
        row = [context.user_data['time'], context.user_data['name'], context.user_data['surname'], context.user_data['phone'], context.user_data['email'], update.effective_user.id]

        try:
            sheet = spreadsheet.worksheet(russian_day)
            sheet.append_row(row)
            await query.message.reply_text("Ваши данные сохранены! Если нужно перезаписаться, просто напишите /start.")
            await query.message.reply_text("Вскоре вы получите ссылку на ваш email для подключения к интервью. 🚀")
            print(f"Данные отправлены: Время: {context.user_data['time']}, Имя: {context.user_data['name']}, Фамилия: {context.user_data['surname']}, Телефон: {context.user_data['phone']}, Email: {context.user_data['email']}, День: {russian_day}, ID: {update.effective_user.id}")
        except Exception as e:
            await query.message.reply_text("Ошибка при сохранении данных. Попробуйте еще раз.")
            print(f"Ошибка: {e}")

    elif query.data == 'rewrite_data':
        print(f"Пользователь {update.effective_user.id} выбрал перезапись данных.")
        await query.message.reply_text("Вы выбрали перезапись данных. Напишите /start, чтобы начать заново.")

    # Сброс данных после завершения
    context.user_data.clear()
    return ConversationHandler.END

# Обновляем состояние в ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start_command)],
    states={
        CHOOSING_DAY: [CallbackQueryHandler(choose_day)],
        CHOOSING_TIME: [CallbackQueryHandler(button_callback)],
        TYPING_NAME_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name_surname)],
        TYPING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
        TYPING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
        CHOOSING_ACTION: [CallbackQueryHandler(handle_action)],
    },
    fallbacks=[
        CommandHandler('stop', stop_command),  # Добавляем обработчик /stop
    ],
)

if __name__ == '__main__':
    application = ApplicationBuilder().token("7713019096:AAGEpMBsD8SCeIWiH-Q7lcnJF2Sd2An1fzg").build()
    application.add_handler(conv_handler)

    print("Бот запущен!")
    application.run_polling()
