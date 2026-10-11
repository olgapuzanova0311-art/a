/**
 * Приём заявок с сайта и бота «Собери ИИ-команду за выходные»:
 * каждая заявка пишется в Google Таблицу, приходит сообщением в Telegram-бот,
 * а участнику один раз уходит письмо с подарками, каналами и VIP.
 *
 * Как подключить (один раз):
 * 1. Откройте таблицу «Регистрации — Собери ИИ-команду за выходные».
 * 2. Расширения → Apps Script. Удалите всё в редакторе и вставьте этот код.
 * 3. Впишите BOT_TOKEN ниже (токен не публикуйте на сайте и в GitHub). Нажмите «Старт» в своём боте. Сохраните.
 * 4. Начать развёртывание → Управление развёртываниями → карандаш → Версия: «Новая версия» → Развернуть.
 *    Первый раз: Новое развёртывание → «Веб-приложение», выполнять как «Я», доступ «Все».
 * 5. Письма: выберите функцию testEmail → «Выполнить» → разрешите доступ к почте.
 *    Проверьте письмо у себя во входящих. После этого снова сделайте шаг 4 (новая версия).
 *    Лимит Gmail: 100 писем в сутки (Google Workspace: 1 500). Если лимит кончился, бот пришлёт предупреждение.
 */
var BOT_TOKEN = 'ВСТАВЬТЕ_ТОКЕН_БОТА';
// CHAT_ID можно не заполнять: напишите боту «Старт», и скрипт сам запомнит ваш чат при первой заявке
var CHAT_ID = '';

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
  sendWelcomeEmail(d);

  return ContentService.createTextOutput(JSON.stringify({ok: saved, error: error}))
    .setMimeType(ContentService.MimeType.JSON);
}

function notify(d, saved, error) {
  if (BOT_TOKEN.indexOf('ВСТАВЬТЕ') === 0) return;
  var chatId = getChatId();
  if (!chatId) return;
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
      payload: JSON.stringify({chat_id: chatId, text: lines.join('\n'), disable_web_page_preview: true}),
      muteHttpExceptions: true
    });
  } catch (err) {}
}

// Находит чат владельца: из CHAT_ID, из сохранённых свойств или из последнего «Старт» в боте
function getChatId() {
  if (CHAT_ID) return CHAT_ID;
  var props = PropertiesService.getScriptProperties();
  var saved = props.getProperty('CHAT_ID');
  if (saved) return saved;
  try {
    var r = JSON.parse(UrlFetchApp.fetch('https://api.telegram.org/bot' + BOT_TOKEN + '/getUpdates', {muteHttpExceptions: true}).getContentText());
    var res = (r && r.result) || [];
    for (var i = res.length - 1; i >= 0; i--) {
      var m = res[i].message;
      if (m && m.chat && m.chat.type === 'private') {
        props.setProperty('CHAT_ID', String(m.chat.id));
        return String(m.chat.id);
      }
    }
  } catch (err) {}
  return '';
}

// ---------- Письмо участнику ----------
var LINKS = {
  tg: 'https://t.me/+cjxoa6weO0czOWRi',
  max: 'https://max.ru/join/PzpWaFYZ8q-BaFvU1pUAVlj1jycdgZgt9afSZqP9sQA',
  vip: 'https://puzanovva.tech/page194999',
  bot: 'https://t.me/aikomandaweb_bot',
  claude: 'https://docs.google.com/document/d/1VLKrNijzr9tmGaOj9c1zO_zo_KEs_KzscmwXtIxw23A/edit',
  karta: 'https://agent.olgapuzanovva.ru/gifts/karta-zadach-450c6f.html',
  prompts: 'https://agent.olgapuzanovva.ru/gifts/15-promptov-3b0c21.html',
  cal1: 'https://agent.olgapuzanovva.ru/d1/',
  cal2: 'https://agent.olgapuzanovva.ru/d2/'
};

// Отправляет письмо один раз на каждую почту, даже если человек зарегистрировался и на сайте, и в боте
function sendWelcomeEmail(d) {
  var email = String(d.email || '').trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) return;
  var props = PropertiesService.getScriptProperties();
  var key = 'mail_' + email;
  if (props.getProperty(key)) return;
  if (MailApp.getRemainingDailyQuota() < 1) {
    notifyText('⚠️ Письмо не отправлено: закончился суточный лимит Gmail. Почта: ' + email);
    return;
  }
  try {
    var vip = String(d.tariff || '').indexOf('VIP') === 0;
    MailApp.sendEmail({
      to: email,
      name: 'Ольга Пузанова',
      subject: 'Ты в списке! Подарки и ссылки на интенсив 17–18 октября',
      htmlBody: welcomeHtml(d.name, vip)
    });
    props.setProperty(key, new Date().toISOString());
  } catch (err) {
    notifyText('⚠️ Письмо на ' + email + ' не отправилось: ' + err);
  }
}

function welcomeHtml(name, vip) {
  var hi = name ? esc(name) + ', привет' : 'Привет';
  var btn = function (href, text, bg, color) {
    return '<a href="' + href + '" style="display:inline-block;margin:4px 6px 4px 0;padding:14px 22px;border-radius:12px;background:' + bg +
      ';color:' + color + ';font-weight:700;text-decoration:none">' + text + '</a>';
  };
  var li = function (href, text) { return '<li style="margin:6px 0"><a href="' + href + '" style="color:#1009F6">' + text + '</a></li>'; };
  return '<div style="font-family:Arial,sans-serif;font-size:16px;line-height:1.55;color:#141414;max-width:560px;margin:0 auto;padding:16px">' +
    '<p>' + hi + '! Это Оля 👋</p>' +
    '<p>Ты зарегистрирован(а) на онлайн-интенсив <b>«Собери ИИ-команду за выходные»</b>.</p>' +
    '<p>📅 <b>Суббота, 17 октября, 14:00 МСК.</b> Собираем твоего первого ИИ-агента.<br>' +
    '📅 <b>Воскресенье, 18 октября, 14:00 МСК.</b> Запускаем контент-завод.</p>' +
    '<p>Добавь оба дня в календарь: <a href="' + LINKS.cal1 + '" style="color:#1009F6">день 1</a> и <a href="' + LINKS.cal2 + '" style="color:#1009F6">день 2</a>.</p>' +
    '<h3 style="margin:24px 0 8px">1. Вступи в канал интенсива</h3>' +
    '<p>Туда придут ссылки на эфиры и новые подарки. Выбери, где удобнее 👇</p>' +
    '<p>' + btn(LINKS.tg, 'Канал в Telegram', '#1009F6', '#ffffff') + btn(LINKS.max, 'Канал в MAX', '#1009F6', '#ffffff') + '</p>' +
    '<h3 style="margin:24px 0 8px">2. Держи подарки 🎁</h3><ul style="padding-left:20px">' +
    li(LINKS.claude, 'Пошаговая инструкция: как оплатить и настроить Claude') +
    li(LINKS.karta, 'Карта задач для ИИ-агентов') +
    li(LINKS.prompts, '15 стартовых промптов') + '</ul>' +
    '<p>Ещё больше подарков и розыгрыш iPhone 17 в боте <a href="' + LINKS.bot + '" style="color:#1009F6">@aikomandaweb_bot</a>.</p>' +
    '<h3 style="margin:24px 0 8px">3. VIP-билет за 490 ₽</h3>' +
    (vip ? '<p>Ты выбрал(а) VIP. Если оплата не прошла, её можно завершить по кнопке ниже.</p>'
         : '<p>Запись обоих дней, дополнительные бонусы и грант на 10 000 ₽ на флагманское обучение.</p>') +
    '<p>' + btn(LINKS.vip, vip ? 'Завершить оплату VIP' : 'Взять VIP за 490 ₽', '#FFBA09', '#141414') + '</p>' +
    '<p style="margin-top:24px">До встречи в эфире!<br>Ольга Пузанова</p>' +
    '<p style="font-size:12px;color:#888">Ты получил(а) это письмо, потому что зарегистрировался(ась) на интенсив на agent.olgapuzanovva.ru или в боте @aikomandaweb_bot.</p>' +
    '</div>';
}

function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }

function notifyText(text) {
  if (BOT_TOKEN.indexOf('ВСТАВЬТЕ') === 0) return;
  var chatId = getChatId();
  if (!chatId) return;
  try {
    UrlFetchApp.fetch('https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage', {
      method: 'post', contentType: 'application/json',
      payload: JSON.stringify({chat_id: chatId, text: text}), muteHttpExceptions: true
    });
  } catch (err) {}
}

// Запустите вручную: письмо придёт на почту владельца скрипта
function testEmail() {
  MailApp.sendEmail({to: Session.getEffectiveUser().getEmail(), name: 'Ольга Пузанова',
    subject: '[Тест] Ты в списке! Подарки и ссылки на интенсив 17–18 октября', htmlBody: welcomeHtml('Оля', false)});
}

function doGet() {
  return ContentService.createTextOutput('ok');
}

// Запустите вручную из редактора, чтобы проверить бота: придёт тестовое сообщение
function testNotify() {
  notify({name: 'Тест', phone: '+7 (900) 000-00-00', email: 'test@test.ru', tariff: 'Бесплатно 0 ₽'}, true, '');
}
