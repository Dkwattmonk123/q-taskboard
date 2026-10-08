from rest_framework import serializers
from users.serializers import UserSerializer
from .models import Project, Membership, Task, Comment


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.SerializerMethodField()
    project_id = serializers.SerializerMethodField()
    created_by_id = serializers.SerializerMethodField()

    def get_assignee_id(self, obj):
        return str(obj.assignee_id) if obj.assignee_id else None

    def get_project_id(self, obj):
        return str(obj.project_id)

    def get_created_by_id(self, obj):
        return str(obj.created_by_id)

    class Meta:
        model = Task
        fields = [
            'id', 'project_id', 'title', 'description', 'status',
            'assignee_id', 'created_by_id', 'position', 'created_at', 'updated_at', 'assignee',
        ]


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'role', 'user']


class ProjectDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    owner_id = serializers.SerializerMethodField()
    memberships = MembershipSerializer(many=True, read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)

    def get_owner_id(self, obj):
        return str(obj.owner_id)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner_id', 'owner', 'memberships', 'tasks', 'created_at', 'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'body', 'author', 'created_at']
