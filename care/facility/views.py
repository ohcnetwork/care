from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import FacilityCreationForm, FacilityCapacityCreationForm
from .models import Facility


class FacilityCreation(LoginRequiredMixin, View):

    form_class = FacilityCreationForm
    template = "facility/facility_creation.html"

    def get(self, request):
        try:
            form = self.form_class()
            return render(request, self.template, {"form": form})
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")

    def post(self, request):
        try:
            data = request.POST
            form = self.form_class(data)
            if form.is_valid():
                facility_obj = form.save()
                return HttpResponseRedirect(
                    "/facility/{}/capacity/add".format(facility_obj.id)
                )
            return render(request, self.template, {"form": form})
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")


class FacilityCapacityCreation(LoginRequiredMixin, View):
    form_class = FacilityCapacityCreationForm
    template = "facility/facility_capacity_creation.html"

    def get(self, request, pk):
        try:
            form = self.form_class()
            return render(request, self.template, {"form": form})
        except Exception as e:
            return HttpResponseRedirect("")

    def post(self, request, pk):
        try:
            data = request.POST
            form = self.form_class(data)
            if form.is_valid():
                duplicate = False
                facility_capacity_obj = form.save(commit=False)
                facility_obj = Facility.objects.get(id=pk)
                facility_capacity_obj.facility = facility_obj
                try:
                    facility_capacity_obj.save()
                except IntegrityError:
                    duplicate = True
                if "addmore" in data:
                    return HttpResponseRedirect(
                        "/facility/{}/capacity/add".format(facility_obj.id)
                    )
                else:
                    return redirect("home")
            return render(
                request, self.template, {"form": form, "duplicate": duplicate}
            )
        except Exception as e:
            return HttpResponseRedirect("")

