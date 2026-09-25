---
description: Run a browser-based review only when explicitly requested
argument-hint: "[page or review focus]"
---
The user explicitly invoked `/rwbrowser`. Review the current task in a browser, limited to ${@:-the relevant changed UI}. Use only a browser already available and authorized for this task; do not install one, start unrelated services, or expand to a full test suite. Report what was actually observed and any access blocker. This command authorizes this bounded browser review only; it does not grant deployment, publishing, or other permissions.
