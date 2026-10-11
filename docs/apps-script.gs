/**
 * Приём заявок с сайта «Собери ИИ-команду за выходные»:
 * каждая заявка пишется в Google Таблицу и приходит сообщением в Telegram-бот.
 *
 * Как подключить (один раз):
 * 1. Откройте таблицу «Регистрации — Собери ИИ-команду за выходные».
 * 2. Расширения → Apps Script. Удалите всё в редакторе и вставьте этот код.
 * 3. Впишите BOT_TOKEN и CHAT_ID ниже (токен не публикуйте на сайте и в GitHub). Сохраните.
 * 4. Начать развёртывание → Управление развёртываниями → карандаш → Версия: «Новая версия» → Развернуть.
 *    Первый раз: Новое развёртывание → «Веб-приложение», выполнять как «Я», доступ «Все».
 */
var BOT_TOKEN = 'ВСТАВЬТЕ_ТОКЕН_БОТА';
var CHAT_ID = 'ВСТАВЬТЕ_CHAT_ID';

var HEADERS = ['Дата и время', 'Имя', 'Телефон', 'Почта', 'Тариф', 'Согласие ПД', 'Согласие на рассылку', 'Событие', 'Страница'];

function doPost(e) {
  var d = {};
  try { d = JSON.parse((e && e.postData && e.postData.contents) || '{}'); } catch (err) {}
  var saved = false, error = '';

  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold').setBackground('#FFBA09');
      sheet.setFrozenRows(1);
    }
    sheet.appendRow([new Date(), d.name || '', d.phone || '', d.email || '', d.tariff || '',
      d.consent_data || '', d.consent_mailing || '', d.event || '', d.page || '']);
    saved = true;
  } catch (err) {
    error = String(err);
  } finally {
    try { lock.releaseLock(); } catch (err) {}
  }

  // Уведомление в Telegram отправляется даже если запись в таблицу не удалась
  notify(d, saved, error);

  return ContentService.createTextOutput(JSON.stringify({ok: saved, error: error}))
    .setMimeType(ContentService.MimeType.JSON);
}

function notify(d, saved, error) {
  if (BOT_TOKEN.indexOf('ВСТАВЬТЕ') === 0 || CHAT_ID.indexOf('ВСТАВЬТЕ') === 0) return;
  var vip = String(d.tariff || '').indexOf('VIP') === 0;
  var lines = [
    (vip ? '💛 Новая заявка · VIP' : '💙 Новая заявка · бесплатно'),
    '',
    '👤 ' + (d.name || 'без имени'),
    '📞 ' + (d.phone || 'нет телефона'),
    '✉️ ' + (d.email || 'нет почты'),
    '🎟 ' + (d.tariff || 'тариф не указан'),
    '🕒 ' + Utilities.formatDate(new Date(), 'Europe/Moscow', 'dd.MM.yyyy HH:mm') + ' МСК'
  ];
  if (vip) lines.push('', 'Человек ушёл на страницу оплаты. Проверь, оплатил ли.');
  if (!saved) lines.push('', '⚠️ В таблицу не записалось: ' + error);
  try {
    UrlFetchApp.fetch('https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage', {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify({chat_id: CHAT_ID, text: lines.join('\n'), disable_web_page_preview: true}),
      muteHttpExceptions: true
    });
  } catch (err) {}
}

function doGet() {
  return ContentService.createTextOutput('ok');
}

// Запустите вручную из редактора, чтобы проверить бота: придёт тестовое сообщение
function testNotify() {
  notify({name: 'Тест', phone: '+7 (900) 000-00-00', email: 'test@test.ru', tariff: 'Бесплатно 0 ₽'}, true, '');
}
