"""
Telegram Bot Service для AI HR Agent
Обеспечивает автоматическую коммуникацию с кандидатами через Telegram
"""
import logging
import json
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище для активных сессий кандидатов
# В реальном проекте должно быть заменено на базу данных
active_sessions = {}
candidate_data = {}

class TelegramBotService:
    """Сервис для управления Telegram ботом для HR автоматизации"""
    
    def __init__(self, token: str = None, webhook_url: Optional[str] = None):
        """
        Инициализация сервиса Telegram бота
        
        Args:
            token: API токен Telegram бота
            webhook_url: URL для настройки webhook (опционально)
        """
        self.token = token
        self.webhook_url = webhook_url
        self.application = None
        self.is_running = False
        
    async def setup(self):
        """Настройка и запуск бота"""
        if not self.token:
            logger.error("Токен Telegram бота не предоставлен")
            return False
            
        try:
            # Создание приложения бота
            self.application = ApplicationBuilder().token(self.token).build()
            
            # Регистрация обработчиков команд
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            
            # Обработчик для текстовых сообщений
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Обработчик для callback-запросов от inline кнопок
            self.application.add_handler(CallbackQueryHandler(self.handle_callback))
            
            # Использование webhook или long polling в зависимости от настроек
            if self.webhook_url:
                await self.application.bot.set_webhook(url=self.webhook_url)
                logger.info(f"Webhook установлен на {self.webhook_url}")
                # В реальном приложении здесь будет настройка webhook сервера
            else:
                # Запуск в режиме long polling для тестирования
                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling()
                logger.info("Бот запущен в режиме long polling")
                
            self.is_running = True
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при настройке Telegram бота: {e}")
            return False
    
    async def stop(self):
        """Остановка бота"""
        if self.application and self.is_running:
            if self.webhook_url:
                await self.application.bot.delete_webhook()
            else:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            self.is_running = False
            logger.info("Telegram бот остановлен")
    
    async def send_message_to_candidate(self, chat_id: int, message: str, 
                                        reply_markup: Optional[InlineKeyboardMarkup] = None) -> bool:
        """
        Отправка сообщения кандидату
        
        Args:
            chat_id: Telegram chat ID кандидата
            message: Текст сообщения
            reply_markup: Опциональная клавиатура с кнопками
            
        Returns:
            bool: Успешность отправки
        """
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения кандидату {chat_id}: {e}")
            return False
    
    async def send_interview_invitation(self, chat_id: int, position: str, 
                                        company: str, date_time: str) -> bool:
        """
        Отправка приглашения на собеседование
        
        Args:
            chat_id: Telegram chat ID кандидата
            position: Название позиции
            company: Название компании
            date_time: Дата и время собеседования
            
        Returns:
            bool: Успешность отправки
        """
        message = (
            f"<b>Приглашение на собеседование</b>\n\n"
            f"Здравствуйте! Мы рассмотрели Ваше резюме на позицию "
            f"<b>{position}</b> в компании <b>{company}</b> и приглашаем Вас на собеседование.\n\n"
            f"<b>Дата и время:</b> {date_time}\n\n"
            f"Пожалуйста, подтвердите Ваше участие."
        )
        
        # Создаем inline-кнопки для ответа
        keyboard = [
            [
                InlineKeyboardButton("Подтвердить", callback_data=json.dumps({
                    "action": "confirm_interview",
                    "position": position,
                    "time": date_time
                })),
                InlineKeyboardButton("Предложить другое время", callback_data=json.dumps({
                    "action": "reschedule_interview",
                    "position": position
                }))
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return await self.send_message_to_candidate(chat_id, message, reply_markup)
    
    # Обработчики команд и сообщений
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        candidate_id = user.id
        
        # Сохраняем информацию о кандидате
        candidate_data[candidate_id] = {
            "id": candidate_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "registered_at": datetime.now().isoformat()
        }
        
        # Приветственное сообщение
        welcome_message = (
            f"Здравствуйте, {user.first_name}! 👋\n\n"
            f"Я HR-ассистент компании. Я могу помочь вам с:\n"
            f"• Информацией о вакансиях\n"
            f"• Статусом вашего отклика\n"
            f"• Ответами на часто задаваемые вопросы\n\n"
            f"Чем я могу вам помочь?"
        )
        
        # Создаем кнопки быстрых действий
        keyboard = [
            [InlineKeyboardButton("Вакансии", callback_data='{"action":"vacancies"}')],
            [InlineKeyboardButton("Статус отклика", callback_data='{"action":"application_status"}')],
            [InlineKeyboardButton("FAQ", callback_data='{"action":"faq"}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_message = (
            "Я HR-ассистент и могу помочь вам с процессом найма.\n\n"
            "Доступные команды:\n"
            "/start - Начать общение с ботом\n"
            "/status - Проверить статус вашего отклика\n"
            "/help - Показать это сообщение\n\n"
            "Вы также можете просто писать мне сообщения с вопросами."
        )
        await update.message.reply_text(help_message)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        user_id = update.effective_user.id
        
        # В реальном приложении здесь будет запрос к базе данных
        # для получения статуса отклика кандидата
        
        status_message = (
            "Текущий статус вашего отклика: <b>На рассмотрении</b>\n\n"
            "Мы свяжемся с вами в ближайшее время для уточнения деталей."
        )
        
        await update.message.reply_text(status_message, parse_mode='HTML')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        message_text = update.message.text
        user_id = update.effective_user.id
        
        # В реальном приложении здесь будет обработка сообщения с использованием AI
        # Например, классификация запроса и формирование ответа
        
        # Простой пример ответа
        if "вакансии" in message_text.lower():
            response = "У нас есть открытые вакансии: Software Developer, UI/UX Designer, Project Manager"
        elif "собеседование" in message_text.lower():
            response = "Для назначения собеседования нам нужно получить ваше резюме."
        elif "резюме" in message_text.lower():
            response = "Вы можете отправить резюме в формате PDF или DOC. Я передам его рекрутеру."
        else:
            response = (
                "Спасибо за ваше сообщение. Я перенаправлю его HR-менеджеру, "
                "который свяжется с вами в ближайшее время."
            )
        
        await update.message.reply_text(response)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback-запросов от inline кнопок"""
        query = update.callback_query
        await query.answer()  # Отправляем уведомление, что запрос обработан
        
        try:
            data = json.loads(query.data)
            action = data.get("action")
            
            if action == "confirm_interview":
                position = data.get("position")
                time = data.get("time")
                response = (
                    f"Отлично! Вы подтвердили собеседование на позицию {position} в {time}.\n\n"
                    f"Мы отправим вам дополнительную информацию ближе к дате собеседования."
                )
                await query.edit_message_text(text=response)
                
                # Здесь должно быть обновление статуса в системе
                
            elif action == "reschedule_interview":
                position = data.get("position")
                response = (
                    f"Пожалуйста, укажите удобное для вас время собеседования на позицию {position}.\n\n"
                    f"Формат: ДД.ММ.ГГГГ ЧЧ:ММ"
                )
                await query.edit_message_text(text=response)
                
                # Переводим кандидата в режим ожидания нового времени
                active_sessions[query.from_user.id] = {"action": "waiting_for_reschedule", "position": position}
                
            elif action == "vacancies":
                # Получение списка вакансий из базы данных в реальном приложении
                vacancies = [
                    {"title": "Software Developer", "id": "sd001"},
                    {"title": "UI/UX Designer", "id": "ux002"},
                    {"title": "Project Manager", "id": "pm003"}
                ]
                
                keyboard = []
                for vacancy in vacancies:
                    keyboard.append([InlineKeyboardButton(
                        vacancy["title"], 
                        callback_data=json.dumps({"action": "vacancy_details", "id": vacancy["id"]})
                    )])
                
                keyboard.append([InlineKeyboardButton("Назад", callback_data='{"action":"back_to_main"}')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                response = "Выберите вакансию для получения подробной информации:"
                await query.edit_message_text(text=response, reply_markup=reply_markup)
                
            elif action == "vacancy_details":
                vacancy_id = data.get("id")
                # В реальном приложении здесь будет запрос к базе данных
                
                if vacancy_id == "sd001":
                    details = (
                        "<b>Software Developer</b>\n\n"
                        "<b>Требования:</b>\n"
                        "• Опыт работы от 2 лет\n"
                        "• Знание JavaScript, React\n"
                        "• Опыт работы с REST API\n\n"
                        "<b>Условия:</b>\n"
                        "• Полный рабочий день\n"
                        "• Удаленная работа\n"
                        "• Конкурентная зарплата"
                    )
                else:
                    details = f"Подробная информация о вакансии {vacancy_id}"
                
                keyboard = [
                    [InlineKeyboardButton("Откликнуться", callback_data=json.dumps({"action": "apply", "id": vacancy_id}))],
                    [InlineKeyboardButton("Назад к списку", callback_data='{"action":"vacancies"}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text=details, reply_markup=reply_markup, parse_mode='HTML')
                
            elif action == "apply":
                vacancy_id = data.get("id")
                response = (
                    f"Чтобы откликнуться на эту вакансию, отправьте свое резюме в формате PDF или DOC.\n\n"
                    f"После получения резюме мы свяжемся с вами для дальнейших шагов."
                )
                
                keyboard = [[InlineKeyboardButton("Назад", callback_data='{"action":"vacancy_details","id":"' + vacancy_id + '"}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text=response, reply_markup=reply_markup)
                
                # Установка статуса ожидания резюме
                active_sessions[query.from_user.id] = {"action": "waiting_for_resume", "vacancy_id": vacancy_id}
                
            elif action == "back_to_main":
                # Возврат к главному меню
                await self.start_command(update, context)
                await query.delete_message()
            
            elif action == "faq":
                faq_text = (
                    "<b>Часто задаваемые вопросы:</b>\n\n"
                    "<b>Q: Как происходит процесс найма?</b>\n"
                    "A: Процесс найма включает отправку резюме, первичное собеседование, техническое интервью и финальное собеседование.\n\n"
                    "<b>Q: Сколько времени занимает рассмотрение резюме?</b>\n"
                    "A: Обычно мы рассматриваем резюме в течение 3-5 рабочих дней.\n\n"
                    "<b>Q: Проводите ли вы собеседования удаленно?</b>\n"
                    "A: Да, мы проводим собеседования как очно, так и удаленно через Zoom или Teams."
                )
                
                keyboard = [[InlineKeyboardButton("Назад", callback_data='{"action":"back_to_main"}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text=faq_text, reply_markup=reply_markup, parse_mode='HTML')
                
            elif action == "application_status":
                # В реальном приложении здесь будет запрос к базе данных
                status_text = (
                    "<b>Статус вашего отклика:</b>\n\n"
                    "Позиция: Software Developer\n"
                    "Статус: На рассмотрении\n"
                    "Дата отклика: 15.05.2025\n\n"
                    "Мы свяжемся с вами в ближайшее время для уточнения деталей."
                )
                
                keyboard = [[InlineKeyboardButton("Назад", callback_data='{"action":"back_to_main"}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка при обработке callback: {e}")
            await query.edit_message_text("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз.")

# Функция для запуска бота
async def run_bot(token: str, webhook_url: Optional[str] = None):
    """
    Запуск Telegram бота
    
    Args:
        token: API токен Telegram бота
        webhook_url: URL для настройки webhook (опционально)
    """
    bot_service = TelegramBotService(token, webhook_url)
    success = await bot_service.setup()
    
    if success:
        # В реальном приложении здесь будет логика для поддержания бота в рабочем состоянии
        # и обработки остановки сервиса
        try:
            # Для тестирования
            if not webhook_url:
                await asyncio.sleep(3600)  # Работает 1 час
                await bot_service.stop()
        except (KeyboardInterrupt, SystemExit):
            await bot_service.stop()
    
    return bot_service

# Для тестирования
if __name__ == "__main__":
    import os
    # Получение токена из переменных окружения
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        asyncio.run(run_bot(token))
    else:
        print("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
