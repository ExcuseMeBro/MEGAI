// Live shape check for the gate's route question: the request the tool-call gate
// builds, answered by the real Jev endpoint. Not part of the offline suite — it needs
// a TypeSafe key (environment or the macOS keychain) and makes one bounded call with
// synthetic state only, no repository text and no personal data.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { platform } from 'node:os';

const ENDPOINT = process.env.TYPESAFE_ENDPOINT || 'https://api.typesafe.ai/v1/systemone';

function apiKey() {
  const provided = process.env.TYPESAFE_API_KEY?.trim();
  if (provided) return provided;
  if (platform() !== 'darwin') return undefined;
  try {
    return execFileSync('security', ['find-generic-password', '-s', 'typesafe.ai', '-w'],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 5_000 }).trim() || undefined;
  } catch {
    return undefined;
  }
}

const key = apiKey();
assert.ok(key, 'no TypeSafe key: set TYPESAFE_API_KEY or store one with '
  + '`security add-generic-password -s typesafe.ai -a "$USER" -w`');

const criteria = {
  as_written: 'run this exact bash call as written',
  'skill:megai': 'focused verification for a flaky test',
};
const questions = {
  object: {
    type: 'noul',
    instructions: 'There is a concrete reason this exact bash call must not run as written.',
  },
  route: {
    type: 'choice',
    instructions: 'The smallest correct next move for what the user asked, from the listed skills and MCP '
      + 'tools: answer `as_written` when this exact bash call is already that move, otherwise the named '
      + 'move is a better next step than the call as written.',
    criteria,
  },
};
const state = [
  'Judge whether the next tool call from the model should run exactly as it is.',
  'What the session is working on:\nfix the flaky parser test',
  'Working directory: /tmp/jev-route-live',
  'Tool call: bash({"command":"node tools/run-flaky.mjs"})',
  'Skills and MCP tools installed here that this call could use instead:\n'
    + Object.entries(criteria).filter(([label]) => label !== 'as_written')
      .map(([label, text]) => `- ${label}: ${text}`).join('\n'),
].join('\n\n');

const response = await fetch(ENDPOINT, {
  method: 'POST',
  headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
  body: JSON.stringify({ state, model: 'jev-latest', questions }),
  signal: AbortSignal.timeout(30_000),
});
assert.equal(response.status, 200, `Jev returned HTTP ${response.status}`);
const payload = await response.json();
const answers = payload?.answers;
const route = answers?.route;
assert.ok(route, 'the response must carry the route answer');
assert.equal(typeof route.choice, 'string', 'the route answer must pick a label');
assert.ok(criteria[route.choice], `route choice "${route.choice}" is not one of the offered labels`);
assert.equal(typeof answers.object?.noul, 'number', 'the objection answer must be a probability');
console.log(`PASS: the live Jev endpoint answered the gate's route request (model ${payload.model}, `
  + `route ${route.choice}, object ${answers.object.noul})`);
