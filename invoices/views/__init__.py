
# django modules
from django.http import HttpResponse
#from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.db.models.functions import ExtractYear
from invoices.models import Invoice, Recipient, UserProfile, InvoiceItem, Advance
from invoices.models import randstring
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.http import require_GET

# api keys
from protected import SENDGRID_API_KEY, EMAIL  # ,OTHER_EMAIL

# general imports
import os
import json
import base64
from qrplatba import QRPlatbaGenerator
from xhtml2pdf import pisa
from datetime import datetime, timedelta
from io import BytesIO
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# sendgrid mail modules
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Bcc, Attachment, FileContent, FileName, FileType, Disposition, ContentId)

# helpers
from invoices.ares import ARES
from invoices.exchange_cnb import get_exchange_rates

# views
from .utils import *
from .users import *
from .advances import *
from .invoices import *
from .recipients import *
from .prints import *
