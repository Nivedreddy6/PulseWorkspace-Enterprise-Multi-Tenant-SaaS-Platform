from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db import transaction
from django.utils.text import slugify

from .models import User
from workspaces.models import Workspace, WorkspaceMembership
from billing.models import Plan, Subscription
from core.models import AuditLog, log_audit_event


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.display_name}!")
            log_audit_event(
                actor=user,
                action=AuditLog.Action.LOGIN,
                resource_type='User',
                resource_id=str(user.id),
                description=f"User {user.username} logged in successfully."
            )
            return redirect(request.GET.get('next') or 'dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'accounts/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        company_name = request.POST.get('company_name', '').strip() or f"{username}'s Team"

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, 'accounts/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'accounts/register.html')

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role_title='Workspace Owner'
            )

            # Auto-provision initial workspace and owner membership
            workspace = Workspace.objects.create(
                name=company_name,
                owner=user,
                description=f"Default workspace for {company_name}"
            )
            WorkspaceMembership.objects.create(
                workspace=workspace,
                user=user,
                role=WorkspaceMembership.Role.OWNER
            )
            # Default Free Tier
            free_plan, _ = Plan.objects.get_or_create(
                tier_code=Plan.Tier.FREE,
                defaults={'name': 'Free Starter', 'price_monthly': 0.00, 'max_members': 3, 'max_projects': 5}
            )
            Subscription.objects.create(
                workspace=workspace,
                plan=free_plan,
                status=Subscription.Status.ACTIVE
            )

            login(request, user)
            request.session['active_workspace_slug'] = workspace.slug

            log_audit_event(
                actor=user,
                action=AuditLog.Action.CREATE,
                resource_type='User',
                resource_id=str(user.id),
                description=f"Registered account and provisioned workspace '{workspace.name}'",
                workspace=workspace
            )

            messages.success(request, f"Welcome to PulseWorkspace, {user.first_name or user.username}!")
            return redirect('dashboard')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')
