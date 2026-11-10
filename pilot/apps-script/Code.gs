/**
 * Sheet-bound controls for the ICPC Contest Archive pilot.
 *
 * This code never calls GitHub. GitHub Actions polls the Sheet every ten
 * minutes. The installed triggers only mint stable IDs and signed approvals.
 * Configure these Script Properties before installing the triggers:
 *
 *   PILOT_APPROVAL_HMAC_SECRET  random 32+ byte secret (also a GitHub secret)
 *   PILOT_REVIEWERS             comma-separated reviewer email allowlist
 *   PILOT_SHEET_NAME            optional; defaults to "Form Responses 1"
 */

const DEFAULT_SHEET_NAME = 'Form Responses 1';

function installPilotTriggers() {
  const spreadsheet = SpreadsheetApp.getActive();
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (['pilotOnFormSubmit', 'pilotOnEdit'].includes(trigger.getHandlerFunction())) {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  ScriptApp.newTrigger('pilotOnFormSubmit')
    .forSpreadsheet(spreadsheet)
    .onFormSubmit()
    .create();
  ScriptApp.newTrigger('pilotOnEdit')
    .forSpreadsheet(spreadsheet)
    .onEdit()
    .create();
}

function pilotOnFormSubmit(event) {
  const sheet = event.range.getSheet();
  if (sheet.getName() !== pilotSheetName_()) return;
  const row = event.range.getRow();
  const headers = pilotHeaders_(sheet);
  const values = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getDisplayValues()[0];
  // A repeated submission for the same source receives the same ID. This is
  // deliberate: retries and duplicate Form responses converge on one branch
  // and one PR instead of racing each other.
  const immutable = [
    SpreadsheetApp.getActive().getId(),
    values[headers['series_id'] - 1] || '',
    values[headers['contest_id'] - 1] || '',
    String(values[headers['source_url'] - 1] || '').trim().replace(/\/$/, ''),
  ].join('\u001f');
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, immutable)
    .map(byte => ('0' + ((byte + 256) % 256).toString(16)).slice(-2))
    .join('');
  pilotSet_(sheet, row, headers, 'submission_id', digest.slice(0, 24));
  pilotSet_(sheet, row, headers, 'review_status', 'SUBMITTED');
  pilotSet_(sheet, row, headers, 'publication_status', 'PENDING_REVIEW');
  pilotSet_(sheet, row, headers, 'updated_at', new Date().toISOString());
}

function pilotOnEdit(event) {
  const sheet = event.range.getSheet();
  if (sheet.getName() !== pilotSheetName_() || event.range.getRow() === 1) return;
  const headers = pilotHeaders_(sheet);
  if (event.range.getColumn() !== headers['review_status']) return;
  const status = String(event.value || '').trim().toUpperCase();
  if (status !== 'APPROVED') return;

  const row = event.range.getRow();
  const reviewer = String(Session.getActiveUser().getEmail() || '').trim().toLowerCase();
  const allowed = String(PropertiesService.getScriptProperties().getProperty('PILOT_REVIEWERS') || '')
    .split(',').map(v => v.trim().toLowerCase()).filter(Boolean);
  const secret = PropertiesService.getScriptProperties().getProperty('PILOT_APPROVAL_HMAC_SECRET');
  const submissionId = pilotGet_(sheet, row, headers, 'submission_id');
  const baseBlobSha = pilotGet_(sheet, row, headers, 'base_blob_sha');

  if (!reviewer || !allowed.includes(reviewer) || !secret || !submissionId || !baseBlobSha) {
    pilotSet_(sheet, row, headers, 'review_status', 'SUBMITTED');
    pilotSet_(sheet, row, headers, 'approval_token', '');
    pilotSet_(sheet, row, headers, 'error',
      'Approval denied: authorized reviewer, HMAC secret, submission ID, and base revision are required.');
    return;
  }

  const payload = [
    submissionId,
    baseBlobSha,
    reviewer,
    pilotGet_(sheet, row, headers, 'series_id'),
    pilotGet_(sheet, row, headers, 'contest_id'),
    pilotGet_(sheet, row, headers, 'source_url'),
    pilotGet_(sheet, row, headers, 'roles'),
    pilotGet_(sheet, row, headers, 'judge'),
    pilotGet_(sheet, row, headers, 'note'),
  ].join('|');
  const signature = Utilities.computeHmacSha256Signature(payload, secret)
    .map(byte => ('0' + ((byte + 256) % 256).toString(16)).slice(-2))
    .join('');
  pilotSet_(sheet, row, headers, 'reviewed_by', reviewer);
  pilotSet_(sheet, row, headers, 'approval_token', signature);
  pilotSet_(sheet, row, headers, 'publication_status', 'APPROVED');
  pilotSet_(sheet, row, headers, 'error', '');
  pilotSet_(sheet, row, headers, 'updated_at', new Date().toISOString());
}

function pilotSheetName_() {
  return PropertiesService.getScriptProperties().getProperty('PILOT_SHEET_NAME') || DEFAULT_SHEET_NAME;
}

function pilotHeaders_(sheet) {
  const names = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getDisplayValues()[0];
  return names.reduce((map, name, index) => { map[String(name).trim()] = index + 1; return map; }, {});
}

function pilotGet_(sheet, row, headers, name) {
  if (!headers[name]) throw new Error('Missing required column: ' + name);
  return String(sheet.getRange(row, headers[name]).getDisplayValue() || '').trim();
}

function pilotSet_(sheet, row, headers, name, value) {
  if (!headers[name]) throw new Error('Missing required column: ' + name);
  sheet.getRange(row, headers[name]).setValue(value);
}
