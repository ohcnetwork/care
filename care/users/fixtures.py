from .models import (
    Skill,
    User,
    UserSkill,
)

users = [
    {
        "username": "admin",
        "email": "admin@coronasafe.network",
        "password": "admin",
        "first_name": "Admin",
        "last_name": "Admin",
        "user_type": 40,
        "district": "1",
        "age": 20,
        "phone_number": "+919696969696",
        "is_superuser": True,
        "is_staff": True,
    },
    {
        "username": "user",
        "email": "user@coronasafe.network",
        "password": "user",
        "first_name": "Staff",
        "last_name": "User",
        "user_type": 10,
        "district": "1",
        "age": 20,
        "phone_number": "+919696969697",
    },
]

skills = [
    {"name": "Skill 1", "description": "Description 1"},
    {"name": "Skill 2", "description": "Description 2"},
    {"name": "Skill 3", "description": "Description 3"},
]

user_skills = [
    {"user": "admin", "skill": "Skill 1"},
    {"user": "admin", "skill": "Skill 2"},
    {"user": "admin", "skill": "Skill 3"},
    {"user": "user", "skill": "Skill 1"},
]


class UserFixture:
    def __init__(self, user_data, skill_data, user_skill_data):
        self.users = user_data
        self.skills = skill_data
        self.user_skills = user_skill_data

    def load(self):
        for user in self.users:
            if User.objects.filter(username=user["username"]).exists():
                continue
            User.objects.create_user(
                username=user["username"],
                email=user["email"],
                password=user["password"],
                first_name=user["first_name"],
                last_name=user["last_name"],
                user_type=user["user_type"],
                district=user["district"],
                age=user["age"],
                phone_number=user["phone_number"],
                is_superuser=user["is_superuser"],
                is_staff=user["is_staff"],
            )

        for skill in self.skills:
            if Skill.objects.filter(name=skill["name"]).exists():
                continue
            Skill.objects.create(name=skill["name"], description=skill["description"])

        for user_skill in self.user_skills:
            if UserSkill.objects.filter(
                user__username=user_skill["user"], skill__name=user_skill["skill"]
            ).exists():
                continue
            UserSkill.objects.create(
                user=User.objects.get(username=user_skill["user"]),
                skill=Skill.objects.get(name=user_skill["skill"]),
            )
