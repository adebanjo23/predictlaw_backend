import os

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from dotenv import load_dotenv
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


############################################################################################## NEW PART
import os
from django.conf import settings
from dotenv import load_dotenv
import pickle
from PyPDF2 import PdfReader
from langdetect import detect, LangDetectException
from googletrans import Translator
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.callbacks import get_openai_callback

load_dotenv()

UPLOAD_FOLDER = 'pdfs'
embeddings_dir = 'embeddings'
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and (
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS or filename.lower().endswith('.json'))


@api_view(['POST'])
def upload_pdf(request):
    if request.method != 'POST':
        return Response("Invalid request method", status=status.HTTP_400_BAD_REQUEST)

    username = request.data.get('username')
    pdf = request.FILES.get('pdf')

    # Check if username and pdf are provided
    if not (username and pdf):
        return Response("Username and PDF file are required", status=status.HTTP_400_BAD_REQUEST)

    # Check if the file type is allowed
    if not allowed_file(pdf.name):
        return Response("Invalid file type. Only PDF files are allowed", status=status.HTTP_400_BAD_REQUEST)

    # Check if a file with the same username already exists
    existing_file_path = os.path.join(settings.MEDIA_ROOT, UPLOAD_FOLDER, f"{username}.pdf")
    if os.path.exists(existing_file_path):
        return Response(f'A PDF file with the username {username} already exists. Delete it to upload a new one.',
                        status=status.HTTP_400_BAD_REQUEST)

    # Save the PDF file
    filename = f"{username}.pdf"
    with open(os.path.join(settings.MEDIA_ROOT, UPLOAD_FOLDER, filename), 'wb') as destination:
        for chunk in pdf.chunks():
            destination.write(chunk)

    return Response({'message': 'PDF uploaded successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def query_pdf(request):
    if request.method != 'POST':
        return Response("Invalid request method", status=status.HTTP_400_BAD_REQUEST)

    username = request.data.get('username')
    query = request.data.get('question')

    if not (username and query):
        return Response("Username and question are required", status=status.HTTP_400_BAD_REQUEST)

    filename = f"{username}.pdf"
    pdf_path = os.path.join(settings.MEDIA_ROOT, UPLOAD_FOLDER, filename)

    if os.path.exists(pdf_path):
        try:
            pdf_reader = PdfReader(pdf_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()

            # Detect language
            try:
                detected_language = detect(text)
            except LangDetectException as e:
                return Response(f'Language detection error: {str(e)}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if detected_language != 'en':
                try:
                    translator = Translator()
                    translated_text = translator.translate(text, src=detected_language, dest='en').text
                    text = translated_text
                except Exception as e:
                    print(f"Translation error: {str(e)}")

            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            chunks = text_splitter.split_text(text=text)

            # Load or create embeddings
            store_name = username
            if os.path.exists(f"media/embeddings/{store_name}.pkl"):
                with open(f"media/embeddings/{store_name}.pkl", "rb") as f:
                    VectorStore = pickle.load(f)
            else:
                embeddings = OpenAIEmbeddings()
                VectorStore = FAISS.from_texts(chunks, embedding=embeddings)
                with open(f"media/embeddings/{store_name}.pkl", "wb") as f:
                    pickle.dump(VectorStore, f)

            # Query the model
            docs = VectorStore.similarity_search(query=query, k=3)
            llm = OpenAI(model_name='gpt-3.5-turbo', temperature=0.8)
            chain = load_qa_chain(llm=llm, chain_type="stuff")
            with get_openai_callback() as cb:
                response = chain.run(input_documents=docs, question=query)
            return Response({'response': response}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response('PDF not found for the given username', status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def delete_pdf(request):
    if request.method != 'POST':
        return Response("Invalid request method", status=status.HTTP_400_BAD_REQUEST)

    username = request.data.get('username')

    if not username:
        return Response("Username is required for deletion", status=status.HTTP_400_BAD_REQUEST)

    filename = f"{username}.pdf"
    pdf_path = os.path.join(settings.MEDIA_ROOT, UPLOAD_FOLDER, filename)
    pkl_path = os.path.join(settings.MEDIA_ROOT, embeddings_dir, f"{username}.pkl")

    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
            if os.path.exists(pkl_path):
                os.remove(pkl_path)
            return Response({'message': f'PDF file and embedding for {username} deleted successfully'},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response('PDF not found for the given username', status=status.HTTP_404_NOT_FOUND)
