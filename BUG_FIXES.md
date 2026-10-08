### Bugs I fixed

**1. SQL injection in task search (the big one)**

`GET /api/projects/:id/tasks?q=...` was building its SQL with an f-string and pasting the search text straight into the query. Typing a single `'` into the search box crashed the endpoint with a 500. A crafted `UNION SELECT` could read other tables, including user emails and password hashes.

I removed the raw SQL completely and used the Django ORM instead (`Q(title__icontains=q) | Q(description__icontains=q)`). The ORM sends the search text as a parameter, so it can never become part of the SQL. A nice side effect is that search results now come back in the same shape as the normal task list. Before, the search path returned raw database rows, which didn't match.

Tests: `test_search_is_not_sql_injectable` sends a lone quote and a UNION payload and checks that nothing leaks. `test_search_matches_title` checks that search still works.

**2. Anyone logged in could edit any task**

`PATCH /api/tasks/:id` looked up the task and saved the changes without checking who was asking. Any logged-in user who had (or guessed) a task ID could rename or move tasks in projects they don't belong to. `DELETE` on the same endpoint already had the right check, so I copied it over. You now need to be a member of the project, and viewers can't edit. Both cases return `403`.

Test: `test_patch_task_requires_edit_membership`.