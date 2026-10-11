You are a coding agent. You have just inherited this repository: AfterHours v1, a small FastAPI + SQLite festival app. Nobody who wrote the ticket code is around any more. The repository is at:
<repo>

Work only inside that folder. Use this Python (dependencies are already installed; do not install anything): <venv>/bin/python

We are about to migrate the tickets table (single-day tickets will become multi-day festival passes), so first we need a safety net.

1. Explain, in plain words for a new teammate, what v1/tickets.py does: selling, reading, changing day, and scanning at the gate. Keep it under 250 words.
2. Write characterization tests for the ticket API in tests/test_tickets_characterization.py, using the fixtures in tests/conftest.py (`client`, and `clock` to set the time the app sees). They should pin down what the code does today, so that we notice if the migration changes it. Do not change any file under v1/.
3. Run `<venv>/bin/python -m pytest -q -p no:cacheprovider` from the repository folder and make sure everything passes.

Reply with the explanation, a short summary of what the tests pin down, and anything that looked surprising.
