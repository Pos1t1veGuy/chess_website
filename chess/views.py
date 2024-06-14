from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse
from django.views import View
from django.conf import settings

from AUTH.models import User
import json
import random
import os


class api(View):
	def get(self, request):
		key = request.GET.get('key')
		if key == 'leaders':
			portion = request.GET.get('portion')
			index = request.GET.get('index')
			if portion and index:
				if portion.isdigit() and index.isdigit():
					portion = int(portion)
					index = int(index)
					if 0 <= portion and 0 <= index:
						users = list( User.objects.values_list('username', flat=True) )

						if User.objects.count() <= index:
							raise Http404('')
						elif User.objects.count() <= portion:
							return HttpResponse(json.dumps(users))
						else:
							return HttpResponse(json.dumps(users))

		raise Http404('')

def random_favicon(request):
	try:
		icons = os.listdir(settings.ICONS_DIR)
		if icons:
			return FileResponse(open(f'{settings.ICONS_DIR}/{random.choice(icons)}', 'rb'), content_type='image/x-icon')
		else:
			raise Http404("No icons found")
	except FileNotFoundError:
		raise Http404("Icon directory not found")