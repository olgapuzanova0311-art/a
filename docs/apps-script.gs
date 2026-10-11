/**
 * Приём заявок с сайта «Собери ИИ-команду за выходные» в Google Таблицу.
 *
 * Как подключить (2 минуты, один раз):
 * 1. Откройте таблицу «Регистрации — Собери ИИ-команду за выходные».
 * 2. Расширения → Apps Script. Удалите всё в редакторе и вставьте этот код. Сохраните.
 * 3. Начать развёртывание → Новое развёртывание → тип «Веб-приложение».
 *    Выполнять как: Я. У кого есть доступ: Все. Нажмите «Развернуть» и разрешите доступ.
 * 4. Скопируйте URL веб-приложения (заканчивается на /exec) и вставьте его в index.html
 *    вместо ВСТАВЬТЕ_URL_НОВОГО_СКРИПТА (или пришлите его Claude).
 */
var HEADERS = ['Дата и время', 'Имя', 'Телефон', 'Почта', 'Тариф', 'Согласие ПД', 'Согласие на рассылку', 'Событие', 'Страница'];

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold').setBackground('#FFBA09');
      sheet.setFrozenRows(1);
    }
    var d = JSON.parse(e.postData.contents || '{}');
    sheet.appendRow([
      new Date(),
      d.name || '',
      d.phone || '',
      d.email || '',
      d.tariff || '',
      d.consent_data || '',
      d.consent_mailing || '',
      d.event || '',
      d.page || ''
    ]);
    return ContentService.createTextOutput(JSON.stringify({ok: true})).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: String(err)})).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return ContentService.createTextOutput('ok');
}
