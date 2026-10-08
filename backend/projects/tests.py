import pytest
from rest_framework.test import APIClient
from users.models import User
from projects.models import Project, Membership, Task
from projects.airtable_client import export_tasks
from projects.airtable_mock import MockTable


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='meera@taskboard.dev', name='Meera Iyer', password='password123')


@pytest.fixture
def auth_client(client, user):
    response = client.post('/api/auth/login', {
        'email': 'meera@taskboard.dev',
        'password': 'password123',
    }, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
    return client


@pytest.mark.django_db
class TestProjects:
    def test_create_project(self, auth_client, user):
        response = auth_client.post('/api/projects', {'name': 'My Project'}, format='json')
        assert response.status_code == 201
        assert response.data['project']['name'] == 'My Project'

    def test_list_only_returns_member_projects(self, auth_client, user):
        p1 = Project.objects.create(name='Mine', owner=user)
        Membership.objects.create(user=user, project=p1, role='admin')
        other = User.objects.create_user(email='other@example.com', name='Other', password='password123')
        p2 = Project.objects.create(name='Not Mine', owner=other)
        Membership.objects.create(user=other, project=p2, role='admin')

        response = auth_client.get('/api/projects')
        assert response.status_code == 200
        names = [p['name'] for p in response.data['projects']]
        assert 'Mine' in names
        assert 'Not Mine' not in names

    def test_get_project_detail(self, auth_client, user):
        project = Project.objects.create(name='My Project', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')

        response = auth_client.get(f'/api/projects/{project.id}')
        assert response.status_code == 200
        assert response.data['project']['name'] == 'My Project'

    def test_non_member_cannot_view_project(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='Private', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.get(f'/api/projects/{project.id}')
        assert response.status_code == 403


@pytest.mark.django_db
class TestTasks:
    def test_create_task(self, auth_client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')

        response = auth_client.post(f'/api/projects/{project.id}/tasks', {'title': 'Do a thing'}, format='json')
        assert response.status_code == 201
        assert response.data['task']['title'] == 'Do a thing'

    def test_viewers_cannot_create_tasks(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        Membership.objects.create(user=user, project=project, role='viewer')

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.post(f'/api/projects/{project.id}/tasks', {'title': 'A task'}, format='json')
        assert response.status_code == 403

    def test_delete_task_requires_membership(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        task = Task.objects.create(project=project, title='A task', created_by=owner)

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.delete(f'/api/tasks/{task.id}')
        assert response.status_code == 403

    def test_search_is_not_sql_injectable(self, auth_client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')
        Task.objects.create(project=project, title='Record demo video',
                            created_by=user, status='todo')
        # a lone quote must NOT 500
        resp = auth_client.get(f'/api/projects/{project.id}/tasks', {'q': "'"})
        assert resp.status_code == 200
        # a UNION payload must leak no user data
        payload = ("x') UNION SELECT id,id,email,password,'todo',NULL::uuid,"
                   "id,0,created_at,updated_at FROM users--")
        resp = auth_client.get(f'/api/projects/{project.id}/tasks', {'q': payload})
        assert resp.status_code == 200
        titles = [t['title'] for t in resp.data['tasks']]
        assert not any('@' in t for t in titles)

    def test_search_matches_title(self, auth_client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')
        Task.objects.create(project=project, title='Record demo video', created_by=user)
        Task.objects.create(project=project, title='Draft press release', created_by=user)
        resp = auth_client.get(f'/api/projects/{project.id}/tasks', {'q': 'demo'})
        assert resp.status_code == 200
        assert [t['title'] for t in resp.data['tasks']] == ['Record demo video']

    def test_patch_task_requires_edit_membership(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        task = Task.objects.create(project=project, title='A task', created_by=owner)
        # meera is NOT a member of this project
        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")
        r = client.patch(f'/api/tasks/{task.id}', {'title': 'HACK'}, format='json')
        assert r.status_code == 403


@pytest.mark.django_db
class TestComments:
    def _login(self, client, email):
        r = client.post('/api/auth/login', {'email': email, 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['token']}")

    def test_member_can_post_and_list_chronologically(self, client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')
        task = Task.objects.create(project=project, title='T', created_by=user)
        self._login(client, 'meera@taskboard.dev')
        assert client.post(f'/api/tasks/{task.id}/comments', {'body': 'first'}, format='json').status_code == 201
        assert client.post(f'/api/tasks/{task.id}/comments', {'body': 'second'}, format='json').status_code == 201
        resp = client.get(f'/api/tasks/{task.id}/comments')
        assert resp.status_code == 200
        assert [c['body'] for c in resp.data['comments']] == ['first', 'second']

    def test_viewer_can_read_but_not_post(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        Membership.objects.create(user=user, project=project, role='viewer')
        task = Task.objects.create(project=project, title='T', created_by=owner)
        self._login(client, 'meera@taskboard.dev')
        assert client.get(f'/api/tasks/{task.id}/comments').status_code == 200
        assert client.post(f'/api/tasks/{task.id}/comments', {'body': 'x'}, format='json').status_code == 403

    def test_non_member_forbidden(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        task = Task.objects.create(project=project, title='T', created_by=owner)
        self._login(client, 'meera@taskboard.dev')
        assert client.get(f'/api/tasks/{task.id}/comments').status_code == 403
        assert client.post(f'/api/tasks/{task.id}/comments', {'body': 'x'}, format='json').status_code == 403


@pytest.mark.django_db
class TestAirtableExport:
    def _project_with_tasks(self, user, n=3):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')
        tasks = [Task.objects.create(project=project, title=f'T{i}', created_by=user, position=i)
                 for i in range(n)]
        return project, tasks

    def test_exports_all_tasks(self, user, db):
        _, tasks = self._project_with_tasks(user, 3)
        table = MockTable()
        summary = export_tasks(tasks, table=table)
        assert summary['created'] == 3 and summary['failed'] == 0
        assert len(table.all()) == 3

    def test_idempotent_second_run_updates_not_duplicates(self, user, db):
        _, tasks = self._project_with_tasks(user, 3)
        table = MockTable()
        export_tasks(tasks, table=table)
        summary = export_tasks(tasks, table=table)   # run again, same table
        assert summary['created'] == 0 and summary['updated'] == 3
        assert len(table.all()) == 3                   # no duplicates

    def test_partial_failure_does_not_abort(self, user, db):
        _, tasks = self._project_with_tasks(user, 3)
        table = MockTable(fail_ids={str(tasks[1].id)})  # middle task fails permanently
        summary = export_tasks(tasks, table=table)
        assert summary['failed'] == 1 and summary['created'] == 2
        assert len(table.all()) == 2                    # the two good ones landed

    def test_export_authz_viewer_forbidden(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        Membership.objects.create(user=user, project=project, role='viewer')
        r = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['token']}")
        resp = client.post(f'/api/projects/{project.id}/export')
        assert resp.status_code == 403
