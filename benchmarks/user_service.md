# user-service benchmark task

The workspace contains `users.json` with sample user records.

Read users.json, then:

1. Create `user_service.py` with a `User` dataclass and three functions:
   - `load_users(path: str) -> list[User]` — read and parse the JSON file
   - `find_user(users: list[User], name: str) -> User | None` — lookup by name
   - `active_users(users: list[User]) -> list[User]` — filter to active users
2. Create `test_user_service.py` with tests for all three functions.
