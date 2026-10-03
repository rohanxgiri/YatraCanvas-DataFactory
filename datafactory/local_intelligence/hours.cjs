// Optional opening_hours.js adapter. JSON over stdin, no eval or shell strings.
const fs = require('node:fs');
let OpeningHours;
try { OpeningHours = require('opening_hours'); }
catch { process.stdout.write(JSON.stringify({valid:false,status:'UNAVAILABLE',backend:'opening_hours.js'})); process.exit(0); }
try {
  const {schedule} = JSON.parse(fs.readFileSync(0, 'utf8'));
  const parsed = new OpeningHours(schedule);
  const warnings = parsed.getWarnings();
  process.stdout.write(JSON.stringify({valid:warnings.length === 0,status:warnings.length ? 'REVIEW' : 'VALID',backend:'opening_hours.js',warnings,schedule}));
} catch {
  process.stdout.write(JSON.stringify({valid:false,status:'INVALID',backend:'opening_hours.js'}));
}
