from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.views import View

from AUTH.models import User
import json


class api(View):
	def get(request):
		key = request.GET.get('key')
		if key == 'leaders':
			portion = request.GET.get('portion')
			index = request.GET.get('index')
			if portion and index:
				if portion.isdigit() and index.isdigit():
					portion = int(portion)
					index = int(index)
					if 0 <= portion and 0 <= index:

						if User.objects.count() <= index:
							raise Http404('')
						elif User.objects.count() <= portion:
							return HttpResponse(json.dumps( list(User.objects.all()) ))
						else:
							return HttpResponse(json.dumps( list(User.objects.all()[portion*index:portion*index + portion]) ))

		raise Http404('')