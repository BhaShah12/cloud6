import os
import datetime
import pytz

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import default_storage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import JobForm
from .models import Job
from .models import Profile
from .filters import JobFilter

def user_login(request):
    form = AuthenticationForm()
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = authenticate(username=email, password=password)
            login(request, user)
            messages.success(request, f' Successfully logged in as {user.username}!')
            return redirect('home')
        except:
            if not User.objects.filter(email=email).exists():
                messages.error(request, "Account Not found. Please sign up using the below link.")
            elif not User.objects.get(email=email).profile.native_auth:
                messages.error(request, "You chose the Google sign-in method when you created your account. Please "
                                        "choose Google to sign in.")
            else:
                messages.error(request, "Username and Password didn't match, please try again!")

    elif request.method == 'GET':
        return render(request, 'registration/login.html')

    return render(request, 'registration/login.html', {'form': form, 'title': 'log in'})


def users_signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('fname')
        last_name = request.POST.get('lname')
        password = request.POST.get('password')
        role = request.POST.get('inlineRadioOptions')
        time_zone = request.POST.get('userTimezone')
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                username=email,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password
            )
            user.profile.role = role
            user.profile.native_auth = True
            user.profile.time_zone = time_zone
            user.save()
            user = authenticate(username=email, password=password)
            if user:
                login(request, user)
                messages.success(request, f' Account Successfully created for {user.username}!')
                return redirect('home')
            else:
                error = " Sorry! There was an error while registering your account, Please try again ! "
                messages.error(request, f' Sorry! There was an error while registering the account for {user.username},'
                                        f' Please try again!')
                return render(request, 'registration/signup.html', {"error": error})

        else:
            messages.error(request, "Account already exists. Please login.")
            return render(request, 'registration/login.html')

    elif request.method == 'GET':
        return render(request, 'registration/signup.html', {'timezones': pytz.common_timezones})

    else:
        error = " Unhandled Exception. Please try again"
        messages.error(request, "Account not created, please try again!")
        return render(request, 'registration/signup.html', {"error": error})


def users_profile(request):
    if request.user.is_authenticated:
        #Get existing data from database and display everything to the user
        #Display empty fields as empty with Submit button enabled
        #If no fields are required then submit button should be disabled
        #If user changes any info in the form then submit button should become enabled
        if request.method == 'GET':
            selectedTimeZone = "UTC"
            if request.user.profile.time_zone != '':
                selectedTimeZone = request.user.profile.time_zone
            context = {
                'user': request.user,
                'timezones': pytz.common_timezones,
                'selectedTimeZone' : selectedTimeZone
            }
            return render(request, 'home/profile.html',context)
        elif request.method == 'POST':
            user = User.objects.get(id=request.user.id)
            user.profile.time_zone = request.POST.get('userTimezone')
            user.save()
            context = {
                'user': request.user,
                'timezones': pytz.common_timezones,
                'selectedTimeZone': user.profile.time_zone
            }
            messages.success(request, f' Profile updated successfully for {user.username}!')
            return render(request, 'home/profile.html', context)
    else:
        return redirect('login_url')


def users_jobs(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = JobForm(request.POST or None)
            form.instance.user = request.user
            if form.is_valid():
                if request.POST.get("URL"):
                    # test the gdrive link first
                    form.instance.url2audio = request.POST.get("URL")
                else:
                    filename = filename_gen(str(request.user))
                    default_storage.save(filename, request.FILES['audiofile'])
                    form.instance.url2audio = url_gen(filename)
                form.save()
                messages.success(request, ('Your Job has been created successfully'))
            else:
                messages.error(request, ('Error creating Job. Please try again'))
            return render(request, 'jobs/jobs.html')
        
        elif request.method=='GET':
            post_list = Job.objects.all()
            paginator = Paginator(post_list, 2)
            page = request.GET.get('page')
            try:
                posts = paginator.page(page)
            except PageNotAnInteger:
                posts = paginator.page(1)
            except EmptyPage:
                posts = paginator.page(paginator.num_pages)

            myFilter = JobFilter()
            #page=myFilter.queryset

            if request.user.profile.role == 'creator':
                return render(request, 'jobs/jobs.html', {'page':page,'posts':posts, 'myFilter':myFilter})
            else:
                return render(request, 'jobs/w_jobs.html', {'page':page,'posts':posts, 'myFilter':myFilter})
    else:
        return redirect('login_url')

def users_reviews(request):
    if request.user.is_authenticated:
        return render(request, 'Reviews/reviews.html')
    else:
        return redirect('login_url')


def users_payments(request):
    if request.user.is_authenticated:
        return render(request, 'Payments/payments.html')
    else:
        return redirect('login_url')


def users_instructions(request):
    if request.user.is_authenticated:
        return render(request, 'home/instructions.html')
    else:
        return redirect('login_url')


# Helpers
def filename_gen(user):
    return str(datetime.datetime.now().timestamp()).replace('.', '-') + "-" + user + ".mp3"


def url_gen(filename):
    return "https://" + os.environ['bucket_name'] + ".s3." + os.environ['aws_region'] + ".amazonaws.com/" + filename
