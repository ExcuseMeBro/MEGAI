// Advisory for agent-issued bash calls: only common direct shell forms are parsed.
// This is not an OS sandbox; user_bash, other agents and shell indirection are not intercepted.
function commands(input) {
  const result = [];
  let words = [], word = '', quote = '', active = false;
  const flushWord = () => { if (active) { words.push(word); word = ''; active = false; } };
  const flushCommand = () => { flushWord(); if (words.length) result.push(words); words = []; };
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (char === '\\' && quote !== "'" && i + 1 < input.length) {
      word += input[++i]; active = true; continue;
    }
    if (quote) {
      if (char === quote) quote = '';
      else word += char;
      continue;
    }
    if (char === "'" || char === '"') { quote = char; active = true; continue; }
    if (/\s/.test(char)) { flushWord(); if (char === '\n') flushCommand(); continue; }
    if (';&|'.includes(char)) { flushCommand(); continue; }
    word += char; active = true;
  }
  flushCommand();
  return result;
}

function broadRoot(path) {
  return /^(?:\.|\.\.|\/|~\/?|~\/(?:PROJECTS|Documents)\/?|\$(?:HOME|\{HOME\})(?:\/(?:PROJECTS|Documents))?\/?|\/(?:Users|home)\/[^/]+(?:\/(?:PROJECTS|Documents))?\/?)$/.test(path);
}

function broadRecursiveGrep(words) {
  if (words[0] !== 'grep') return false;
  let recursive = false, i = 1;
  for (; i < words.length; i++) {
    const option = words[i];
    if (option === '--') { i++; break; }
    if (!option.startsWith('-') || option === '-') break;
    if (option === '--recursive' || /^-[a-zA-Z]*[rR][a-zA-Z]*$/.test(option)) recursive = true;
    // A pattern argument to -e/-f is not a search root.
    if (option === '-e' || option === '-f' || option === '--regexp' || option === '--file') i++;
  }
  // With -e/-f the first non-option argument is a path; otherwise it is a pattern.
  const hasPatternOption = words.slice(1, i).some(arg => ['-e', '-f', '--regexp', '--file'].includes(arg));
  const roots = words.slice(i + (hasPatternOption ? 0 : 1));
  return recursive && roots.some(broadRoot);
}

export function guardBroadSearch(event) {
  if (event?.toolName !== 'bash' || typeof event.input?.command !== 'string') return undefined;
  if (!commands(event.input.command).some(broadRecursiveGrep)) return undefined;
  return { block: true, reason: 'Broad recursive grep discovery blocked before traversal. Use tgrep with a bounded path (or native rg for exhaustive/hidden/ignored coverage); scope first, not grep -v after scanning.' };
}
