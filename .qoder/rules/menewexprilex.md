---
trigger: always_on
alwaysApply: true
---
User uses powershell
Use ; to split commands in powershell (no &&)
All responses in chat must be in Russian; in code, use only English.
Write modular code — split into independent modules and functions, and organize by logical areas (e.g., clients, configs, utilities).
Keep code simple, readable, and maintainable, aiming for senior-level quality from the start; avoid temporary hacks or workarounds.
Keep functions short (10–15 lines) and favor self-documenting code — clear names and structure, with comments only for complex or non-obvious parts.
Use short but meaningful names (PEP 8, snake_case).
Avoid over-abstraction — don’t create unnecessary classes or utilities for simple tasks.
Remove unused variables, redundant checks, or unnecessary logic.
Handle all exceptions with proper logging to keep the application functional even during failures.
Optimize asynchronous operations and avoid blocking code.
Follow the DRY (Don’t Repeat Yourself) principle — extract repeated code into separate functions or utilities.
Use type hints (typing) for better readability and IDE support.
Infinite loops (e.g., farming) must be controllable and terminable via signals or external conditions.
Ensure testability — pass dependencies as parameters and avoid global variables.
Keep changes localized to avoid affecting unrelated parts of the code and preserve functionality during refactoring.