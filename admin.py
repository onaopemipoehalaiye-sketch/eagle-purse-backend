import os

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from models import Transaction, User

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "eaglepurse-admin")
SECRET_KEY = os.getenv("SECRET_KEY", "eaglepurse-secret-key")


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        return request.session.get("admin_authenticated", False)


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"
    column_list = [
        User.email,
        User.monthly_allowance,
        User.feeding_budget,
        User.dietary_pref,
        User.allowance_period,
        User.meals_per_day,
    ]
    column_searchable_list = [User.email, User.dietary_pref]
    column_sortable_list = [User.email, User.monthly_allowance, User.feeding_budget]
    column_default_sort = [(User.email, False)]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    # Don't expose password hash in the list view
    column_details_exclude_list = [User.password_hash]


class TransactionAdmin(ModelView, model=Transaction):
    name = "Transaction"
    name_plural = "Transactions"
    icon = "fa-solid fa-receipt"
    column_list = [
        Transaction.id,
        Transaction.user_email,
        Transaction.date,
        Transaction.category,
        Transaction.vendor,
        Transaction.item,
        Transaction.amount,
    ]
    column_searchable_list = [Transaction.user_email, Transaction.vendor, Transaction.category, Transaction.item]
    column_sortable_list = [Transaction.date, Transaction.amount, Transaction.user_email, Transaction.category]
    column_default_sort = [(Transaction.date, True)]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


def create_admin(app, engine) -> Admin:
    authentication_backend = AdminAuth(secret_key=SECRET_KEY)
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="EaglePurse Admin",
        base_url="/admin",
    )
    admin.add_view(UserAdmin)
    admin.add_view(TransactionAdmin)
    return admin
