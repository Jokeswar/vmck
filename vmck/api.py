import base64
import json

import jwt
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import jobs
from . import models
from . import settings
from .backends import get_backend


def job_info(job):
    return {
        'id': job.id,
        'state': job.state,
    }


def home(request):
    return JsonResponse({
        'version': '0.0.1',
    })


def create_token(request):
    auth_header = request.headers['Authorization']
    token_type, _, credentials = auth_header.partition(' ')

    username, password = base64.b64decode(credentials).decode('utf-8').split(':')
    # TODO if password is not correct return failure

    private_key = settings.SECRET_KEY
    print("Signing with " + private_key)

    jwt_token = jwt.encode(
        {
            'sub': username,
            'iss': 'vmck'
        },
        key=private_key,
        algorithm='HS256'
    ).decode('utf-8')

    return JsonResponse({"auth_token": jwt_token})


def create_job(request):
    options = json.loads(request.body) if request.body else {}  # TODO validate
    options.setdefault('cpus', 1)
    options.setdefault('memory', 512)
    options['cpu_mhz'] = options['cpus'] * settings.QEMU_CPU_MHZ
    job = jobs.create(get_backend(), options)
    return JsonResponse(job_info(job))


def get_job(request, pk):
    job = get_object_or_404(models.Job, pk=pk)

    ssh_remote = jobs.poll(job)
    rv = dict(job_info(job), ssh=ssh_remote)
    return JsonResponse(rv)


def kill_job(request, pk):
    job = get_object_or_404(models.Job, pk=pk)
    jobs.kill(job)
    return JsonResponse({'ok': True})


def route(**views):
    @csrf_exempt
    @require_http_methods(list(views))
    def view(request, **kwargs):
        return views[request.method](request, **kwargs)

    return view


urls = [
    path('', route(GET=home)),
    path('token', route(POST=create_token)),
    path('jobs', route(POST=create_job)),
    path('jobs/<int:pk>', route(GET=get_job, DELETE=kill_job)),
]