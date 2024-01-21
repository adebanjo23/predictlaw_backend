from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from django.db.models import Q
from .models import User
from .tokens import account_activation_token
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import authenticate, login


@api_view(['POST'])
def signup(request):
    if request.method != 'POST':
        return Response("Invalid request method", status=HTTP_400_BAD_REQUEST)

    try:
        username = request.data.get("username")
        phone = request.data.get("phone")
        email = request.data.get("email")

        if not username or not phone or not email:
            return Response("All fields are required", status=status.HTTP_400_BAD_REQUEST)

        print("Here")

        # Check if a user with the provided username or email already exists
        existing_user = User.objects.filter(Q(username=username) | Q(email=email)).first()

        print("Here3")
        if existing_user:
            return Response({"error": "User with this username or email already exists"}, status=HTTP_400_BAD_REQUEST)

        # Create a new user if one doesn't already exist
        user = User.objects.create(
            username=username,
            phone=phone,
            email=email,
            is_active=False
        )

        current_site = get_current_site(request)
        mail_subject = 'Predict Law User Activation Link'
        message = render_to_string('acc_active_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
        })

        to_email = user.email
        email = EmailMessage(
            mail_subject, message, to=[to_email]
        )

        try:
            email.send()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"success": "Sign up successful"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('https://8q8uukr1vo.postedstuff.com/V2-6LB4-i2o9-VWma-5YRA/')
    else:
        return redirect('https://8q8uukr1vo.postedstuff.com/V2-6LB4-i2o9-VWma-KBKo/')


@api_view(['POST'])
def resend_activation_link(request):
    if request.method != 'POST':
        return Response("Invalid request method", status=HTTP_400_BAD_REQUEST)

    try:
        username = request.data.get("username")
        if not username:
            return Response("Username is required", status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username, is_active=False)
        except User.DoesNotExist:
            return Response({"error": "User not found or already activated"}, status=status.HTTP_404_NOT_FOUND)

        current_site = get_current_site(request)
        mail_subject = 'Predict Law User Activation Link'
        message = render_to_string('acc_active_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
        })
        to_email = user.email
        email = EmailMessage(
            mail_subject, message, to=[to_email]
        )
        try:
            email.send()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"success": "Activation link resent successfully"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def user_login(request):
    if request.method != 'POST':
        return Response("Invalid request method", status=HTTP_400_BAD_REQUEST)

    try:
        username = request.data.get("username")
        if not username:
            return Response("Username is required", status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(username=username)

        if user is None:
            return Response({"error": "Invalid username"}, status=status.HTTP_401_UNAUTHORIZED)

        if user.is_active:
            return Response({"success": "Login successful"}, status=status.HTTP_200_OK)

        else:
            return Response({"error": "User is not active"}, status=status.HTTP_406_NOT_ACCEPTABLE)

    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

