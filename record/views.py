from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.contrib import messages
from record.models import Record
from django.contrib.auth.models import User
from datetime import datetime, date as dt_date, timedelta
from collections import defaultdict
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

def can_view_dashboard(user):
    return user.is_superuser or user.is_staff or user.groups.filter(name='DashboardViewers').exists()

@login_required
def index(request):
    if request.method == 'POST':
        user = request.user
        selected_date = request.POST.get('date')
        is_leave = request.POST.get('is_leave') == 'on'
        fields = 0 if is_leave else int(request.POST.get('fields', 0))

        # Check if the date already exists for the user
        if Record.objects.filter(date=selected_date, user=user).exists():
            messages.error(request, 'You have already entered data for this date.')
        else:
            # Save the new record
            record = Record(user=user, date=selected_date, field=fields, is_leave=is_leave)
            record.save()
            messages.success(request, 'Record saved successfully!')
        return redirect('index')
    
    else:
        today = dt_date.today()
        start_date = today - timedelta(days=7)  # default to the past 7 days
        end_date = today
        
        if request.GET.get('start_date') and request.GET.get('end_date'):
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()

        records = Record.objects.filter(user=request.user, date__range=[start_date, end_date]).order_by('-date')
        
        context = {
            'user': request.user,
            'today': today,
            'records': records,
            'start_date': start_date,
            'end_date': end_date,
        }
        return render(request, 'index.html', context)


    
def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')
    else:
        return render(request, 'login.html')

@login_required
def logout_user(request):
    logout(request)
    # messages.success(request, 'Logged out successfully!')
    return redirect('login')

@login_required
@user_passes_test(can_view_dashboard)
def dashboard(request):
    today = dt_date.today()
    start_date = today  
    end_date = today
    status_date = today  # default status report date
    selected_user = None  # default to showing all users

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        status_date_str = request.POST.get('status_date')
        selected_user_id = request.POST.get('selected_user')

        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if status_date_str:
                status_date = datetime.strptime(status_date_str, '%Y-%m-%d').date()
            if selected_user_id:
                selected_user = User.objects.get(id=selected_user_id)
        except (ValueError, User.DoesNotExist):
            messages.error(request, 'Invalid input. Please try again.')

    records = Record.objects.filter(date__range=[start_date, end_date])
    if selected_user:
        records = records.filter(user=selected_user)
    records = records.order_by('date', 'user')

    data = defaultdict(lambda: defaultdict(lambda: {'value': 0, 'type': 'normal', 'id': None}))
    dates = set()

    for record in records:
        if record.is_leave:
            data[record.user.username][record.date] = {'value': 'Leave', 'type': 'leave', 'id': record.id}
        else:
            data[record.user.username][record.date] = {'value': record.field, 'type': 'normal', 'id': record.id}
        dates.add(record.date)

    dates = sorted(dates)

    user_data = {}
    daily_totals = [0] * len(dates)
    grand_total = 0

    for username, user_records in data.items():
        daily_records = []
        user_total = 0
        for date in dates:
            record = user_records.get(date, {'value': 0, 'type': 'normal', 'id': None})
            daily_records.append(record)
            if record['type'] == 'normal':
                user_total += record['value']
                daily_totals[dates.index(date)] += record['value']
        
        user_data[username] = {
            'daily_records': daily_records,
            'total': user_total
        }
        grand_total += user_total

    # Prepare data for the chart
    chart_labels = [date.strftime('%Y-%m-%d') for date in dates]
    chart_data = daily_totals

    # Status report for selected date
    all_users = User.objects.all()
    status_report = {}
    for user in all_users:
        record = Record.objects.filter(user=user, date=status_date).first()
        if record:
            if record.is_leave:
                status_report[user.username] = "Leave"
            else:
                status_report[user.username] = record.field
        else:
            status_report[user.username] = "Not entered yet"

    context = {
        'user': request.user,
        'date_range': dates,
        'user_data': user_data,
        'daily_totals': daily_totals,
        'grand_total': grand_total,
        'start_date': start_date,
        'end_date': end_date,
        'today': today,
        'status_date': status_date,
        'status_report': status_report,
        'all_users': User.objects.all(),  # Add this line
        'selected_user': selected_user,  # Add this line
        'chart_labels': chart_labels,
        'chart_data': chart_data
    }

    return render(request, 'dashboard.html', context)

@login_required
@user_passes_test(can_view_dashboard)
def status_record(request):
    today = dt_date.today()
    status_date = today  # default status report date

    if request.method == 'POST':
        status_date_str = request.POST.get('status_date')
        try:
            if status_date_str:
                status_date = datetime.strptime(status_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date. Please try again.')

    # Status report for selected date
    all_users = User.objects.all()
    status_report = {}
    for user in all_users:
        record = Record.objects.filter(user=user, date=status_date).first()
        if record:
            if record.is_leave:
                status_report[user.username] = "Leave"
            else:
                status_report[user.username] = record.field
        else:
            status_report[user.username] = "Not entered yet"

    context = {
        'status_date': status_date,
        'status_report': status_report,
    }

    return render(request, 'statusrecord.html', context)

@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def update_record(request):
    data = json.loads(request.body)
    record_id = data.get('id')
    new_value = data.get('value')
    record_type = data.get('type')

    try:
        record = Record.objects.get(id=record_id)
        if record_type == 'leave':
            record.is_leave = new_value.lower() == 'leave'
            record.field = 0
        else:
            record.is_leave = False
            record.field = int(new_value)
        record.save()
        return JsonResponse({'success': True})
    except Record.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Record not found'})
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid value'})
    